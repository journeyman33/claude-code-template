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

PI4
  openclaw-gateway    ✓ running
  openclaw-antfarm    ✓ running
  disk                24G / 917G (3%)

COGSTACK
  openclaw-gateway    ✓ running
  openclaw-antfarm    ✓ running
  fastapi             ✓ healthy
  ...
  disk                ?? / ??

BIGTORIG
  openclaw-gateway    ✓ running
  claude-router       ✗ RESTARTING ← flag this
  mcp-docker          ⚠ unhealthy ← flag this
  disk                ?? / ??

ISSUES REQUIRING ATTENTION
  - bigtorig: claude-router is restarting
  - bigtorig: mcp-docker is unhealthy
```

Use ✓ for healthy, ⚠ for unhealthy, ✗ for down/restarting.
Always end with an ISSUES section — "None" if everything is clean.
