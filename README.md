# Description

Old version: https://github.com/innogames/ltc/tree/old

Load Testing Center (codename `ltc`) - dashboard/report analyzer for load testing with JMeter (http://jmeter.apache.org/).

Developed and used in Innogames GmbH (www.innogames.com) to provide load tests results.

Online web application/dashboard for "continuous integration" (CI) Load testing with JMeter.
A central system for launching (incl. distribution testing), monitoring tests, creating reports, and for a comparative analysis between different load tests provided with Jmeter.
Can be used with Jenkins.
Consist of several modules:

1. Analyzer - build reports, analyze results and compare results with another.
2. Online - online monitoring for running tests
3. Controller - configure and run the tests (COMING SOON)

### Docker
To try to use this tool, you can try this docker-compose to deploy it quickly.
https://github.com/arcmedia/JmeterControlCenter

## [DASHBOARD]
Get tests overview:
![alt tag](/pics/dashboard.png)

## [ANALYZER]
Create a dynamic report for the tests and compare them with previous results:
![alt tag](/pics/analyzer.png)

Get fancy good-readable aggregate table for the test:
![alt tag](/pics/aggregate.png)

## [ONLINE] Online test monitoring
Provides online test monitoring, reads .csv results from files, and builds graphs online.

## [CONTROLLER]
COMING SOON


## Stack

* Backend: Django 5.2 + Django REST Framework (PostgreSQL, JSONB metrics storage).
  OpenAPI schema at `/api/v1/schema/` (Swagger UI at `/api/v1/schema/swagger/`).
* Frontend: React + TypeScript + Material UI single-page app in `frontend/`
  (Vite; charts via MUI X Charts, tables via MUI X DataGrid).

### Development

```bash
# Backend (needs PostgreSQL; see ltc/local_settings.example.py for LTC_* env vars)
make migrate
make run                # Django on :8888

# Frontend
make frontend-install
make frontend-dev       # Vite dev server on :5173, proxies API to :8888

# Tests
make test
```

Production build: `make frontend-build` (outputs `frontend/dist`, served by Django),
then `manage.py collectstatic`.

### Packaging

Deployment is a self-contained Debian package (all Python deps vendored in
`/www/ltc/vendor`, SPA and static files prebuilt): see [packaging/README.md](packaging/README.md).
Build locally with `bash packaging/build-deb.sh`.

AI-facing project documentation lives in `CLAUDE.md` and `.claude/docs/`.

### Running tests with Jenkins
Add in Jenkins job those commands, to prepare test plan and run the test:

Jmeter job parameters list example:
```
THREADS = 100
DURATION = 3600
RAMPUP = 1800
TEST_PLAN = testplan.jmx
VARS:
[{"name":"THREAD_COUNT", "value": "$THREADS", "distributed": true},{"name": "SERVER_NAME", "value": "innogames.com"},{"name": "DURATION", "value": "$DURATION"},{"name": "RAMPUP", "value": "$RAMPUP"},{"name":"THREAD_COUNT_TOTAL", "value": "$THREADS", "distributed": true}]
```
Job pre-build action example:
```
python3 /www/ltc/manage.py start_test --jmeter_path=$JMETER_HOME --temp_path="/www/ltc/temp" --testplan $TEST_PLAN --project $JOB_NAME --threads $THREADS --thread_size $THREAD_MEM_SIZE_MB --vars "$VARS" --duration "$DURATION"
```
