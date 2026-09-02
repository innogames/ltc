#!/usr/bin/env bash
#
# Build the vendorized LTC Debian package.
#
# All Python dependencies (requirements.txt, incl. the git-hosted
# igrestlogin/serveradmin packages) are installed into /www/ltc/vendor
# inside the package; manage.py and ltc/wsgi.py put that directory at the
# front of sys.path, so the target server needs only python3.11 + nginx.
# The React SPA is built and collectstatic runs at BUILD time — the target
# never compiles assets.
#
# Environment (all optional):
#   PYTHON        interpreter matching the target (default: python3.11)
#   VERSION       package version (default: date +%y%m%d%H%M)
#   BUILD_DIR     work dir (default: ./build-deb under the repo)
#   PACKAGE_NAME  default: ltc
#   APP_DIR       install prefix on the target (default: /www/ltc)
#   SKIP_FRONTEND set to 1 to reuse an existing frontend/dist
#   REQUIREMENTS_FILE  requirements set to vendor (default: requirements.txt,
#                      public deps only). Internal production builds MUST pass
#                      requirements-innogames.txt (adds the SSO backend) and
#                      export PIP_INDEX_URL for the internal package index —
#                      without it, SSO login is unavailable on the target.
#
# Output: ${BUILD_DIR}/${PACKAGE_NAME}_${VERSION}_amd64.deb
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="${PYTHON:-python3.11}"
VERSION="${VERSION:-$(date +%y%m%d%H%M)}"
BUILD_DIR="${BUILD_DIR:-${REPO_DIR}/build-deb}"
PACKAGE_NAME="${PACKAGE_NAME:-ltc}"
APP_DIR="${APP_DIR:-/www/ltc}"
REQUIREMENTS_FILE="${REQUIREMENTS_FILE:-${REPO_DIR}/requirements.txt}"

STAGE="${BUILD_DIR}/stage"
STAGE_APP="${STAGE}${APP_DIR}"
DEB_FILE="${BUILD_DIR}/${PACKAGE_NAME}_${VERSION}_amd64.deb"

echo "==> Building ${PACKAGE_NAME} ${VERSION} with ${PYTHON} into ${BUILD_DIR}"
rm -rf "${STAGE}"
mkdir -p "${STAGE_APP}"

# --- 1. Frontend build (Node >= 20) -----------------------------------------
if [ "${SKIP_FRONTEND:-0}" != "1" ]; then
    echo "==> Building frontend (npm ci && npm run build)"
    (cd "${REPO_DIR}/frontend" && npm ci && npm run build)
fi
test -f "${REPO_DIR}/frontend/dist/index.html" || {
    echo "ERROR: frontend/dist/index.html missing — frontend build failed?"
    exit 1
}

# --- 2. Vendor Python dependencies ------------------------------------------
echo "==> Vendoring Python dependencies into ${STAGE_APP}/vendor"
TOOL_VENV="${BUILD_DIR}/.pkg-venv"
rm -rf "${TOOL_VENV}"
# Prefer an isolated tooling venv; fall back to the interpreter's own pip
# (fine with --target) where python3.x-venv/ensurepip is unavailable.
if "${PYTHON}" -m venv "${TOOL_VENV}" 2>/dev/null; then
    PIP="${TOOL_VENV}/bin/python -m pip"
    ${PIP} install --quiet -U pip
elif "${PYTHON}" -m pip --version >/dev/null 2>&1; then
    echo "==> venv unavailable for ${PYTHON}; using its pip directly"
    PIP="${PYTHON} -m pip"
else
    echo "ERROR: ${PYTHON} has neither venv nor pip available"
    exit 1
fi
${PIP} install \
    -r "${REQUIREMENTS_FILE}" \
    --target "${STAGE_APP}/vendor" \
    --ignore-installed --no-cache-dir

# --- 3. Application files -----------------------------------------------------
echo "==> Copying application files"
cp "${REPO_DIR}/manage.py" "${STAGE_APP}/"
cp -r "${REPO_DIR}/ltc" "${STAGE_APP}/ltc"
# Puppet templates local_settings.py on the target; never ship a real one.
rm -f "${STAGE_APP}/ltc/local_settings.py"
mkdir -p "${STAGE_APP}/frontend"
cp -r "${REPO_DIR}/frontend/dist" "${STAGE_APP}/frontend/dist"

# --- 4. collectstatic at build time ------------------------------------------
# The vendor bootstrap in the staged manage.py picks up the vendored Django;
# settings boot without local_settings thanks to env-var defaults, and
# collectstatic needs no database.
echo "==> Running collectstatic in the stage tree"
(cd "${STAGE_APP}" && "${PYTHON}" manage.py collectstatic --noinput -v0)

# Byte-code caches would be stale/foreign on the target.
find "${STAGE_APP}" -name '__pycache__' -type d -prune -exec rm -rf {} +
find "${STAGE_APP}" -name '*.pyc' -delete

# --- 5. Debian metadata --------------------------------------------------------
echo "==> Writing DEBIAN metadata"
mkdir -p "${STAGE}/DEBIAN"

cat > "${STAGE}/DEBIAN/control" <<EOF
Package: ${PACKAGE_NAME}
Architecture: amd64
Maintainer: InnoGames System Administration (it@innogames.com)
Version: ${VERSION}
Section: base
Description: LoadtestCenter (self-contained: Python deps vendored in ${APP_DIR}/vendor)
Depends: nginx,
         python3.11
EOF

cat > "${STAGE}/DEBIAN/preinst" <<'EOF'
#!/bin/bash -e
# nginx keeps running: it only proxies and serves static files from disk.
service ltc stop || true
EOF

cat > "${STAGE}/DEBIAN/postinst" <<EOF
#!/bin/bash -e
# Stale bytecode from previous package layouts breaks imports and keeps
# dpkg from removing obsolete directories — clear it before migrating.
find ${APP_DIR} -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true

# Static files are prebuilt and shipped; only migrations run on the target.
python3.11 ${APP_DIR}/manage.py migrate --noinput

# Drop root-owned bytecode caches that the migrate above just created.
find ${APP_DIR}/vendor -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true

service ltc start || service ltc restart
EOF

chmod 0755 "${STAGE}/DEBIAN/preinst" "${STAGE}/DEBIAN/postinst"

# --- 6. Build the package -------------------------------------------------------
echo "==> dpkg-deb"
dpkg-deb --root-owner-group -b "${STAGE}" "${DEB_FILE}"
rm -rf "${TOOL_VENV}"
echo "==> Built ${DEB_FILE}"
