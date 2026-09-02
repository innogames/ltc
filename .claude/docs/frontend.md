# Frontend Guide (`frontend/`)

React 18 + TypeScript SPA, Vite build, Material UI. Replaces the old Django templates
(jQuery/Bootstrap/billboard.js — deleted in Phase 4 of the modernization).

## Design system

The UI implements the InnoGames design system from the Claude Design prototype
("Load testing center redesign" → `LTC Prototype.dc.html`): deep-forest header
(`#1F3F14`) with a `#7FB342` underline, light **and** dark themes, SF Theramin Gothic
display type over Calibri body.

`src/theme.ts` is the single source: it defines the token maps and exposes them **twice** —
as an MUI palette/typography/component theme (so MUI components are reskinned) and as the
prototype's `--s-*` CSS custom properties (so ported markup and inline SVG use identical
values). Helpers `successChip()`, `successColor()`, `errorsColor()` map the API's severity
levels to colors; never re-derive thresholds client-side. Theme mode lives in `App.tsx`
and persists to `localStorage` (`ltc-theme`).

**Brand fonts are not committed** — they're proprietary. `src/styles/fonts.css` points
`@font-face` at `/static/fonts/*.ttf`; drop the TTFs into the deployment's
`<STATIC_ROOT>/fonts/` (`SF_Theramin_Gothic{,_Bold,_Condensed}.ttf`,
`calibri{,b,l}.ttf`) and they render. Without them the fallbacks (Arial Black / Segoe UI)
are used, so public checkouts look sane.

## Stack

- **UI**: `@mui/material` (+ icons), reskinned by `src/theme.ts`.
- **Charts**: inline SVG in `src/components/charts.tsx` — the prototype's own hand-tuned
  rendering *is* the design: `Sparkline`, `SuccessDonut`, `TimeseriesChart` (dual axis +
  dashed threshold + error band), `MiniArea` (CPU/memory), plus `linePath`/`areaPath`
  builders. Boxplots live in `ActionDetailsDrawer`.
- **Tables**: MUI `Table` with the theme's compact tabular-numeric treatment. Aggregate-table
  columns are derived at runtime from the JSON keys of the first row — never hardcoded.
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
| `/` Dashboard | 4 KPI tiles (running/analyzing, pass rate, needs attention, generator slots); last-tests table with project chips + all/active/attention filters, per-row sparkline, mean with Δ-vs-previous pill, animated status dot, result pill, row → Analyzer; right rail with active-test progress cards and load-generator cards (memory + load bars, JMeter badge ≥5 danger / ≥3 warning, dimmed when offline). 10 s polling. |
| `/analyzer` | Context bar (project/test selects, started/VUs/duration/result, ‹ Previous run, Publish to Confluence); tabs: **Overview** (5 KPI tiles with deltas, success donut, top-failed-actions with rate bars, slowest-actions bars with the 200 ms marker), **Compare** (mean/median history bars over the last runs, compare-against select, critical/warning/improved counts, highlight cards, side-by-side table with Δ), **Aggregate** (filter, only-with-errors / slower-than toggles, sortable dynamic columns, error-tinted rows, Export CSV), **Response times** (series toggles, dual-axis chart, peak/above-threshold/errors summary), **Monitoring** (per-host CPU + memory areas, empty state when uncollected). Clicking any action opens the details drawer. |
| `/online` | Running-test select, elapsed progress + live pulse, Stop test (confirm dialog), 5 live KPI tiles, live response-time chart with error band, live aggregate table. 5 s polling. |

Admin stays on Django (`/admin/` link in the app bar).

⚠️ `ltc/templatetags/tags.py` (global builtins) is used by the **Confluence** templates
(`get_percentage_rel`/`get_percentage_abs`) — it must survive the template cleanup even after
the web templates are deleted.

## Conventions

- Colors for severity come from the theme, driven by API `*_level` fields — do not re-derive
  thresholds client-side.
- Every data fetch goes through `src/api/` hooks (react-query) — no fetch/axios calls in components.
- Mutations: `useStopTest()` and `usePublishReport()`; both surface the API's `detail`
  message in a snackbar rather than failing silently.
- The header's global search jumps to `/analyzer?test=<id>` by test id, name or project.
- Devcontainer: npm registry access is granted in `.devcontainer/project/scripts/project-install.sh`
  (pre-firewall); ports 5173/8888 are forwarded via `.devcontainer/project/devcontainer-overrides.json`.
