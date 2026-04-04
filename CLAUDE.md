# CogStack — Claude Code Context

## Who I Am
Charles Vosloo, founder/CEO of CogStack, AI infrastructure consultancy, Johannesburg SA.
This session is running from ~/.hermes/ on desktop-wsl (DELL-WIN10), WSL2 Ubuntu.

## Stack
- Python: uv exclusively (never bare pip)
- TypeScript, Postgres, Docker Compose
- Editor: Zed in vim mode
- Shell: zsh + tmux (session 'ugo', start via ~/start-ugo.sh)
- Commits: conventional commits

## Active Projects
- **CTIS**: tender.cogstack.co.za — Next.js + FastAPI, Hostinger KVM 8
- **cogstack-leadgen**: n8n (n8n.bigtorig.com) + Notion CRM + Python scraper (~/cogstack-leadgen)
- **Hermes**: ~/.hermes/ — v0.7.0, Telegram @CogHermes_bot, Honcho at localhost:8000

## Infrastructure
- Tailscale mesh: desktop-wsl, desktop, laptop-wsl, bigtorig, cogstack, pi4
- Obsidian vault: bare repo on pi4, working copy ~/vault
- Ollama: 100.109.221.78:11434 — default model qwen3:14b
- D: drive (/mnt/d/) is cold archive only — never git clone/operate there

## Workflow
- PIV Loop: /plan-feature → /execute → /validate
- Docs live in ~/.hermes/docs/ (e.g. HermesV0.7setup.md)
- Rules in ~/.claude/rules/, reference in ~/claude-code-template/.claude/reference/

## Do Not
- Never pip install outside a project venv
- Never commit .env files
- Never modify ~/.hermes/memories/ directly — use the memory tool
