# Decision Log

ADR-style, newest last. Check here before re-litigating an architectural choice.

## 2026-08: Modernization (Django 5.2 + DRF + React/MUI SPA)

1. **Full SPA, not per-page islands.** `frontend/` (Vite + React + TS) replaces all Django
   templates except Confluence rendering and the admin. Rationale: tiny template surface
   (~18 templates, ~800 lines JS), clean API seam already half-existed.
2. **TypeScript + generated API types.** Types come from the drf-spectacular OpenAPI schema
   (`npm run generate-api`); serializers are the single source of truth.
3. **MUI X Charts** (not Recharts/billboard.js): one design system for UI and charts.
4. **Settings: explicit + env vars.** Everything lives in tracked `ltc/settings.py`; secrets via
   `LTC_*` env vars; untracked `local_settings.py` is an optional dev override only. Before this,
   the committed repo could not boot (INSTALLED_APPS additions lived only in prod local_settings).
5. **Severity thresholds live server-side** (success 98/95 %, error bands 3/10 %, slow-action
   200 ms) as `*_level` serializer fields — clients only map levels to colors.
6. **No task queue (yet).** The heavy online CSV parse is throttled via a 5 s cache guard
   (`ltc/online/services.py`) instead of introducing Celery. Revisit if polling load grows or
   report generation moves out of Jenkins-driven commands.
7. **Polling, not WebSockets.** react-query `refetchInterval` (10 s dashboard / 5 s online).
   Channels/SSE deemed not worth the infrastructure for these refresh rates.
8. **Django admin stays.** It is the operator UI for ReportTemplate/GraphiteVariable/SSHKey/
   LoadGenerator editing. Do not rebuild it in React.
9. **Confluence rendering stays server-side.** `confluence/*.html` templates emit Confluence
   storage-format XHTML — not a web UI concern.
10. **AutoField PKs kept** (`DEFAULT_AUTO_FIELD = AutoField`) to avoid BigAutoField migrations on
    large production tables.
11. **Historical migrations edited in place** (jsonb.JSONField → models.JSONField;
    index_together → named AddIndex matching the physical index names) rather than squashed,
    to keep existing production DBs consistent without data migrations.
12. **psycopg2 kept** for now; psycopg3 swap is orthogonal and deferred.
13. **Out of scope, deliberately**: Controller UI (no backend views exist), CSV-upload feature
    (was unreachable/broken — re-specify before rebuilding), CI pipeline.

## 2026-08: Vendorized Debian packaging

14. **Python deps vendored in the deb** (`/www/ltc/vendor`, `pip install --target`), not taken
    from Puppet-installed system packages — the system model cannot deliver Django 5.2. The
    vendor dir is prepended to `sys.path` by `manage.py` and `ltc/wsgi.py`, so it shadows any
    remaining system Django until Puppet drops those packages.
15. **`Architecture: amd64`, `Depends: python3.11`** — honest about the cp311/amd64 binary
    wheels (psycopg2, numpy, pandas, scipy, cryptography). Build interpreter must match the
    bookworm target.
16. **Assets built at package time**: SPA build + `collectstatic` happen in CI; `postinst`
    only migrates and restarts uWSGI. The target never needs Node or writes to `/www/ltc`.
17. **Build logic lives in the repo** (`packaging/*.sh`); Jenkins steps are one-liners —
    portable to GitLab CI later.

## 2026-09: Redesign + the empty-data fix

18. **The "all graphs and tables are empty" bug was one line**: `TestViewSet` ordered by
    plain `-started_at`, and **PostgreSQL sorts NULLs FIRST on DESC**, so page 1 of
    `/api/v1/tests/` was never-started tests with no metrics — the dashboard table and the
    analyzer's test dropdown were full of dataless ghost rows. Fixed with
    `F('started_at').desc(nulls_last=True)` (the pattern the models already used) plus a
    `?started=true` filter. It passed CI because **SQLite orders NULLs the opposite way**;
    the regression test now asserts explicit ordering rather than DB-specific null placement.
19. **The Claude Design prototype is the UI source of truth** (project "Load testing center
    redesign"). Its `ltc-data.js` mock is written against the `/api/v1/` payloads, so it also
    defines the API contract — which is why the redesign and the data fixes shipped together.
20. **MUI kept and reskinned**, not replaced: the theme carries the design tokens twice
    (MUI palette + `--s-*` CSS variables) so ported prototype markup keeps exact values.
21. **Charts are inline SVG, not MUI X Charts**: the prototype's own drawing (sparklines,
    donut, dual-axis timeseries with threshold band, boxplots) *is* the design, and hand
    paths reproduce it exactly with no chart-library layout fighting.
22. **Brand fonts referenced, never committed** — proprietary faces load from
    `/static/fonts/` when present, with Arial Black / Segoe UI fallbacks otherwise.
23. **`rps` and per-bucket `errors` are derived server-side** (from the resolution's
    `per_sec_divider` and the per-action data) so every client agrees on units.
24. **`post_to_confluence()` params made optional**: the management command had always
    called it with zero args against a signature requiring two — a latent `TypeError`. The
    parent page is now looked up when not supplied.
