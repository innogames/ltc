# Backend Guide

## Settings & environment

`ltc/settings.py` is explicit and self-contained; environment variables override defaults
(see `ltc/local_settings.example.py` for the full list — all prefixed `LTC_`). An untracked
`ltc/local_settings.py` may override anything for local dev, and is imported last.

- `igrestlogin` (InnoGames SSO) is optional at import time: settings and `ltc/urls.py` register it
  only when the package is installed, so open-source checkouts boot without it.
- `DEFAULT_AUTO_FIELD` is `AutoField` on purpose — the schema predates BigAutoField; don't change it.
- DB engine is `django.db.backends.postgresql`; PostgreSQL is required (JSONB everywhere).

## URL map

```
/                    Dashboard        ltc/base/views.py::index (template; replaced by SPA in Phase 4)
/analyzer/           Analyzer         ltc/analyzer/views/analyzer_views.py (template)
/analyzer/test_data/            POST  legacy JSON report payload (kept until SPA cutover)
/analyzer/compare_highlights/   POST  legacy HTML fragment (kept until SPA cutover)
/analyzer/action_details/<t>/<a>      legacy popup page
/online/             Online           ltc/online/views.py (template)
/api/v1/...          DRF API          ltc/api/urls.py — see api.md
/admin/              Django admin     custom AdminSite in ltc/admin/sites.py — operator UI, keep
/loginapi/           SSO endpoints    igrestlogin package (only when installed)
/logout/             logout_then_login
```

## Services layer (business logic shared by template views and API)

- `ltc/base/services.py` — `dashboard_test_stats(tests)`: batched JSONB aggregation
  (KeyTextTransform+Cast, constant query count) + success-level thresholds (98/95 %).
- `ltc/analyzer/services.py` — `test_report_data`, `compare_highlights` (Student's t-test with
  Satterthwaite df, significance percent from the `signifficant_actions_compare_percent`
  Configuration row), `compare_table`, `action_details_data`, error-band constants (3/10 %),
  slow-action threshold (200 ms).
- `ltc/online/services.py` — `refresh_online_data(test)`: cache-guarded (5 s cooldown) wrapper
  around the heavy `TestOnlineData.update()` CSV parse. Never call `update()` directly from a view.

Presentation thresholds are decided server-side (`success_level`, `errors_level` fields); clients
only map levels to colors.

## Management commands (`ltc/controller/management/commands/`)

| Command | Trigger | Purpose |
|---|---|---|
| `start_test` | Jenkins job step | Full test run: provision slaves → run JMeter (blocks) → analyze → cleanup → Confluence. |
| `check_tests` | cron | Watchdog: terminate tests inactive >1h. |
| `loadgenerators_monitor` | cron | Sync LoadGenerator inventory from Serveradmin, SSH-refresh stats. |
| `gather_jmeter_instances_info` | cron | `jstat -gc` per running JmeterServer → JmeterInstanceStatistic. |
| `post_to_confluence` | Jenkins/manual | Publish test/project report to Confluence. |

There is no task queue (deliberate — see decisions.md); long-running work lives in these commands.

## Known hotspots / gotchas

- `TestOnlineData.update()` parses the whole tail of the JMeter CSV with pandas — only call via
  `ltc.online.services.refresh_online_data` (throttled).
- `GraphiteVariable.__init__` connects a GraphiteClient per instance — avoid bulk ORM reads of it.
- `Test.start()`/`wait_for_finished()` block for the whole test and install signal handlers —
  never call from a web request.
- Legacy `RawSQL("((data->>%s)::numeric)")` remains in `ltc/base/models.py` fat methods
  (top_errors/top_mean/get_test_metric/compare_tests); prefer the services layer for new code.
- Migration history was hand-edited during the Django 5.2 upgrade: historical migrations now use
  `models.JSONField` and named `AddIndex` ops matching the physical index names created by the old
  `index_together`. Never regenerate/squash these without checking a production DB's index names.

## Testing

`pytest` + `pytest-django` (`pytest.ini`), tests in `ltc/*/tests.py`. Default settings are
`ltc.test_settings` (SQLite — runs anywhere); use `pytest --ds=ltc.settings` against a real
PostgreSQL. `make test`.

## Deployment (Debian package, see packaging/README.md)

Jenkins builds a **self-contained** `ltc_<version>_amd64.deb` via `packaging/build-deb.sh`:
all Python deps vendored into `/www/ltc/vendor` (front of `sys.path` via `manage.py` /
`ltc/wsgi.py` bootstrap), SPA + `collectstatic` prebuilt into `/www/ltc/frontend/dist` and
`/www/ltc/_static`. Target (bookworm) runs uWSGI (`wsgi_module ltc.wsgi`) + nginx, managed
by Puppet (`admin::loadtest::web`), which also templates `/www/ltc/ltc/local_settings.py`
with secrets. `postinst` runs migrations and restarts the `ltc` service. Vendored wheels
are cp311/amd64 — the build interpreter must match the target (`python3.11`).
