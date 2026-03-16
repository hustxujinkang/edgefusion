#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

if [ ! -x ".venv/bin/python" ]; then
  echo "[ERROR] virtual environment missing. Run ./install.sh first."
  exit 1
fi

mkdir -p logs
exec .venv/bin/python -m edgefusion.main
