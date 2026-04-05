#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "httpx>=0.28.1",
#     "python-dotenv>=1.2.1",
# ]
# ///
# =============================================================
# scrape.py — B2C scraper using Firecrawl API
# Sources: Gumtree (buyer-intent ads), HelloPeter (competitor complaints)
# =============================================================
# Usage:
#   uv run scripts/scrape.py gumtree
#   uv run scripts/scrape.py gumtree --max 30 --out /tmp/leads.json
#   uv run scripts/scrape.py hellopeter
#   uv run scripts/scrape.py hellopeter --max 20
#
# Output: JSON array to stdout (or --out file)
# Schema: { title, description, phone, location, price, adid, url, source,
#            competitor, pain_point, scraped_at }
# =============================================================

import argparse
import hashlib
import json
import logging
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx
from dotenv import load_dotenv
import os

load_dotenv(Path.home() / ".hermes/.env")

# ── Logging ──────────────────────────────────────────────────

log = logging.getLogger("scraper")


def setup_logging(log_dir: Path, source: str) -> None:
    log.setLevel(logging.DEBUG)
    console = logging.StreamHandler(sys.stderr)
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter("[%(name)s] %(levelname)s: %(message)s"))
    log.addHandler(console)
    log_dir.mkdir(exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    fh = logging.FileHandler(log_dir / f"{source}-{today}.log", encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter("%(asctime)s [%(name)s] %(levelname)s: %(message)s"))
    log.addHandler(fh)


# ── Constants ────────────────────────────────────────────────

# NOTE: Gumtree removed the "Wanted Ads" top-level category (c9110) in 2025/2026.
# All /s-wanted-ads/... paths now 301-redirect to /s-all-the-ads/v1b0p1 (losing the keyword).
# Use buyer-intent keyword phrases (?q=) to surface people looking to BUY a tracker.
SEARCH_URLS = [
    # Direct buyer-intent queries
    "https://www.gumtree.co.za/s-all-the-ads/v1b0p1?q=need+car+tracker",
    "https://www.gumtree.co.za/s-all-the-ads/v1b0p1?q=want+car+tracker",
    "https://www.gumtree.co.za/s-all-the-ads/v1b0p1?q=car+tracker+wanted",
    "https://www.gumtree.co.za/s-all-the-ads/v1b0p1?q=looking+for+tracker",
    "https://www.gumtree.co.za/s-all-the-ads/v1b0p1?q=gps+tracker+needed",
    "https://www.gumtree.co.za/s-all-the-ads/v1b0p1?q=vehicle+tracker+wanted",
    # Theft/crime-related — people who just experienced theft are hot tracker prospects
    "https://www.gumtree.co.za/s-all-the-ads/v1b0p1?q=car+stolen+tracker",
    "https://www.gumtree.co.za/s-all-the-ads/v1b0p1?q=vehicle+stolen+need+tracker",
    "https://www.gumtree.co.za/s-all-the-ads/v1b0p1?q=hijacked+car+tracker",
    "https://www.gumtree.co.za/s-all-the-ads/v1b0p1?q=car+break+in+tracker",
    # Vehicle security / anti-theft — adjacent intent
    "https://www.gumtree.co.za/s-all-the-ads/v1b0p1?q=vehicle+security+tracking",
    "https://www.gumtree.co.za/s-all-the-ads/v1b0p1?q=car+theft+prevention+tracker",
    # Installation / service requests — people seeking tracker installation
    "https://www.gumtree.co.za/s-all-the-ads/v1b0p1?q=tracker+installation+wanted",
    "https://www.gumtree.co.za/s-all-the-ads/v1b0p1?q=install+car+tracker",
    # New car purchases — people who just bought expensive vehicles (Tier 1)
    "https://www.gumtree.co.za/s-all-the-ads/v1b0p1?q=just+bought+car+need+tracker",
    "https://www.gumtree.co.za/s-all-the-ads/v1b0p1?q=new+car+need+tracker",
    "https://www.gumtree.co.za/s-all-the-ads/v1b0p1?q=just+bought+bakkie+tracker",
    "https://www.gumtree.co.za/s-all-the-ads/v1b0p1?q=just+bought+SUV+tracker",
    "https://www.gumtree.co.za/s-all-the-ads/v1b0p1?q=just+bought+Fortuner",
    "https://www.gumtree.co.za/s-all-the-ads/v1b0p1?q=just+bought+Land+Cruiser",
    "https://www.gumtree.co.za/s-all-the-ads/v1b0p1?q=just+bought+Ranger+tracker",
    "https://www.gumtree.co.za/s-all-the-ads/v1b0p1?q=new+car+insurance+tracker",
]

# HelloPeter — competitor complaint scraping (Tier 1 + Tier 2 signal)
HELLOPETER_TARGETS = [
    {"slug": "cartrack", "competitor": "Cartrack"},
    {"slug": "tracker-connect", "competitor": "Tracker Connect"},
    {"slug": "mix-telematics", "competitor": "MiX Telematics"},
    {"slug": "netstar", "competitor": "Netstar"},
    {"slug": "beame", "competitor": "Beame"},
]
HELLOPETER_BASE = "https://www.hellopeter.com"

# Gumtree URL path segments that NEVER contain tracker buyer-intent ads.
_BLOCKED_CATEGORIES = [
    "/a-cars-bakkies/",
    "/a-heavy-trucks-buses/",
    "/a-other-pets/",
    "/a-removals-storage/",
    "/a-property-",
    "/a-wearable-technology/",
]

# Gumtree-owned numbers injected site-wide (not seller phones)
_GUMTREE_NUMBERS = {"+27756035177", "27756035177", "0870220222", "+27870220222"}

PHONE_RE = re.compile(r"(?:\+27|27|0)[6-8]\d[\s\-]?\d{3}[\s\-]?\d{4}")

GUMTREE_BASE = "https://www.gumtree.co.za"

# ── Retry constants ──────────────────────────────────────────
MAX_RETRIES = 3
RETRY_DELAYS = [2, 5, 15]

# ── Firecrawl ────────────────────────────────────────────────
FIRECRAWL_API_KEY = os.environ.get("FIRECRAWL_API_KEY")
FIRECRAWL_BASE = "https://api.firecrawl.dev/v1"


# ── Helpers — copied from gumtree_scrapling.py ───────────────

def extract_phone(text: str | None) -> str | None:
    """Extract and normalise a SA phone number from text."""
    if not text:
        return None
    match = PHONE_RE.search(text)
    if not match:
        return None
    number = re.sub(r"[\s\-]", "", match.group(0))
    if number.startswith("0"):
        number = "+27" + number[1:]
    elif number.startswith("27") and not number.startswith("+"):
        number = "+" + number
    # Filter Gumtree's own numbers
    if number in _GUMTREE_NUMBERS:
        return None
    return number


def extract_ad_links(links: list[str]) -> list[str]:
    """
    Filter a list of URLs to individual Gumtree ad links.
    Accept:  URLs with /a- pattern
    Reject:  blocked categories, job ads, user pages
    """
    seen = set()
    result = []
    for href in links:
        if not href:
            continue
        # Normalise to absolute URL
        if href.startswith("/"):
            href = GUMTREE_BASE + href
        href = href.split("?")[0]  # strip query params
        if "/a-" not in href:
            continue
        if "/s-user/" in href or "/s-my-gumtree/" in href:
            continue
        if not href.startswith(GUMTREE_BASE):
            continue
        if any(cat in href for cat in _BLOCKED_CATEGORIES):
            continue
        if "-jobs/" in href:
            continue
        if href not in seen:
            seen.add(href)
            result.append(href)
    return result


def url_hash(url: str) -> str:
    """Generate a stable 12-char dedup key from a URL."""
    return hashlib.md5(url.encode()).hexdigest()[:12]


def extract_adid(url: str) -> str | None:
    """Extract adid from URL — last numeric segment or /a-xxx/DIGITS pattern."""
    m = re.search(r"/a-[^/]+/(\d+)", url)
    if m:
        return m.group(1)
    m = re.search(r"/(\d{7,12})$", url)
    if m:
        return m.group(1)
    # Fall back to last segment if numeric
    parts = [p for p in url.rstrip("/").split("/") if p]
    if parts and re.match(r"^\d+$", parts[-1]):
        return parts[-1]
    return None


def parse_ad_markdown(markdown: str, url: str) -> dict:
    """Extract lead fields from Firecrawl markdown of an individual ad page."""
    lines = markdown.strip().splitlines()

    # Title: first non-empty H1 or first non-empty line
    title = None
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("# "):
            title = stripped[2:].strip()
            break
        if stripped and not title:
            title = stripped

    # Description: concatenate non-heading, non-empty lines (skip first few nav lines)
    desc_lines = []
    in_desc = False
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            in_desc = True
            continue
        if in_desc and stripped:
            desc_lines.append(stripped)
            if len(" ".join(desc_lines)) > 2000:
                break
    description = " ".join(desc_lines[:50]) if desc_lines else markdown[:500]

    # Location — three strategies in priority order:
    # 1. Firecrawl markdown puts location on the line AFTER "Location:" as markdown links:
    #    "Location:"
    #    "[Other](url), [Cape Town](url)"
    # 2. "Location:" label with inline content on the same line (older format)
    # 3. URL path segment — Gumtree ad URLs: /a-category/city-slug/title/adid
    location = None

    # Strategy 1 & 2: find "Location:" line then extract from next line or same line
    for i, line in enumerate(lines):
        stripped = line.strip()
        if re.search(r"(?i)^location\s*:?\s*$", stripped):
            # Content is on the next non-empty line as markdown links
            for j in range(i + 1, min(i + 4, len(lines))):
                next_line = lines[j].strip()
                if not next_line:
                    continue
                # Extract all markdown link texts: [City](url)
                link_texts = re.findall(r"\[([^\]]+)\]\(https?://[^)]+\)", next_line)
                # Filter out "Other" (Gumtree placeholder) and keep real city/region names
                meaningful = [t for t in link_texts if t.lower() not in ("other", "all categories", "all ads")]
                if meaningful:
                    location = ", ".join(meaningful)
                break
            if location:
                break
        elif re.search(r"(?i)location\s*[:\|]", stripped):
            # Inline: "Location: Cape Town" or "Location | Cape Town"
            loc = re.sub(r"(?i)location\s*[:\|]\s*", "", stripped).strip()
            # Strip any markdown links, keep text
            loc = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", loc)
            loc = loc.strip(" ,")
            if loc and loc.lower() not in ("", "other"):
                location = loc
            break

    # Strategy 3: extract from URL path if still no location
    # Gumtree ad URL structure: /a-{category}/{city-slug}/{title}/{adid}
    # e.g. /a-all-the-ads/johannesburg/need-tracker/123
    if not location:
        url_parts = [p for p in url.replace("https://www.gumtree.co.za", "").split("/") if p]
        # url_parts[0] = "a-category", url_parts[1] = city-slug (if not numeric/title)
        if len(url_parts) >= 3:
            city_slug = url_parts[1]
            # Skip if it looks like a title (contains many words) or is "other"
            if city_slug.lower() not in ("other", "v1b0p1") and "-" in city_slug and len(city_slug) < 40:
                # Convert slug to title case: "cape-town" → "Cape Town"
                city_name = city_slug.replace("-", " ").title()
                # Sanity check: must look like a SA city name, not a category
                if not any(kw in city_slug for kw in ("electronics", "services", "cars", "property", "jobs", "bakkies", "trucks")):
                    location = city_name

    # Price — look for R digit pattern
    price = None
    price_m = re.search(r"R\s*[\d,]+", markdown)
    if price_m:
        price = price_m.group(0).replace(" ", "")

    # Phone — search description and full markdown
    phone = extract_phone(description)
    if not phone:
        phone = extract_phone(markdown)

    adid = extract_adid(url)

    return {
        "title": title,
        "description": description,
        "phone": phone,
        "location": location,
        "price": price,
        "adid": adid,
        "url": url,
        "source": "Gumtree",
        "competitor": None,
        "pain_point": None,
        "scraped_at": datetime.now(timezone.utc).isoformat(),
    }


# ── HelloPeter helpers ───────────────────────────────────────

def extract_review_links(links: list[str], slug: str) -> list[str]:
    """Filter a list of URLs to individual HelloPeter review detail links."""
    seen: set[str] = set()
    result: list[str] = []
    for href in links:
        if not href:
            continue
        if not href.startswith("http"):
            href = HELLOPETER_BASE + href
        # Must be a review detail page (not the listing page itself)
        if f"/{slug}/reviews/" not in href:
            continue
        # Strip query params for dedup
        href = href.split("?")[0]
        if href not in seen:
            seen.add(href)
            result.append(href)
    return result


def parse_hellopeter_markdown(markdown: str, url: str, competitor: str) -> dict:
    """Extract lead fields from a scraped HelloPeter review page."""
    lines = [l.strip() for l in markdown.splitlines() if l.strip()]

    # Title: first H1 or first heading-like line
    title = f"Complaint about {competitor}"
    for line in lines:
        if line.startswith("# "):
            candidate = line[2:].strip()
            if len(candidate) > 5:
                title = candidate
                break

    # Reviewer name — look for "by <Name>" or "Reviewed by" patterns
    reviewer_name = None
    name_patterns = [
        re.compile(r"(?i)(?:reviewed?\s+by|by|from)\s*[:\-]?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]\.?)?)", re.MULTILINE),
        re.compile(r"(?i)([A-Z][a-z]+\s+[A-Z]\.)\s+(?:from|in|at)\s+\w", re.MULTILINE),
    ]
    for pattern in name_patterns:
        m = pattern.search(markdown)
        if m:
            reviewer_name = m.group(1).strip()
            break

    # Location — look for "from <City>" pattern in review text
    location = None
    loc_m = re.search(r"(?i)\bfrom\s+([A-Z][a-zA-Z\s]{2,20})(?:\s*[,\.]|\s+\w)", markdown)
    if loc_m:
        candidate = loc_m.group(1).strip()
        # Only accept plausible SA city names (not common words)
        if candidate.lower() not in ("the", "a", "this", "that", "my", "your", "his", "her"):
            location = candidate

    # Description: extract review body (longer text block, skip nav/metadata)
    desc_lines = []
    for line in lines:
        if len(line) > 30 and not line.startswith("#") and not line.startswith("[") and not line.startswith("|"):
            desc_lines.append(line)
            if len(" ".join(desc_lines)) > 2000:
                break

    description = " ".join(desc_lines[:40]) if desc_lines else markdown[:500]
    pain_point = description[:500]

    return {
        "title": title,
        "description": description,
        "phone": None,
        "location": location,
        "price": None,
        "adid": url_hash(url),
        "url": url,
        "source": "HelloPeter",
        "competitor": competitor,
        "pain_point": pain_point,
        "reviewer_name": reviewer_name,
        "scraped_at": datetime.now(timezone.utc).isoformat(),
    }


# ── Firecrawl API calls ──────────────────────────────────────

def firecrawl_scrape_links(url: str, client: httpx.Client) -> list[str]:
    """Scrape a Gumtree listing page and return the links."""
    for attempt in range(MAX_RETRIES):
        try:
            resp = client.post(
                f"{FIRECRAWL_BASE}/scrape",
                json={"url": url, "formats": ["links"]},
                timeout=60.0,
            )
            if resp.status_code == 402:
                log.error("Firecrawl credits exhausted (HTTP 402) — aborting")
                sys.exit(1)
            if resp.status_code >= 500:
                delay = RETRY_DELAYS[attempt]
                log.warning("Firecrawl server error %d, retry in %ds", resp.status_code, delay)
                time.sleep(delay)
                continue
            resp.raise_for_status()
            data = resp.json()
            if data.get("error") and "blocked" in str(data.get("error", "")).lower():
                log.error("Firecrawl returned blocked error: %s", data.get("error"))
                sys.exit(1)
            links = data.get("data", {}).get("links", [])
            return links
        except httpx.HTTPStatusError as e:
            log.warning("Firecrawl scrape failed: %s", e)
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAYS[attempt])
        except httpx.HTTPError as e:
            log.warning("Firecrawl request error: %s, retry in %ds", e, RETRY_DELAYS[attempt])
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAYS[attempt])
    return []


