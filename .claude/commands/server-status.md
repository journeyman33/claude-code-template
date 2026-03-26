---
description: Check health of all services across pi4, cogstack, and bigtorig
---

# Server Status

Check the health of all 3 servers and report a unified dashboard.

## For each server: pi4 (localhost), cogstack, bigtorig

Run the following checks via SSH (use `bash -c` locally for pi4):

### 1. Systemd user services

```bash
systemctl --user list-units --type=service --state=running 2>/dev/null
```

Look for: `openclaw-gateway`, `openclaw-antfarm`, any proxy services.
Flag any expected services that are missing.

### 2. Docker containers

```bash
docker ps --format "{{.Names}}: {{.Status}}"
```

Flag any containers where Status contains `unhealthy` or `Restarting`.

### 3. Disk usage

```bash
df -h / | tail -1
```

Flag if used% > 80%.

### 4. Memory

```bash
free -h | grep Mem
```

### 5. OpenAI/Codex auth (per server)

Check `~/.openclaw/agents/main/agent/auth-profiles.json` on each server:

```bash
python3 -c "
import json, time
try:
    d = json.load(open('/home/charles/.openclaw/agents/main/agent/auth-profiles.json'))
    profile = d.get('profiles', {}).get('openai-codex:default', {})
    stats = d.get('usageStats', {}).get('openai-codex:default', {})
    errors = stats.get('errorCount', 0)
    last_used = stats.get('lastUsed', 0)
    expires = profile.get('expires', 0)
    now_ms = time.time() * 1000
    days_since_used = (now_ms - last_used) / 86400000 if last_used else 999
    days_until_expiry = (expires - now_ms) / 86400000 if expires else 0
    expiry_flag = ' EXPIRED' if days_until_expiry <= 0 else (' expiry_warn' if days_until_expiry < 3 else '')
    print(f'errors={errors} days_since_used={days_since_used:.1f} days_until_expiry={days_until_expiry:.1f}{expiry_flag}')
except Exception as e:
    print(f'ERROR: {e}')
"
```

- Flag if `errorCount > 5` (agents failing)
- Flag if `days_since_used > 14` (stale/unused)
- Flag ⚠ if `days_until_expiry < 3` (token about to expire — cron should have caught this)
- Flag ✗ if `days_until_expiry <= 0` (token expired — run `openclaw models auth login --provider openai-codex` to re-auth)
- Note: token auto-refreshes every 7 days via cron (`~/.openclaw/refresh-codex-token.py`); manual re-auth only needed if refresh token itself expires

## API Credits (run once — all servers share the same OpenRouter key)

### OpenRouter balance

Use the management key to query the `or-feb26` key (the active openclaw key) by name:

```bash
MGMTKEY=$(grep OPENROUTER_MANAGEMENT_KEY ~/.openclaw/.env.hugo | cut -d= -f2)
curl -s https://openrouter.ai/api/v1/keys \
  -H "Authorization: Bearer $MGMTKEY" | python3 -c "
import json, sys
keys = json.load(sys.stdin).get('data', [])
def fmt_key(name):
    key = next((k for k in keys if k.get('name') == name), None)
    if not key:
        return f'{name}: not found'
    monthly = key.get('usage_monthly', 0)
    limit = key.get('limit')
    remaining = key.get('limit_remaining')
    if remaining is not None:
        status = 'CRITICAL' if remaining < 1 else ('LOW' if remaining < 5 else 'ok')
        return f'{name}: remaining=\${remaining:.2f} used_monthly=\${monthly:.2f} limit=\${limit:.2f} status={status}'
    elif limit is not None:
        rem = limit - monthly
        status = 'CRITICAL' if rem < 1 else ('LOW' if rem < 5 else 'ok')
        return f'{name}: remaining=\${rem:.2f} used_monthly=\${monthly:.2f} limit=\${limit:.2f} status={status}'
    else:
        return f'{name}: used_monthly=\${monthly:.2f} pay-as-you-go'
print(fmt_key('or-openclaw'))
print(fmt_key('or-feb26'))
"
```

- Flag ⚠ if `status=LOW` (remaining < $5)
- Flag ✗ if `status=CRITICAL` (remaining < $1 — openclaw agents will go down)
- If no limit set: show `$X.XX/mo  pay-as-you-go`

### Anthropic

OAuth Pro subscription — no credit balance to check. Just show `OAuth Pro ✓`.

## Known services per server

**pi4:**
- systemd: `openclaw-gateway`, `openclaw-antfarm`, `openclaw-antfarm-proxy`, `openclaw-docker-proxy`
- docker: Mission Control (3000), SearXNG (8080), RustDesk

**cogstack:**
- systemd: `openclaw-gateway`, `openclaw-antfarm`, `openclaw-coder-proxy`
- docker: fastapi, nextjs, n8n, grafana, supabase-db, gotrue, caddy, qdrant, redis, clickhouse, prometheus, neo4j, arcane, cadvisor

**bigtorig:**
- systemd: `openclaw-gateway`, `openclaw-antfarm`
- docker: supabase stack, n8n, flowise, open-webui, qdrant, redis, neo4j, caddy, claude-router, maui-api, arcane, dentist-ai-gateway, tender-app

## Output Format

Produce a dashboard like:

```
SERVER STATUS — <date>
═══════════════════════════════════════

API CREDITS
  Anthropic         OAuth Pro ✓
  or-openclaw       $30.00 remaining ✓  (openclaw agents — all 3 servers)
  or-feb26          $8.39 remaining ✓   (personal use)
  OpenAI/Codex      OAuth ✓ (pi4 errors=0, cogstack errors=0, bigtorig errors=0)

PI4
  openclaw-gateway        ✓ running
  openclaw-antfarm        ✓ running
  disk                    24G / 917G (3%)
  memory                  4.1Gi / 7.6Gi used

COGSTACK
  openclaw-gateway        ✓ running
  openclaw-antfarm        ✓ running
  fastapi                 ✓ healthy
  ...
  disk                    ?? / ??

BIGTORIG
  openclaw-gateway        ✓ running
  claude-router           ✗ RESTARTING ← flag this
  mcp-docker              ⚠ unhealthy ← flag this
  disk                    ?? / ??

ISSUES REQUIRING ATTENTION
  - bigtorig: claude-router is restarting
  - bigtorig: mcp-docker is unhealthy
  - OpenRouter: $0.80 remaining — CRITICAL, agents will go down
```

Use ✓ for healthy, ⚠ for warning (< $5 credits / unhealthy), ✗ for critical (< $1 / down/restarting).
Always end with an ISSUES section — "None" if everything is clean.
