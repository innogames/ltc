# LTC Architecture

## What it does

LTC drives the full JMeter load-test lifecycle:

1. **Controller** — provisions distributed JMeter (master + remote `jmeter-server` slaves) over SSH
   on "load generator" VMs discovered from InnoGames Serveradmin; starts/stops/terminates tests.
2. **Online** — live monitoring of a running test by incrementally tailing the JMeter results CSV.
3. **Analyzer** — parses result CSVs into aggregate/timeseries data, compares a test against previous
   runs (Student's t-test "highlights"), publishes reports to Confluence.

Entry point for a test run is Jenkins calling `manage.py start_test` (see README.md), which blocks for
the whole test duration and then analyzes, cleans up, and posts the report.

## Apps

| App | Purpose |
|---|---|
| `ltc.base` | Core domain: `Project`, `Test`, `TestFile`, `Configuration`. Owns most business logic in fat model methods. `services.py` has the batched dashboard stats. |
| `ltc.analyzer` | Report data models + `ReportTemplate`/`GraphiteVariable` Confluence templating engine. `services.py` builds report/compare payloads. |
| `ltc.online` | `TestOnlineData` — incremental CSV tailing for live graphs. `services.py` throttles refresh. |
| `ltc.controller` | `LoadGenerator`/`JmeterServer` SSH orchestration (paramiko); all management commands. |
| `ltc.admin` | No models. Monkey-patches the global admin site at `ready()`: login redirects to `settings.LOGIN_URL`, non-staff get 403. |
| `ltc.api` | DRF serializers/views — the API consumed by the React SPA and by Jenkins. |

## Data model (core relations)

```
Project 1─* Test 1─* TestFile                (raw files: result CSV, log, testplan, jenkins build.xml)
                 1─* TestData                (timeseries per resolution, JSONB `data`)
                 1─* TestActionData          (per-action timeseries, JSONB)
                 1─* TestActionAggregateData (per-action aggregate stats, JSONB)
                 1─* ServerMonitoringData    (per-server monitoring, JSONB)
                 1─* TestError ─ Error       (error text/code + count, per Action)
                 1─* TestOnlineData          (live: response_codes / aggregate_table / data_over_time)
                 1─* JmeterServer ─ LoadGenerator   (running jmeter-server processes on generator VMs)
Action  *─1 Project                          (named request/transaction)
ReportTemplate 1─* GraphiteVariable          (Confluence report templating; admin-edited)
ReportCache, Configuration, SSHKey, ActivityLog, JmeterInstanceStatistic  (support tables)
```

**The JSONB pattern**: metric tables have a single `data = models.JSONField()` column holding dicts
like `{"mean": .., "median": .., "count": .., "errors": ..}`. Aggregations cast keys to numeric via
`KeyTextTransform` + `Cast` (see `ltc/base/services.py`; older code uses
`RawSQL("((data->>%s)::numeric)")`). Column sets are dynamic — the aggregate table UI derives its
columns from the JSON keys of the first row.

## Test lifecycle (Test.status)

```
C created → S scheduled → R running → A analyzing/analyzed → F finished
                                   ↘ FA failed
```

`start_test` command: create Test → `prepare_test_plan()` → `find_loadgenerators()` + provision
`JmeterServer`s over SSH → `test.start()` (spawns local JMeter master, blocks) →
`wait_for_finished()` (updates `last_active`, aborts on sustained >90% error rate) → `analyze()`
(parse CSVs via `TestFile.parse_csv()`) → `cleanup()` → Confluence report.

`Test.is_locked` is a DB-column mutex used by the online-data updater. `check_tests` command is the
watchdog that terminates tests inactive for >1h.

## External integrations

- **Jenkins** — invokes `start_test` / `post_to_confluence` as job steps; parses `build.xml` via `TestFile.parse_build_xml()`.
- **Serveradmin/adminapi** (`git+…serveradmin.git`) — `loadgenerators_monitor` command syncs LoadGenerator inventory.
- **Graphite** — `GraphiteVariable` fetches metric values/graphs for Confluence reports (`settings.GRAPHITE_*`).
  ⚠️ `GraphiteVariable.__init__` builds a GraphiteClient on every instantiation — ORM reads of this model need Graphite settings.
- **Confluence** — `ReportTemplate.render()` emits Confluence storage-format XHTML using
  `ltc/analyzer/templates/confluence/*.html`. Server-side only; not part of the web UI.
- **igrestlogin** (`git+ssh…igrestlogin.git`) — InnoGames SSO: token login endpoints under `/loginapi/`,
  `RestLoginBackend` auth backend. Optional at import time (guarded in settings/urls); sessions + cookies.

## Frontend/backend split

React SPA (`frontend/`, see frontend.md) talks only to `/api/v1/` (see api.md). Django serves the
built SPA (`frontend/dist`) plus `/admin` and `/loginapi/`. Live updates are HTTP polling
(dashboard 10 s, online 5 s) — no websockets/Channels by decision (see decisions.md).
