#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "httpx>=0.28.1",
#     "python-dotenv>=1.2.1",
# ]
# ///
# =============================================================
# search.py — B2C lead search via Exa + Tavily
# Finds competitor churn, forum posts, theft signals beyond Gumtree.
# =============================================================
# Usage:
#   uv run scripts/search.py                         # all default B2C queries
#   uv run scripts/search.py --type=churn            # Hellopeter/competitor churn
#   uv run scripts/search.py --type=forums           # forum + Reddit signals
#   uv run scripts/search.py --type=theft            # recent theft → tracking need
#   uv run scripts/search.py --query "custom query"  # ad hoc
#
# Output: JSON array to stdout (same schema as scrape.py)
# =============================================================

import argparse
import hashlib
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv(Path.home() / ".hermes/.env")

# ── Logging ──────────────────────────────────────────────────

log = logging.getLogger("search")


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


# ── Credentials ──────────────────────────────────────────────

EXA_API_KEY = os.environ.get("EXA_API_KEY")
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY")

EXA_URL = "https://api.exa.ai/search"
TAVILY_URL = "https://api.tavily.com/search"

# ── Retry constants ──────────────────────────────────────────

MAX_RETRIES = 3
RETRY_DELAYS = [2, 5, 15]

# ── Default B2C queries by type ──────────────────────────────

# Tier 2 — Competitor churn (cancel signals)
CHURN_QUERIES = [
    "unhappy Netstar customer South Africa wants to cancel",
    "Tracker Connect complaints South Africa bad service",
    "Cartrack alternative South Africa looking to switch",
    "cancel Cartrack South Africa looking for alternative",
    "Cartrack too expensive alternative South Africa",
    "MiX Telematics complaints South Africa bad service",
    "Beame tracker complaints South Africa",
    "cancel Netstar South Africa tracker alternative",
    "site:hellopeter.com Cartrack complaint cancel",
    "site:hellopeter.com Tracker Connect unhappy customer",
    "site:hellopeter.com Netstar complaint South Africa",
    "site:hellopeter.com MiX Telematics bad service",
]

# Tier 3 — Forum + community signals
FORUM_QUERIES = [
    "need car tracker South Africa MyBroadband forum",
    "want vehicle tracking system South Africa",
    "looking for GPS tracker Johannesburg Cape Town",
    "which car tracker South Africa recommend",
    "tracker installation Johannesburg price quote",
    "tracker installation Cape Town price quote",
    "Reddit r/southafrica car tracker recommendation",
    "MyBroadband car tracker South Africa recommendation 2026",
]

# Tier 3 — Life events: new car purchases (Exa/Tavily finds these better than Gumtree)
LIFE_EVENT_QUERIES = [
    "just bought a Fortuner need tracker South Africa",
    "just bought Toyota Hilux need vehicle tracker",
    "just bought Land Cruiser need GPS tracker South Africa",
    "just bought Ford Ranger need tracker installed",
    "just bought new car need tracker Gauteng",
    "site:autotrader.co.za buyer inquiry tracker",
    "site:cars.co.za \"just bought\" tracker South Africa",
    "Facebook \"just bought\" Fortuner tracker South Africa",
    "OLX South Africa new car buyer tracker needed",
    "AutoTrader SA recently sold Fortuner buyer contact tracker",
]

# Tier 1 — Theft signals (fear = urgent buyer)
THEFT_QUERIES = [
    "car stolen Johannesburg need GPS tracker 2026",
    "vehicle hijacked South Africa tracking device",
    "bakkie stolen Gauteng want tracker installed",
    "car stolen no tracker South Africa",
    "vehicle stolen Cape Town GPS tracking",
    "bakkie stolen Cape Town",
    "vehicle stolen Johannesburg no tracking",
    "car hijacked Pretoria need tracker",
]

# Tier 1 — New car purchases (life event = high intent)
NEW_CAR_QUERIES = [
    "just bought car need tracker South Africa",
    "just bought a Fortuner need tracker",
    "just bought Land Cruiser South Africa tracker",
    "just bought a Ranger bakkie tracker South Africa",
    "just bought car insurance requires tracker South Africa",
    "new car purchase tracker Gauteng",
    "just bought SUV Johannesburg tracker needed",
    "Facebook just bought Fortuner South Africa",
]

# Tier 1 — Insurance forced buyers (very high intent)
INSURANCE_QUERIES = [
    "car insurance requires tracker South Africa",
    "insurance tracking device required South Africa",
    "insurance company tracker requirement South Africa",
    "insurance won't cover car without tracker South Africa",
    "need tracker for insurance South Africa urgent",
]

ALL_QUERIES = {
    "churn": CHURN_QUERIES,
    "forums": FORUM_QUERIES,
    "theft": THEFT_QUERIES,
    "new_car": NEW_CAR_QUERIES,
    "insurance": INSURANCE_QUERIES,
    "life_events": LIFE_EVENT_QUERIES,
}


# ── API calls ─────────────────────────────────────────────────

