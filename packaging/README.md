# Debian packaging (vendorized)

`build-deb.sh` produces a **self-contained** `ltc_<version>_amd64.deb`:
all Python dependencies from `requirements.txt` (including the git-hosted
`igrestlogin` and `serveradmin`/adminapi packages) are installed into
`/www/ltc/vendor`, which `manage.py` and `ltc/wsgi.py` put at the front of
`sys.path`. The target server only needs `python3.11` and `nginx` — the
Puppet-installed system Django/DRF/pandas packages are shadowed and can be
removed from the manifest once this package is live.

The React SPA is built and `collectstatic` runs at **build** time; the
package ships `/www/ltc/_static` and `/www/ltc/frontend/dist/index.html`.
On install, `postinst` only runs migrations and restarts the `ltc`
(uWSGI) service.

## Package layout

```
/www/ltc/
├── manage.py               vendor-aware entry point (Puppet crons use it)
├── ltc/                    Django project (no local_settings.py — Puppet
│                           templates it on the target)
├── vendor/                 all Python deps (cp311/amd64 wheels)
├── frontend/dist/index.html   SPA entry served by the Django catch-all
└── _static/                collectstatic output (SPA assets, admin, DRF)
```

## Jenkins job steps

1. **Prepare** — unchanged, except the artifact is now
   `${PACKAGE_NAME}_${VERSION}_amd64.deb` (was `_all`).
2. **Test** — replace the inline venv/pytest snippet with:
   ```bash
   PYTHON=${python} REQUIREMENTS_FILE=requirements-innogames.txt \
       bash packaging/test.sh
   ```
   (SQLite test settings: no PostgreSQL needed on the agent.)
3. **Build** — replace the inline build snippet with:
   ```bash
   PYTHON=${python} VERSION=${VERSION} BUILD_DIR=${BUILD_DIR} \
       REQUIREMENTS_FILE=requirements-innogames.txt \
       bash packaging/build-deb.sh
   ```
   Requirements on the agent: `python3.11` (must match the bookworm
   target — vendored wheels are cp311/amd64), Node >= 20 (`npm`),
   `dpkg-deb`, and `PIP_INDEX_URL` exported for the internal package
   index (credentials from the CI secret store), e.g.
   ```bash
   export PIP_INDEX_URL="https://<user>:${PIP_INDEX_URL_PASSWORD}@artifactory.../api/pypi/<repo>/simple"
   ```
   `requirements.txt` alone (the default) builds a package without the
   internal SSO backend — fine for public/local builds; internal
   deployments need `requirements-innogames.txt`.
4. **Upload** — unchanged deb-drop curl; update the filename glob:
   ```bash
   curl -f -F "token=${dd_token}" -F "repos=${REPO}" -F "max_versions=3" \
        -F "package=@${BUILD_DIR}/${PACKAGE_NAME}_${VERSION}_amd64.deb" \
        ${dd_url}
   ```

## Local smoke test (devcontainer or any amd64 py3.11 box)

```bash
bash packaging/build-deb.sh                 # add SKIP_FRONTEND=1 to reuse dist
dpkg-deb -c build-deb/ltc_*_amd64.deb | less
# Prove the vendor dir alone satisfies imports (no venv active):
cd build-deb/stage/www/ltc && python3.11 manage.py check
```

## Puppet follow-ups (admin::loadtest::web)

- Remove the stale `ltc_daemon` cron — `/www/jltc/manage.py daemon` points
  at a removed command and a wrong path.
- After the vendored package is live, drop
  `ig::software::python::django`, `::djangorestframework` and the
  `python3-pandas/matplotlib/scipy` packages (vendor shadows them;
  matplotlib is no longer a dependency at all).
- nginx must serve `/static/` from `/www/ltc/_static` (as for the old app).
