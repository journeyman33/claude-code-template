---
paths:
  - "**/*.py"
  - "**/pyproject.toml"
  - "**/uv.lock"
---

# Python / FastAPI Rules

## Project Setup
- `uv init` for new projects, `uv sync` to install
- Python 3.12+ unless project specifies otherwise
- Always define `[tool.ruff]` in pyproject.toml for linting

## FastAPI Patterns
- Routers in `src/routers/`, one file per domain (users, auth, tenders, etc.)
- Pydantic v2 for all request/response models — no raw dicts in endpoints
- Dependency injection for DB sessions, auth, config
- Use `lifespan` context manager for startup/shutdown, not deprecated `@app.on_event`

## Error Handling
- Custom exception classes in `src/exceptions.py`
- `@app.exception_handler` for global error responses
- Never return raw 500s — always a structured `{"error": ..., "detail": ...}`

## Database
- SQLAlchemy 2.0 async style with `async_sessionmaker`
- Alembic for migrations — never modify tables manually
- One transaction per request via dependency injection

## Testing
- pytest + httpx `AsyncClient` for endpoint tests
- Fixtures in `conftest.py`
- `uv run pytest` to run tests

## Validation Commands
```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src/
uv run pytest
```