def firecrawl_batch_scrape(urls: list[str], client: httpx.Client) -> list[dict]:
    """Batch-scrape ad pages via Firecrawl, poll until complete."""
    if not urls:
        return []

    # Submit batch
    for attempt in range(MAX_RETRIES):
        try:
            resp = client.post(
                f"{FIRECRAWL_BASE}/batch/scrape",
                json={"urls": urls, "formats": ["markdown"]},
                timeout=60.0,
            )
            if resp.status_code == 402:
                log.error("Firecrawl credits exhausted (HTTP 402) — aborting")
                sys.exit(1)
            resp.raise_for_status()
            batch_data = resp.json()
            break
        except httpx.HTTPError as e:
            log.warning("Firecrawl batch submit failed: %s", e)
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAYS[attempt])
            else:
                return []
    else:
        return []

    batch_id = batch_data.get("id")
    if not batch_id:
        log.error("Firecrawl batch response missing 'id': %s", batch_data)
        return []

    log.info("Firecrawl batch submitted: %s (%d URLs)", batch_id, len(urls))

    # Poll until complete
    poll_url = f"{FIRECRAWL_BASE}/batch/scrape/{batch_id}"
    max_polls = 60  # 60 × 5s = 5min max
    for poll in range(max_polls):
        time.sleep(5)
        try:
            resp = client.get(poll_url, timeout=30.0)
            resp.raise_for_status()
            poll_data = resp.json()
            status = poll_data.get("status")
            log.debug("Batch poll %d/%d: status=%s", poll + 1, max_polls, status)
            if status == "completed":
                return poll_data.get("data", [])
            if status in ("failed", "cancelled"):
                log.error("Firecrawl batch %s: %s", batch_id, status)
                return []
        except httpx.HTTPError as e:
            log.warning("Batch poll failed: %s", e)

    log.error("Firecrawl batch %s timed out after %ds", batch_id, max_polls * 5)
    return []


