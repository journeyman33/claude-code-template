# Claude Code — Ugolino Hacks Reference
_Compiled March 2026 — post to Ugolino for instant awareness_

Status legend: ✅ Already set up | 🔧 Needs setup | 💡 Technique only

---

## FROM THE VIDEO: 9 Hacks

### Hack 1 — CLI over MCP + Skills pairing 💡
Move away from MCP servers wherever a CLI equivalent exists.
CLIs live in the terminal — same place Claude Code lives. Zero overhead, lower tokens, often more functionality.

**Rule:** Every time you add a CLI tool, pair it with a skill so Ugolino knows how to use it.

Your stack already does this:
- `gh` CLI (GitHub) ✅
- `docker` / `docker compose` CLI ✅
- `uv` CLI (Python) ✅
- `bun` CLI (Node) ✅

CLIs to consider adding:
```bash
# Notion CLI (instead of Notion MCP)
npm install -g notion-cli-js

# n8n CLI
npm install -g n8n

# Supabase CLI
npm install -g supabase
```
Then create a skill in `.claude/skills/<tool>/SKILL.md` for each one.

---

### Hack 2 — /btw Sidebar Conversations 💡
**Released March 11, 2026. Requires Claude Code v2.1.72+** ✅ (you're on 2.1.84)

Ask a question without adding to the conversation history or interrupting a running task.

```
/btw what port does n8n run on in our stack?
/btw did we commit the Caddyfile changes?
/btw what was the name of that Notion database?
```

**How it works:**
- Spawns an ephemeral agent with full conversation visibility but no tools
- Answer appears in a dismissible overlay — press Space/Enter/Escape to dismiss
- Zero context cost — reuses prompt cache
- Works even while Claude is mid-response on another task

**The key distinction:**
- `/btw` — asks about what Claude already knows (no tools, low cost)
- subagent — goes out to find something new (has tools, higher cost)

**Best use cases for Ugolino:**
```
# While a long SSH task is running:
/btw what's the bigtorig neo4j container name again?
/btw did we set CLAUDE_AUTOCOMPACT_PCT_OVERRIDE in settings?
```

---

### Hack 3 — /hook for Sound Notifications 🔧
Get an audio ping when Ugolino finishes a task — essential when you have multiple sessions running.

```
/hook Play a subtle ding sound when you complete a task
```

For WSL2 (desktop), point it at a Windows sound file:
```
/hook Run: powershell.exe -c "(New-Object Media.SoundPlayer 'C:\Windows\Media\ding.wav').PlaySync()" when task completes
```

Or create a hook in `~/.claude/hooks/`:
```json
{
  "hooks": {
    "Stop": [
      {
        "command": "powershell.exe -c \"(New-Object Media.SoundPlayer 'C:\\Windows\\Media\\ding.wav').PlaySync()\""
      }
    ]
  }
}
```

---

### Hack 4 — /clear Early and Often 💡
**Context rot is real.** Performance degrades as context fills:

| Context Used | Efficiency (Opus) |
|---|---|
| 256k tokens | ~92% |
| 500k tokens | ~85% |
| 1M tokens | ~78% |

**Rule:** Clear at 20-25% context usage. You have `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE: 75` ✅ which auto-compacts at 75% — but manual `/clear` at task boundaries is still better.

```
/clear          # Wipes history, starts fresh (file edits are preserved)
/compact        # Summarises history, preserves thread (use between tasks)
```

**When to use which:**
- `/compact` — switching sub-tasks within the same project
- `/clear` — completely different task or project

---

### Hack 5 — Status Line ✅
You already have this set up and running. Your statusline shows:
```
DELL-WIN10 | OAuth (Pro) | Sonnet 4.6 | /home/charles/ugolino | context: % | Telegram: active
```

**To enhance it with rate limits** (add to `statusline-command.sh`):
```bash
# The rate_limits field is now available in statusline scripts:
# rate_limits.api.used_percentage
# rate_limits.api.resets_at
```

**Tip:** Run `/status` to check the current status overlay at any time.

---

### Hack 6 — Skill Creator Skill from Anthropic 🔧
The most powerful meta-skill. Not just creates skills — also modifies, tests, and benchmarks them with quantifiable performance scores.

Install it:
```bash
# Inside Claude Code:
/plugin install skill-creator@claude-plugins-official
```

Usage:
```
/skill-creator create a skill for the Notion CLI that handles database queries
/skill-creator improve my server-status command and benchmark it
/skill-creator test my sync-memories command and give me a performance score
```

**Why this matters for you:** Use it to iterate on your existing commands (server-status, sync-memories, prime-remote) with actual metrics rather than vibes.

---

### Hack 7 — Agent Teams ✅
Already enabled: `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS: "1"` in settings.json.

**Key rules:**
- Must explicitly say "create an agent team" — it won't activate on its own
- Each teammate gets its own context window and can message other teammates directly
- Use tmux — each teammate opens in its own split pane (Shift+Down to cycle)
- Cost: ~7x normal token usage — use sparingly on Pro plan

**Best invocation pattern:**
```
Create an agent team for cogstack-leadgen:
- Teammate 1: Gumtree scraper (curl_cffi + BeautifulSoup4) — focus on anti-bot evasion
- Teammate 2: n8n webhook integration — focus on Notion CRM schema mapping
Have them share findings before implementation.
```

**Kill all background agents instantly:** `Ctrl+F`

---

### Hack 8 — Plan Mode + Open-Ended Questions 💡
In plan mode, don't just ask it to do things. Ask it what you're missing.

**Power prompts to use in plan mode:**
```
What am I not thinking about here?
What are the unintended consequences of this approach?
What would a senior DevOps engineer be concerned about?
What would break this in production?
What assumptions are you making that might be wrong?
```

**Toggle plan mode:** `Shift+Tab` (cycles: auto → plan → bypass → normal)

This is especially valuable for infrastructure work — Ugolino touching pi4/bigtorig/cogstack benefits from a planning pass before execution.

---

### Hack 9 — Obsidian as Second Brain 💡
Obsidian is a free markdown vault that integrates beautifully with Claude Code's markdown-first output.

**The concept:** Point Claude Code at a folder you've designated as an Obsidian vault. Everything Claude writes as markdown becomes navigable in Obsidian with graph view showing connections.

**Relevance for you:**
- Your `~/ugolino/` directory could double as an Obsidian vault
- CLAUDE.md, sync-memories output, network-memory.md all become Obsidian nodes
- Graph view makes cross-project relationships visible

**Setup:**
```bash
# Download Obsidian (Windows) and point vault at:
\\wsl$\Ubuntu\home\charles\ugolino
# Or use a Windows-native folder synced to WSL
```

**Best use case for CogStack:** Knowledge base for CTIS tender intelligence — not traditional coding.

---

## BONUS HACKS (beyond the video)

### B1 — Shell Aliases 🔧
Add to `~/.zshrc`:
```bash
alias c='claude'
alias cc='cd ~/ugolino && claude --channels plugin:telegram@claude-plugins-official'
alias cr='claude --resume'
alias ugo='~/ugolino/start-ugo.sh'
```

### B2 — /vim Mode 💡
You use Zed in vim mode — Claude Code has native vim keybindings for the prompt input:
```
/vim    # toggle vim mode in the prompt
```
Full vim motions: h/j/k/l, w/b, d/c/y, text objects (iw, aw, i"), 0/$.

### B3 — /fork and /rewind 💡
```
/fork experiment-attempt-1    # clone current conversation, keep original safe
/rewind                        # roll back to an earlier point
```
Use `/fork` before any risky experiment — the original conversation is untouched.

### B4 — /effort Command 💡
Control model reasoning depth per-task:
```
/effort low     # fast, cheap — good for mechanical tasks
/effort medium  # default
/effort high    # deep reasoning — use "ultrathink" keyword on Opus
```

Also available as frontmatter in commands:
```yaml
---
description: Quick git status check
effort: low
model: haiku
---
```

### B5 — Ctrl+T Task List 💡
When Claude is working through a multi-step task:
```
Ctrl+T    # toggle task list overlay
```
Shows pending/in-progress/complete tasks. Persists across context compactions.

### B6 — Ctrl+R History Search 💡
```
Ctrl+R    # reverse history search through previous Claude Code inputs
```
Same as zsh Ctrl+R but scoped to Claude Code session history.

### B7 — Git Worktrees for Parallel Work 🔧
Run two Claude sessions on different features simultaneously without branch conflicts:
```bash
# Create a worktree for a second feature
git worktree add ../ugolino-feature-2 feat/content-platform

# Open second Claude session in it
cd ../ugolino-feature-2 && claude
```
Each session has its own working directory and branch — no conflicts.

### B8 — Lazy-Load MCP Tools 🔧
Saves context tokens on startup — only loads MCP tool definitions when actually needed:
```json
// Add to ~/.claude/settings.json
"mcpLazyLoad": true
```

### B9 — /compact with Instructions 💡
Don't just compact — tell it what to preserve:
```
/compact keep all information about the bigtorig docker stack and neo4j issue
/compact preserve the Notion CRM schema decisions
```
Raw `/compact` may discard critical details. Directed compaction keeps what matters.

### B10 — @file Instant Context Loading 💡
Add any file to context instantly without a prompt:
```
@~/.claude/network-memory.md review this and tell me what needs updating
@~/ugolino/CLAUDE.md check if anything is outdated
@/path/to/docker-compose.yml what services are unhealthy?
```

### B11 — Disable Auto-Updates 🔧
Prevents surprise version changes mid-workflow (useful when system prompt patches are applied):
```json
// Add to ~/.claude/settings.json
"autoUpdates": false
```
Update manually with `claude update` when ready.

### B12 — /copy Command 💡
Interactive picker for copying code blocks from Claude's output — useful when Telegram truncates long responses:
```
/copy    # opens interactive picker to select and copy any code block
```

---

## QUICK REFERENCE CARD

```
Session Control
  /clear          → fresh start (keeps file edits)
  /compact [keep X] → compress history, keep thread
  /fork [name]    → clone conversation safely
  /rewind         → roll back
  /btw [question] → side question, zero context cost
  /effort [level] → set reasoning depth

Navigation
  Shift+Tab       → cycle permission modes
  Ctrl+T          → toggle task list
  Ctrl+F          → kill all background agents
  Ctrl+R          → history search
  /vim            → toggle vim keybindings

Context
  @file.md        → add file to context instantly
  /status         → show status overlay
  /memory         → manage auto-memory
  /model [name]   → switch model mid-session

Agent Teams (requires CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1)
  "create an agent team..." → spawn teammates
  Shift+Down      → cycle between teammate panes
  Ctrl+F          → kill all agents

Your Setup Status
  ✅ bypassPermissions (settings.json)
  ✅ autoMemory + autoDream
  ✅ Telegram channels (Ugolino bot)
  ✅ Agent Teams enabled
  ✅ CLAUDE_AUTOCOMPACT_PCT_OVERRIDE: 75
  ✅ BASH_MAX_OUTPUT_LENGTH: 150000
  ✅ Status line (custom script)
  ✅ tmux session persistence
  ✅ PIV Loop commands (prime, plan, execute, validate)
  ✅ Rules directory (path-scoped)
  ✅ sync-memories command
  ✅ server-status command
  🔧 /hook sound notification
  🔧 Shell aliases (c, cc, ugo)
  🔧 skill-creator skill
  🔧 /vim mode (try it — you'll love it)
  🔧 Obsidian vault (optional)
```
