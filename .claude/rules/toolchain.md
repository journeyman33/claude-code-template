# Toolchain Preferences

## Python
- Always use `uv` — never `pip`, never `python -m venv` manually
- `uv run` to execute scripts, `uv add` to add deps, `uv sync` to install
- `uv python install 3.12` for new projects unless otherwise specified
- pyproject.toml is the source of truth — never requirements.txt

## Node / Bun
- Prefer `bun` over `npm` where possible
- `bun install`, `bun run`, `bun add`
- Fall back to `npm` only if a package has bun incompatibilities

## Containers
- Always docker-compose, never raw `docker run` for services
- Compose files: `docker-compose.yml` (prod), `docker-compose.dev.yml` (dev overrides)
- Health checks on every service that exposes a port
- Named volumes, not bind mounts, for persistent data in production

## Reverse Proxy
- Caddy over Nginx — always
- Use Caddyfile format, not JSON config
- Automatic HTTPS via Caddy where a domain is available

## Shell
- zsh with starship, atuin, zoxide
- Prefer `&&` chaining over multi-line scripts unless logic is complex
- Always quote variables: "$VAR" not $VAR
- Use `gh` CLI for all GitHub operations
