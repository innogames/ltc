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
| `GET /tests/?project=&status=&started=&project_enabled=&page=&page_size=` | Tests, **newest started first with never-started rows last** (`nulls_last` — plain `-started_at` puts NULLs first on PostgreSQL and filled the dashboard with dataless rows). `status` repeatable (C/R/A/S/F/FA); `started=true` hides never-started tests; `project_enabled=true` limits to enabled projects; `page_size` up to 200. Each row's `stats` (mean, success %, level, delta vs previous, `spark[]`) is batched server-side. |
| `POST /tests/` | Create a test (Jenkins integration). Accepts `project_name` to get-or-create the project. |
| `GET /tests/<id>/` | Test detail (same serializer, per-object stats). |
| `GET /tests/<id>/report/` | Full analyzer payload: `test_action_aggregate_data` (dynamic JSONB stat keys + `errors_level`), `test_data` (timeseries points `{timestamp, mean, median, count, rps, errors}` — `rps` and per-bucket `errors` are derived server-side), `server_monitoring_data`, `compare_data` (last 15 runs), `slow_action_threshold_ms`. |
| `GET /tests/<id>/monitoring/` | Per-server series `[{host, cpu[], mem[], la}]` for the Monitoring tab. CPU busy = `CPU_user+CPU_system+CPU_iowait`; memory used % = `Memory_used / (used+free+buff+cached)`. Returns `[]` (200) when nothing was collected — the normal case. See `ltc/analyzer/monitoring.py`. |
| `POST /tests/<id>/stop/` | Terminates a running test. 409 unless status is running/analyzing/scheduled. |
| `POST /tests/<id>/publish/` | Publishes the report to Confluence. 503 when `WIKI_URL` is unset, 409 without a project report template, 502 on a Confluence failure; otherwise `{"url": ...}`. |
| `GET /tests/<id>/compare/<other_id>/` | Comparison vs another test (`0` = previous test): `tests`, `highlights` {critical, warning, success}, `compare_table` rows. |
| `GET /tests/<id>/actions/<action_id>/` | Per-action stats incl. boxplot values (q1/q2/q3/IQR/LW/UW) for the last 5 tests + error list. |
| `GET /tests/<id>/online/` | Test + `online_data` (response_codes / aggregate_table / data_over_time). Triggers a server-side refresh throttled to once per 5 s — safe to poll. |
| `GET /loadgenerators/` | Load generators. `num_cpu, memory, memory_free, la_1/5/15` are emitted as **numbers** (the columns are CharFields; junk → `null`), plus `jmeter` (count of running jmeter-servers) and nested `jmeter_servers`. |
| `GET /users/me/` | Current user (SPA auth check). |
| `GET /health_check` | Liveness (also HEAD). |

## Legacy aliases (delete with the jQuery pages)

`GET /test/` (unpaginated list, `status[]` param), `GET /test/<pk>` (= online action),
`GET /loadgenerator/` — used by the old `dashboard.js`/`online.js` only.

## Polling guidance for clients

Dashboard: 10 s (`/tests/?status=R&status=A`, `/loadgenerators/`). Online: 5 s
(`/tests/<id>/online/` — matches the server-side refresh cooldown).
