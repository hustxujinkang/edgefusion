#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"
. "$PROJECT_DIR/runtime-env.sh"

PURGE=0
SERVICE_FILE="/etc/systemd/system/${EDGEFUSION_SERVICE_NAME}.service"

if [ "$(id -u)" -ne 0 ]; then
  echo "[ERROR] uninstall.sh must run as root."
  echo "[ERROR] Example: sudo ./uninstall.sh"
  exit 1
fi

if [ "${1:-}" = "--purge" ]; then
  PURGE=1
elif [ "$#" -gt 0 ]; then
  echo "[ERROR] Usage: sudo ./uninstall.sh [--purge]"
  exit 1
fi

if command -v systemctl >/dev/null 2>&1; then
  if systemctl cat "$EDGEFUSION_SERVICE_NAME" >/dev/null 2>&1; then
    systemctl stop "$EDGEFUSION_SERVICE_NAME" >/dev/null 2>&1 || true
    systemctl disable "$EDGEFUSION_SERVICE_NAME" >/dev/null 2>&1 || true
  fi
fi

rm -f "$SERVICE_FILE"

if command -v systemctl >/dev/null 2>&1; then
  systemctl daemon-reload
  systemctl reset-failed "$EDGEFUSION_SERVICE_NAME" >/dev/null 2>&1 || true
fi

rm -rf "$EDGEFUSION_APP_DIR"

if [ "$PURGE" -eq 1 ]; then
  rm -rf "$EDGEFUSION_CONFIG_DIR"
  rm -rf "$EDGEFUSION_DATA_DIR"
  rm -rf "$EDGEFUSION_LOG_DIR"
fi

echo "[OK] uninstall completed."
echo "[INFO] Service removed: $SERVICE_FILE"
echo "[INFO] App dir removed: $EDGEFUSION_APP_DIR"

if [ "$PURGE" -eq 1 ]; then
  echo "[INFO] Config dir removed: $EDGEFUSION_CONFIG_DIR"
  echo "[INFO] Data dir removed: $EDGEFUSION_DATA_DIR"
  echo "[INFO] Log dir removed: $EDGEFUSION_LOG_DIR"
else
  echo "[INFO] Config dir preserved: $EDGEFUSION_CONFIG_DIR"
  echo "[INFO] Data dir preserved: $EDGEFUSION_DATA_DIR"
  echo "[INFO] Log dir preserved: $EDGEFUSION_LOG_DIR"
  echo "[INFO] Reinstall later with sudo ./deploy.sh or purge with sudo ./uninstall.sh --purge"
fi
