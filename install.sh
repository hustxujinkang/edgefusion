#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

if [ -n "${PYTHON_BIN:-}" ]; then
  CANDIDATES=("$PYTHON_BIN")
else
  CANDIDATES=(python3.10 python3.11 python3.12 python3)
fi

PYTHON_BIN=""
for candidate in "${CANDIDATES[@]}"; do
  if ! command -v "$candidate" >/dev/null 2>&1; then
    continue
  fi

  if "$candidate" -c 'import sys; raise SystemExit(0 if (3, 10) <= sys.version_info[:2] < (3, 13) else 1)' >/dev/null 2>&1; then
    PYTHON_BIN="$candidate"
    break
  fi
done

if [ -z "$PYTHON_BIN" ]; then
  echo "[ERROR] Python 3.10, 3.11, or 3.12 is required."
  exit 1
fi

if [ ! -d ".venv" ]; then
  "$PYTHON_BIN" -m venv .venv
fi

.venv/bin/python -m pip install --upgrade pip setuptools wheel
.venv/bin/python -m pip install -r requirements.txt

mkdir -p logs

if [ ! -f "config.yaml" ]; then
  echo "[ERROR] config.yaml not found."
  exit 1
fi

echo "[OK] install completed."
