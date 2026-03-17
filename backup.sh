#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"
. "$PROJECT_DIR/runtime-env.sh"

if [ "$(id -u)" -ne 0 ]; then
  echo "[ERROR] backup.sh must run as root."
  echo "[ERROR] Example: sudo ./backup.sh"
  exit 1
fi

if [ ! -f "$EDGEFUSION_CONFIG_FILE" ]; then
  echo "[ERROR] config file '$EDGEFUSION_CONFIG_FILE' not found."
  exit 1
fi

if [ ! -f "$EDGEFUSION_DB_PATH" ]; then
  echo "[ERROR] database file '$EDGEFUSION_DB_PATH' not found."
  exit 1
fi

BACKUP_ROOT="${1:-/var/backups/$EDGEFUSION_SERVICE_NAME}"
TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP_DIR="$BACKUP_ROOT/$TIMESTAMP"
SERVICE_WAS_ACTIVE=0

restart_service_if_needed() {
  if [ "$SERVICE_WAS_ACTIVE" -eq 1 ]; then
    systemctl start "$EDGEFUSION_SERVICE_NAME"
  fi
}

trap restart_service_if_needed EXIT

if command -v systemctl >/dev/null 2>&1 && systemctl is-active --quiet "$EDGEFUSION_SERVICE_NAME"; then
  systemctl stop "$EDGEFUSION_SERVICE_NAME"
  SERVICE_WAS_ACTIVE=1
fi

mkdir -p "$BACKUP_DIR"
install -m 0644 "$EDGEFUSION_CONFIG_FILE" "$BACKUP_DIR/config.yaml"
install -m 0640 "$EDGEFUSION_DB_PATH" "$BACKUP_DIR/edgefusion.db"

echo "[OK] backup completed."
echo "[INFO] Backup dir: $BACKUP_DIR"
echo "[INFO] Config file: $BACKUP_DIR/config.yaml"
echo "[INFO] Database file: $BACKUP_DIR/edgefusion.db"
