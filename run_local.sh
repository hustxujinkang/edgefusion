#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

export EDGEFUSION_SERVICE_NAME="${EDGEFUSION_SERVICE_NAME:-edgefusion-local}"
export EDGEFUSION_CONFIG_FILE="${EDGEFUSION_CONFIG_FILE:-$PROJECT_DIR/config.yaml}"
export EDGEFUSION_LOG_DIR="${EDGEFUSION_LOG_DIR:-$PROJECT_DIR/logs}"
export EDGEFUSION_DATA_DIR="${EDGEFUSION_DATA_DIR:-$PROJECT_DIR/.local-data}"
export EDGEFUSION_DB_PATH="${EDGEFUSION_DB_PATH:-$PROJECT_DIR/edgefusion.db}"
export EDGEFUSION_DB_URL="${EDGEFUSION_DB_URL:-sqlite:///$EDGEFUSION_DB_PATH}"

REQ_FILE="${EDGEFUSION_REQUIREMENTS_FILE:-requirements.txt}"
REINSTALL=0

if [ "${1:-}" = "--reinstall" ]; then
  REINSTALL=1
fi

find_bootstrap_python() {
  local candidates=()
  if [ -n "${PYTHON_BIN:-}" ]; then
    candidates=("$PYTHON_BIN")
  else
    candidates=(python3.10 python3.11 python3.12 python3)
  fi

  for candidate in "${candidates[@]}"; do
    if ! command -v "$candidate" >/dev/null 2>&1; then
      continue
    fi

    if "$candidate" -c 'import sys; raise SystemExit(0 if (3, 10) <= sys.version_info[:2] < (3, 13) else 1)' >/dev/null 2>&1; then
      PYTHON_BIN="$candidate"
      export PYTHON_BIN
      return
    fi
  done

  echo "[ERROR] Python 3.10, 3.11, or 3.12 is required."
  exit 1
}

venv_supported() {
  .venv/bin/python -c 'import sys; raise SystemExit(0 if (3, 10) <= sys.version_info[:2] < (3, 13) else 1)' >/dev/null 2>&1
}

if [ -x ".venv/bin/python" ]; then
  if ! venv_supported; then
    echo "[ERROR] Existing .venv uses an unsupported Python version."
    echo "[ERROR] Remove .venv and install Python 3.10, 3.11, or 3.12."
    exit 1
  fi
else
  find_bootstrap_python
  "$PYTHON_BIN" -m venv .venv
  REINSTALL=1
fi

if [ ! -f "$REQ_FILE" ]; then
  echo "[ERROR] Requirements file '$REQ_FILE' not found."
  exit 1
fi

if [ "$REINSTALL" -eq 0 ]; then
  if ! .venv/bin/python -c 'import yaml, flask, sqlalchemy' >/dev/null 2>&1; then
    REINSTALL=1
  fi
fi

if [ "$REINSTALL" -eq 1 ]; then
  .venv/bin/python -m pip install --upgrade pip setuptools wheel
  .venv/bin/python -m pip install -r "$REQ_FILE"
fi

if [ ! -f "$EDGEFUSION_CONFIG_FILE" ]; then
  echo "[ERROR] local config file '$EDGEFUSION_CONFIG_FILE' not found."
  exit 1
fi

mkdir -p "$EDGEFUSION_LOG_DIR" "$EDGEFUSION_DATA_DIR"
touch "$EDGEFUSION_DB_PATH"
exec .venv/bin/python -m edgefusion.main
