# LTC — Load Testing Center

Django web app that orchestrates, monitors and reports on Apache JMeter load tests.
Used at InnoGames; started by Jenkins jobs, publishes reports to Confluence.

Detailed AI-facing docs live in `.claude/docs/`:

- [architecture.md](.claude/docs/architecture.md) — apps, data model, test lifecycle, external integrations
- [backend.md](.claude/docs/backend.md) — settings, URL map, management commands, hotspots, conventions
- [api.md](.claude/docs/api.md) — DRF API contract consumed by the frontend
- [frontend.md](.claude/docs/frontend.md) — React/TypeScript/MUI SPA in `./frontend`
- [decisions.md](.claude/docs/decisions.md) — ADR log; check before re-litigating an architectural choice

## Quick facts

- Python package: `ltc/` (apps: `base`, `analyzer`, `online`, `controller`, `admin`, `api`)
- Django 5.2 + Django REST Framework, PostgreSQL (heavy JSONB usage), Python 3.11+
- Frontend: React + TypeScript + Material UI SPA in `frontend/` (Vite)
- Auth: Django sessions via InnoGames SSO (`igrestlogin`); Django admin is a real operator UI — keep it
- Confluence report rendering is server-side (`ltc/analyzer/templates/confluence/`) — never move it to the SPA

## Run / test / build

```bash
# Backend (venv at .venv, Postgres required — see ltc/local_settings.example.py for env vars)
.venv/bin/python manage.py migrate
.venv/bin/python manage.py runserver 8888

# Tests
.venv/bin/python -m pytest

# Frontend
cd frontend && npm install && npm run dev     # Vite dev server on :5173, proxies /api to :8888
cd frontend && npm run build                  # production bundle in frontend/dist
```

Makefile has `test`, `run`, `frontend-*` targets; `make dev-help` lists devcontainer targets.

## Conventions

- Settings are explicit in `ltc/settings.py`, secrets/env-specific values from environment variables;
  `ltc/local_settings.py` (untracked) is an optional local override only.
- API changes: update serializers/views in `ltc/api/`, then regenerate frontend types
  (`cd frontend && npm run generate-api`) so the TS client stays in sync with the OpenAPI schema.
- Presentation thresholds (success 98/95 %, error bands 3/10 %, 200 ms slow-action) are decided
  server-side in serializers as `*_level` fields — the SPA only maps levels to colors.
- Long-running work (JMeter runs, CSV parsing) belongs in management commands
  (`ltc/controller/management/commands/`), not in request handlers.
