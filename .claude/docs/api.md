# API Contract (`/api/v1/`)

Machine-readable schema: `GET /api/v1/schema/` (OpenAPI 3, drf-spectacular), Swagger UI at
`/api/v1/schema/swagger/`. Regenerate frontend types after changing serializers:
`cd frontend && npm run generate-api`.

## Conventions

- Auth: Django **session** cookie (`SessionAuthentication`); default permission `IsAuthenticated`.
  The SPA sends `X-CSRFToken` from the `csrftoken` cookie for unsafe methods.
- Versioning: URL path (`/api/v1/`); pagination: PageNumber (`?page=`), page size 50
  (`projects` and `loadgenerators` lists are unpaginated — small tables).
- Severity fields (`success_level`: success/warning/danger, `errors_level`: ok/warn/crit) are
  computed server-side; thresholds live in `ltc/base/services.py` and `ltc/analyzer/services.py`.

## Endpoints

| Method & path | Purpose |
|---|---|
| `GET /projects/` | Project list (id, name, enabled). |
| `GET /tests/?project=&status=&page=` | Tests, newest first. `status` repeatable (C/R/A/S/F/FA). Each row has `stats` (mean, success %, level, delta vs previous test) batched server-side. |
| `POST /tests/` | Create a test (Jenkins integration). Accepts `project_name` to get-or-create the project. |
| `GET /tests/<id>/` | Test detail (same serializer, per-object stats). |
| `GET /tests/<id>/report/` | Full analyzer payload: `test_action_aggregate_data` (with `errors_level` per row), `test_data` (rtot timeseries), `server_monitoring_data`, `compare_data` (last 15 tests), `slow_action_threshold_ms`. |
| `GET /tests/<id>/compare/<other_id>/` | Comparison vs another test (`0` = previous test): `tests`, `highlights` {critical, warning, success}, `compare_table` rows. |
| `GET /tests/<id>/actions/<action_id>/` | Per-action stats incl. boxplot values (q1/q2/q3/IQR/LW/UW) for the last 5 tests + error list. |
| `GET /tests/<id>/online/` | Test + `online_data` (response_codes / aggregate_table / data_over_time). Triggers a server-side refresh throttled to once per 5 s — safe to poll. |
| `GET /loadgenerators/` | Load generators with nested `jmeter_servers`. |
| `GET /users/me/` | Current user (SPA auth check). |
| `GET /health_check` | Liveness (also HEAD). |

## Legacy aliases (delete with the jQuery pages)

`GET /test/` (unpaginated list, `status[]` param), `GET /test/<pk>` (= online action),
`GET /loadgenerator/` — used by the old `dashboard.js`/`online.js` only.

## Polling guidance for clients

Dashboard: 10 s (`/tests/?status=R&status=A`, `/loadgenerators/`). Online: 5 s
(`/tests/<id>/online/` — matches the server-side refresh cooldown).
