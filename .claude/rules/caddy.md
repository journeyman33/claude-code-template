---
paths:
  - "**/Caddyfile*"
  - "**/caddy/**"
---

# Caddy Rules

## General
- Always use Caddyfile format — not JSON API
- Automatic HTTPS is the default — never disable unless localhost/testing
- Use `reverse_proxy` to upstream services by container name + port

## Standard Patterns

### Reverse proxy to a service
```caddyfile
app.example.com {
    reverse_proxy app:8000
}
```

### With health checks
```caddyfile
api.example.com {
    reverse_proxy api:8000 {
        health_uri /health
        health_interval 10s
    }
}
```

### Basic auth (admin panels)
```caddyfile
admin.example.com {
    basicauth {
        charles <hashed-password>
    }
    reverse_proxy grafana:3000
}
```

## CogStack Conventions
- Domains follow pattern: `service.bigtorig.com` or `service.cogstack.co.za`
- Internal services (n8n, Supabase Studio, Grafana) always behind basicauth
- Public APIs (FastAPI, Next.js) — no basicauth, handle auth in app
- Reload with: `docker exec caddy caddy reload --config /etc/caddy/Caddyfile`