# ── Main ──────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scrape B2C leads via Firecrawl (Gumtree buyer-intent ads, HelloPeter complaints)"
    )
    parser.add_argument("source", choices=["gumtree", "hellopeter"], help="Source to scrape")
    parser.add_argument("--max", type=int, default=15, dest="max_ads", help="Max ads to collect (default: 15)")
    parser.add_argument("--out", type=str, default=None, help="Output JSON file path (default: stdout)")
    return parser.parse_args()


def run_gumtree(args: argparse.Namespace, client: httpx.Client) -> list[dict]:
    """Phase 1+2: collect Gumtree buyer-intent ad leads."""
    results: list[dict] = []
    seen_adids: set[str] = set()
    all_ad_urls: list[str] = []
    seen_urls: set[str] = set()

    # Phase 1: collect ad links from all search pages
    for search_url in SEARCH_URLS:
        if len(seen_urls) >= args.max_ads * 3:
            break
        log.info("Fetching listing: %s", search_url)
        links = firecrawl_scrape_links(search_url, client)
        ad_links = extract_ad_links(links)
        log.info("Found %d ad links from listing", len(ad_links))
        for link in ad_links:
            adid = extract_adid(link)
            if adid and adid in seen_adids:
                continue
            if link not in seen_urls:
                seen_urls.add(link)
                if adid:
                    seen_adids.add(adid)
                all_ad_urls.append(link)

    if not all_ad_urls:
        log.warning("No Gumtree ad links collected")
        return []

    ad_urls_to_scrape = all_ad_urls[:args.max_ads]
    log.info("Batch-scraping %d Gumtree ad pages", len(ad_urls_to_scrape))

    # Phase 2: batch-scrape ad pages
    batch_results = firecrawl_batch_scrape(ad_urls_to_scrape, client)
    log.info("Batch returned %d results", len(batch_results))

    for item in batch_results:
        metadata = item.get("metadata", {})
        source_url = metadata.get("sourceURL") or metadata.get("url") or ""
        markdown = item.get("markdown", "")
        if not markdown:
            log.debug("Empty markdown for %s — skipping", source_url)
            continue
        lead = parse_ad_markdown(markdown, source_url)
        if lead.get("adid") and lead["adid"] in seen_adids and source_url not in ad_urls_to_scrape:
            log.debug("Duplicate adid %s — skipping", lead["adid"])
            continue
        results.append(lead)
        log.info(
            '✓ "%s" | phone: %s | loc: %s',
            (lead.get("title") or "?")[:60],
            lead.get("phone") or "none",
            lead.get("location") or "?",
        )

    return results


