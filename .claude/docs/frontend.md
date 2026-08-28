# Frontend Guide (`frontend/`)

React 18 + TypeScript SPA, Vite build, Material UI. Replaces the old Django templates
(jQuery/Bootstrap/billboard.js — deleted in Phase 4 of the modernization).

## Stack

- **UI**: `@mui/material` (+ icons), theme in `src/theme.ts` with the severity palette
  (success/warning/danger mapped from API `success_level`/`errors_level` fields).
- **Charts**: `@mui/x-charts` — LineChart (response times over time, dual y-axis),
  BarChart (top-mean, compare), PieChart (success/error donut).
- **Tables**: `@mui/x-data-grid` (sorting/filtering; replaces tablesorter). Aggregate-table
  columns are derived at runtime from the JSON keys of the first row.
- **Data**: `@tanstack/react-query` + `axios` (`src/api/client.ts`; `withCredentials`,
  `X-CSRFToken` from the `csrftoken` cookie). Polling via `refetchInterval`
  (dashboard 10 000 ms, online 5 000 ms) — never hand-rolled `setInterval`.
- **Routing**: `react-router-dom` — `/`, `/analyzer` (`?project=&test=`), `/online`.
- **API types**: generated from the OpenAPI schema — `npm run generate-api`
  (requires the Django dev server on :8888) → `src/api/schema.d.ts`. Regenerate whenever
  serializers change; keep hand-written types out of `src/api/`.

## Dev workflow

```bash
make run             # Django on :8888
make frontend-dev    # Vite on :5173, proxies /api /loginapi /logout /admin /static to :8888
```
Auth is the Django session cookie; the Vite proxy keeps everything same-origin in dev.
401/403 from the API redirect the SPA to the SSO login (see `src/api/client.ts`).

## Build & serving

`make frontend-build` → `frontend/dist`. Django serves it: `ltc/settings.py` adds
`frontend/dist` to `STATICFILES_DIRS` when present, and `ltc/urls.py`'s catch-all serves
`index.html` for SPA routes. Deployments must run the frontend build before `collectstatic`.

## Page inventory (ported from the old templates)

| Route | Contents |
|---|---|
| `/` Dashboard | Last-tests table, last-test-per-project table, active tests (progress bar from `started_at`+`duration`), load generators (JMeter-instance badge: ≥5 danger, 3–4 warning). |
| `/analyzer` | Cascading project/test selects; tabs: Overview (donut + top-errors + top-mean bar with 200 ms band), Compare (bar vs last 15 tests + highlights cards + side-by-side table), Aggregate table (DataGrid, error column colored by `errors_level`), Response times (line, zoom), Monitoring (placeholder — upstream feature was dead). Action details opens an MUI Dialog (was a popup window). |
| `/online` | Running-test select; live line chart (avg / errors/s / rps) + aggregate DataGrid, 5 s polling. |

Admin stays on Django (`/admin/` link in the app bar).

⚠️ `ltc/templatetags/tags.py` (global builtins) is used by the **Confluence** templates
(`get_percentage_rel`/`get_percentage_abs`) — it must survive the template cleanup even after
the web templates are deleted.

## Conventions

- Colors for severity come from the theme, driven by API `*_level` fields — do not re-derive
  thresholds client-side.
- Every data fetch goes through `src/api/` hooks (react-query) — no fetch/axios calls in components.
- Devcontainer: npm registry access is granted in `.devcontainer/project/scripts/project-install.sh`
  (pre-firewall); ports 5173/8888 are forwarded via `.devcontainer/project/devcontainer-overrides.json`.
