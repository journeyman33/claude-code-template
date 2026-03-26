---
description: Pull memory and project context from all CogStack servers into Ugolino's local context
argument-hint: [server] — optional: pi4 | bigtorig | cogstack | all (default: all)
---

# Sync Memories — Cross-Network Context Pull

Pull Claude Code memory files, active project state, and OpenClaw agent context from the
CogStack network into Ugolino's working context. Run this at the start of any session where
you'll be working across servers, or whenever you've been away for a while.

## Target Servers

```
SERVERS="pi4 bigtorig cogstack"
```

If `$ARGUMENTS` is one of `pi4`, `bigtorig`, or `cogstack`, sync only that server.
Otherwise sync all three.

---

## Phase 1: Claude Code Memory (all servers)

For each server, pull all Claude Code auto-memory files:

```bash
ssh <server> "find ~/.claude/projects -name '*.md' 2>/dev/null | head -40"
ssh <server> "cat ~/.claude/projects/*/memory/*.md 2>/dev/null"
ssh <server> "cat ~/.claude/projects/*/CLAUDE.md 2>/dev/null"
```

Read each file that is returned. Summarise key facts extracted per server.

---

## Phase 2: OpenClaw Agent Memory (all servers)

Each server runs OpenClaw agents. Pull their memory stores:

```bash
# OpenClaw memory files
ssh <server> "find ~/.openclaw -name 'memory*.md' -o -name 'MEMORY.md' 2>/dev/null | head -20"
ssh <server> "cat ~/.openclaw/agents/*/memory/*.md 2>/dev/null"

# OpenClaw agent configs (names, models, skills)
ssh <server> "cat ~/.openclaw/agents/main/agent/agent.json 2>/dev/null"
```

---

## Phase 3: Active Project State (all servers)

For each server, find active projects and check their state:

```bash
# Recent git activity across all projects
ssh <server> "find ~ -name '.git' -maxdepth 4 -not -path '*/.openclaw/*' 2>/dev/null \
  | while read d; do \
      proj=\$(dirname \$d); \
      echo \"=== \$proj ===\"; \
      git -C \$proj log --oneline -3 2>/dev/null; \
      git -C \$proj status --short 2>/dev/null | head -5; \
    done"

# Any running services or docker containers
ssh <server> "docker ps --format '{{.Names}}: {{.Status}}' 2>/dev/null | grep -v Exited | head -20"
ssh <server> "systemctl --user list-units --type=service --state=running 2>/dev/null | grep -v systemd"
```

---

## Phase 4: Write Consolidated Memory File

After reading all remote data, write a consolidated snapshot to:
`~/.claude/network-memory.md`

Use this exact structure:

```markdown
# CogStack Network Memory Snapshot
_Synced: <ISO timestamp>_

---

## PI4 — Hugo Personal Agent

### Claude Code Projects
<bullet list of projects and last 3 commits>

### OpenClaw Memory Highlights
<key facts extracted from openclaw memory files>

### Active Services
<running docker containers and systemd services>

### Uncommitted Work
<any dirty git repos>

---

## BIGTORIG — Bigtorig Runtime + Coder

### Claude Code Projects
<bullet list of projects and last 3 commits>

### OpenClaw Memory Highlights
<key facts extracted>

### Active Services
<running containers>

### Uncommitted Work
<dirty repos>

---

## COGSTACK — Cogstack Runtime + CTIS

### Claude Code Projects
<bullet list of projects and last 3 commits>

### OpenClaw Memory Highlights
<key facts extracted>

### Active Services
<running containers — fastapi, nextjs, n8n, etc.>

### Uncommitted Work
<dirty repos>

---

## Cross-Network Flags

<List anything that needs attention:>
- Uncommitted work on any server
- Services in unhealthy or restarting state
- OpenClaw agents with high error counts
- Projects with diverged branches
```

---

## Phase 5: Reference from CLAUDE.md

After writing `~/.claude/network-memory.md`, append the following line to
`~/ugolino/CLAUDE.md` if it isn't already there:

```markdown
## Live Network Memory
See `~/.claude/network-memory.md` for the latest synced state of pi4, bigtorig, and cogstack.
Run `/sync-memories` to refresh.
```

---

## Output Report

Produce a concise terminal summary:

```
MEMORY SYNC — <timestamp>
═══════════════════════════════════════════════

PI4
  Claude Code projects found : <N>
  OpenClaw memory files      : <N>
  Uncommitted repos          : <list or "none">
  Flags                      : <issues or "✓ clean">

BIGTORIG
  Claude Code projects found : <N>
  OpenClaw memory files      : <N>
  Uncommitted repos          : <list or "none">
  Flags                      : <issues or "✓ clean">

COGSTACK
  Claude Code projects found : <N>
  OpenClaw memory files      : <N>
  Uncommitted repos          : <list or "none">
  Flags                      : <issues or "✓ clean">

Snapshot written → ~/.claude/network-memory.md

SUGGESTED NEXT STEP
  <Based on what was found — e.g., "bigtorig has uncommitted work in /opt/ctis — run /prime-remote bigtorig /opt/ctis to investigate">
```

Keep output scannable. Bullets and headers only — no prose paragraphs.
