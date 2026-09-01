#!/usr/bin/env bash
#
# Jenkins test step: run the backend test suite.
# Uses SQLite (ltc.test_settings via pytest.ini) — no PostgreSQL needed
# on the build agent. PYTHON defaults to the target interpreter.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="${PYTHON:-python3.11}"
TEST_VENV="${TEST_VENV:-${REPO_DIR}/.test-venv}"
# Internal builds pass REQUIREMENTS_FILE=requirements-innogames.txt
# (with PIP_INDEX_URL exported for the internal package index).
REQUIREMENTS_FILE="${REQUIREMENTS_FILE:-${REPO_DIR}/requirements.txt}"

"${PYTHON}" -m venv "${TEST_VENV}"
"${TEST_VENV}/bin/python" -m pip install --quiet -U pip
"${TEST_VENV}/bin/python" -m pip install --quiet \
    -r "${REQUIREMENTS_FILE}" pytest pytest-django

cd "${REPO_DIR}"
"${TEST_VENV}/bin/python" -m pytest