def run_hellopeter(args: argparse.Namespace, client: httpx.Client) -> list[dict]:
    """Scrape HelloPeter competitor complaint reviews for churn leads."""
    results: list[dict] = []
    seen_urls: set[str] = set()
    all_review_urls: list[str] = []

    # Phase 1: scrape each competitor's reviews listing page for review links
    for target in HELLOPETER_TARGETS:
        slug = target["slug"]
        competitor = target["competitor"]
        listing_url = f"{HELLOPETER_BASE}/{slug}/reviews"
        log.info("Fetching HelloPeter reviews: %s (%s)", listing_url, competitor)
        links = firecrawl_scrape_links(listing_url, client)
        review_links = extract_review_links(links, slug)
        log.info("Found %d review links for %s", len(review_links), competitor)
        for link in review_links:
            if link not in seen_urls:
                seen_urls.add(link)
                all_review_urls.append((link, competitor))
        if len(all_review_urls) >= args.max_ads * 2:
            break

    if not all_review_urls:
        log.warning("No HelloPeter review links collected — site may block scraping")
        return []

    # Apply max limit
    to_scrape = all_review_urls[:args.max_ads]
    urls_only = [u for u, _ in to_scrape]
    url_to_competitor = {u: c for u, c in to_scrape}

    log.info("Batch-scraping %d HelloPeter review pages", len(urls_only))

    # Phase 2: batch-scrape review pages
    batch_results = firecrawl_batch_scrape(urls_only, client)
    log.info("Batch returned %d results", len(batch_results))

    for item in batch_results:
        metadata = item.get("metadata", {})
        source_url = metadata.get("sourceURL") or metadata.get("url") or ""
        markdown = item.get("markdown", "")
        if not markdown:
            log.debug("Empty markdown for %s — skipping", source_url)
            continue
        competitor = url_to_competitor.get(source_url, "Unknown")
        lead = parse_hellopeter_markdown(markdown, source_url, competitor)
        results.append(lead)
        log.info(
            '✓ HelloPeter: %s | reviewer: %s | loc: %s',
            competitor,
            lead.get("reviewer_name") or "?",
            lead.get("location") or "?",
        )

    return results


def main() -> None:
    args = parse_args()

    log_dir = Path.home() / "vault/projects/cogstack-leadgen/logs"
    setup_logging(log_dir, "scraper")

    if not FIRECRAWL_API_KEY:
        log.error("FIRECRAWL_API_KEY not set in ~/.hermes/.env")
        sys.exit(1)

    headers = {
        "Authorization": f"Bearer {FIRECRAWL_API_KEY}",
        "Content-Type": "application/json",
    }

    with httpx.Client(headers=headers) as client:
        if args.source == "gumtree":
            results = run_gumtree(args, client)
        else:
            results = run_hellopeter(args, client)

    log.info("Done — %d leads", len(results))

    output = json.dumps(results, indent=2, ensure_ascii=False)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(output, encoding="utf-8")
        log.info("Written to %s", args.out)
    else:
        print(output)


if __name__ == "__main__":
    main()
