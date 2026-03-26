---
paths:
  - "**/docker-compose*.yml"
  - "**/docker-compose*.yaml"
  - "**/Dockerfile*"
---

# Docker / Docker Compose Rules

## Compose Structure
- Always pin image versions — never `image: postgres:latest`
- Every service that exposes a port must have a `healthcheck`
- Use named volumes for all persistent data
- Group related services with comments: `# --- Database ---`
- `restart: unless-stopped` on production services

## Networking
- Define explicit networks — don't rely on the default bridge
- Backend services should not expose ports to host unless necessary
- Use service names for inter-container DNS (e.g., `postgres:5432`)

## Environment Variables
- Use `.env` file for compose variable substitution
- Never hardcode secrets in compose files — always `${SECRET_VAR}`
- Provide `.env.example` with all required keys, no values

## Dockerfile Best Practices
- Multi-stage builds for production images
- Non-root user in final stage
- `.dockerignore` always present
- Pin base image digests for production: `python:3.12-slim@sha256:...`

## CogStack Specifics
- Caddy is always the entry point — never expose app ports directly to internet
- Standard internal ports: FastAPI :8000, Next.js :3000, n8n :5678
- All stacks use the `cogstack-net` external network for Caddy to reach services