def exa_search(query: str, client: httpx.Client) -> list[dict]:
    """Search Exa for B2C signals."""
    if not EXA_API_KEY:
        log.warning("EXA_API_KEY not set — skipping Exa search")
        return []

    payload = {
        "query": query,
        "numResults": 3,
        "type": "neural",
        "useAutoprompt": True,
        "contents": {"text": True, "highlights": True},
    }
    headers = {"x-api-key": EXA_API_KEY, "Content-Type": "application/json"}

    for attempt in range(MAX_RETRIES):
        try:
            resp = client.post(EXA_URL, json=payload, headers=headers, timeout=30.0)
            if resp.status_code == 429:
                retry_after = int(resp.headers.get("Retry-After", RETRY_DELAYS[attempt]))
                log.warning("Exa rate limit, retry in %ds", retry_after)
                time.sleep(retry_after)
                continue
            if resp.status_code >= 500:
                log.warning("Exa server error %d, retry in %ds", resp.status_code, RETRY_DELAYS[attempt])
                time.sleep(RETRY_DELAYS[attempt])
                continue
            resp.raise_for_status()
            results = resp.json().get("results", [])
            log.debug("Exa query '%s': %d results", query[:50], len(results))
            return results
        except httpx.HTTPError as e:
            log.warning("Exa request failed: %s, retry in %ds", e, RETRY_DELAYS[attempt])
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAYS[attempt])
    return []


def tavily_search(query: str, client: httpx.Client) -> list[dict]:
    """Search Tavily for B2C signals."""
    if not TAVILY_API_KEY:
        log.warning("TAVILY_API_KEY not set — skipping Tavily search")
        return []

    payload = {
        "api_key": TAVILY_API_KEY,
        "query": query,
        "search_depth": "advanced",
        "max_results": 3,
    }

    for attempt in range(MAX_RETRIES):
        try:
            resp = client.post(TAVILY_URL, json=payload, timeout=30.0)
            if resp.status_code == 429:
                retry_after = int(resp.headers.get("Retry-After", RETRY_DELAYS[attempt]))
                log.warning("Tavily rate limit, retry in %ds", retry_after)
                time.sleep(retry_after)
                continue
            if resp.status_code >= 500:
                log.warning("Tavily server error %d, retry in %ds", resp.status_code, RETRY_DELAYS[attempt])
                time.sleep(RETRY_DELAYS[attempt])
                continue
            resp.raise_for_status()
            results = resp.json().get("results", [])
            log.debug("Tavily query '%s': %d results", query[:50], len(results))
            return results
        except httpx.HTTPError as e:
            log.warning("Tavily request failed: %s, retry in %ds", e, RETRY_DELAYS[attempt])
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAYS[attempt])
    return []


def url_to_adid(url: str) -> str:
    """Generate a stable dedup key from a URL hash."""
    return hashlib.md5(url.encode()).hexdigest()[:12]


def exa_result_to_lead(result: dict) -> dict:
    """Adapt an Exa search result to the raw lead schema."""
    url = result.get("url", "")
    text = result.get("text", "") or ""
    highlights = result.get("highlights", [])
    description = " ".join(highlights) if highlights else text[:500]
    return {
        "title": result.get("title", ""),
        "description": description,
        "phone": None,
        "location": None,
        "price": None,
        "adid": url_to_adid(url),
        "url": url,
        "source": "Exa",
        "competitor": None,
        "pain_point": None,
        "scraped_at": datetime.now(timezone.utc).isoformat(),
    }


def tavily_result_to_lead(result: dict) -> dict:
    """Adapt a Tavily search result to the raw lead schema."""
    url = result.get("url", "")
    return {
        "title": result.get("title", ""),
        "description": result.get("content", "")[:500],
        "phone": None,
        "location": None,
        "price": None,
        "adid": url_to_adid(url),
        "url": url,
        "source": "Tavily",
        "competitor": None,
        "pain_point": None,
        "scraped_at": datetime.now(timezone.utc).isoformat(),
    }


# ── Main ──────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="B2C search via Exa + Tavily (competitor churn, forums, theft signals)"
    )
    parser.add_argument(
        "--type",
        choices=["churn", "forums", "theft", "new_car", "insurance", "life_events", "all"],
        default="all",
        help="Query type (default: all)",
    )
    parser.add_argument("--query", type=str, default=None, help="Ad hoc search query")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    log_dir = Path.home() / "vault/projects/cogstack-leadgen/logs"
    setup_logging(log_dir, "search")

    if not EXA_API_KEY and not TAVILY_API_KEY:
        log.error("Neither EXA_API_KEY nor TAVILY_API_KEY set in ~/.hermes/.env")
        sys.exit(1)

    # Build query list
    if args.query:
        queries = [args.query]
    elif args.type == "all":
        queries = CHURN_QUERIES + THEFT_QUERIES + NEW_CAR_QUERIES + INSURANCE_QUERIES + LIFE_EVENT_QUERIES + FORUM_QUERIES
    else:
        queries = ALL_QUERIES[args.type]

    results: list[dict] = []
    seen_urls: set[str] = set()

    with httpx.Client() as client:
        for query in queries:
            log.info("Searching: %s", query)

            # Exa
            exa_results = exa_search(query, client)
            for r in exa_results:
                url = r.get("url", "")
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    results.append(exa_result_to_lead(r))

            # Tavily
            tavily_results = tavily_search(query, client)
            for r in tavily_results:
                url = r.get("url", "")
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    results.append(tavily_result_to_lead(r))

    log.info("Done — %d unique results", len(results))
    print(json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
