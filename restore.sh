#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"
. "$PROJECT_DIR/runtime-env.sh"

if [ "$(id -u)" -ne 0 ]; then
  echo "[ERROR] restore.sh must run as root."
  echo "[ERROR] Example: sudo ./restore.sh /path/to/backup"
  exit 1
fi

if [ "$#" -ne 1 ]; then
  echo "[ERROR] Usage: sudo ./restore.sh /path/to/backup"
  exit 1
fi

BACKUP_DIR="$1"
BACKUP_CONFIG_FILE="$BACKUP_DIR/config.yaml"
BACKUP_DB_FILE="$BACKUP_DIR/edgefusion.db"
SERVICE_WAS_ACTIVE=0
RESTORE_SUCCEEDED=0

if [ ! -f "$BACKUP_CONFIG_FILE" ]; then
  echo "[ERROR] backup config '$BACKUP_CONFIG_FILE' not found."
  exit 1
fi

if [ ! -f "$BACKUP_DB_FILE" ]; then
  echo "[ERROR] backup database '$BACKUP_DB_FILE' not found."
  exit 1
fi

restore_service_if_needed() {
  if [ "$RESTORE_SUCCEEDED" -eq 0 ] && [ "$SERVICE_WAS_ACTIVE" -eq 1 ]; then
    systemctl start "$EDGEFUSION_SERVICE_NAME" >/dev/null 2>&1 || true
  fi
}

trap restore_service_if_needed EXIT

if command -v systemctl >/dev/null 2>&1 && systemctl is-active --quiet "$EDGEFUSION_SERVICE_NAME"; then
  systemctl stop "$EDGEFUSION_SERVICE_NAME"
  SERVICE_WAS_ACTIVE=1
fi

mkdir -p "$EDGEFUSION_LOG_DIR" "$EDGEFUSION_DATA_DIR" "$(dirname "$EDGEFUSION_CONFIG_FILE")"
install -m 0644 "$BACKUP_CONFIG_FILE" "$EDGEFUSION_CONFIG_FILE"
install -m 0640 "$BACKUP_DB_FILE" "$EDGEFUSION_DB_PATH"

if id "$EDGEFUSION_USER" >/dev/null 2>&1; then
  chown "$EDGEFUSION_USER:$EDGEFUSION_USER" "$EDGEFUSION_DB_PATH"
  chown -R "$EDGEFUSION_USER:$EDGEFUSION_USER" "$EDGEFUSION_DATA_DIR" "$EDGEFUSION_LOG_DIR"
fi

RESTORE_SUCCEEDED=1

if command -v systemctl >/dev/null 2>&1 && systemctl cat "$EDGEFUSION_SERVICE_NAME" >/dev/null 2>&1; then
  systemctl start "$EDGEFUSION_SERVICE_NAME"
fi

echo "[OK] restore completed."
echo "[INFO] Restored config: $EDGEFUSION_CONFIG_FILE"
echo "[INFO] Restored database: $EDGEFUSION_DB_PATH"
