#!/usr/bin/env bash
set -euo pipefail

SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SOURCE_DIR"

is_interactive_deploy() {
  [ -t 0 ] && [ -z "${EDGEFUSION_NONINTERACTIVE:-}" ]
}

prompt_with_default() {
  local prompt="$1"
  local default_value="$2"
  local value=""
  read -r -p "$prompt [$default_value]: " value
  printf '%s' "${value:-$default_value}"
}

resolve_deploy_settings() {
  local service_name="${EDGEFUSION_SERVICE_NAME:-edgefusion}"
  if is_interactive_deploy && [ -z "${EDGEFUSION_SERVICE_NAME:-}" ]; then
    service_name="$(prompt_with_default "Service name" "$service_name")"
  fi
  EDGEFUSION_SERVICE_NAME="$service_name"

  local service_user="${EDGEFUSION_USER:-$EDGEFUSION_SERVICE_NAME}"
  if is_interactive_deploy && [ -z "${EDGEFUSION_USER:-}" ]; then
    service_user="$(prompt_with_default "Run as user" "$service_user")"
  fi
  EDGEFUSION_USER="$service_user"

  local app_dir="${EDGEFUSION_APP_DIR:-/opt/$EDGEFUSION_SERVICE_NAME}"
  if is_interactive_deploy && [ -z "${EDGEFUSION_APP_DIR:-}" ]; then
    app_dir="$(prompt_with_default "App dir" "$app_dir")"
  fi
  EDGEFUSION_APP_DIR="$app_dir"

  local config_dir="${EDGEFUSION_CONFIG_DIR:-/etc/$EDGEFUSION_SERVICE_NAME}"
  if is_interactive_deploy && [ -z "${EDGEFUSION_CONFIG_DIR:-}" ]; then
    config_dir="$(prompt_with_default "Config dir" "$config_dir")"
  fi
  EDGEFUSION_CONFIG_DIR="$config_dir"

  local data_dir="${EDGEFUSION_DATA_DIR:-/var/lib/$EDGEFUSION_SERVICE_NAME}"
  if is_interactive_deploy && [ -z "${EDGEFUSION_DATA_DIR:-}" ]; then
    data_dir="$(prompt_with_default "Data dir" "$data_dir")"
  fi
  EDGEFUSION_DATA_DIR="$data_dir"

  local log_dir="${EDGEFUSION_LOG_DIR:-/var/log/$EDGEFUSION_SERVICE_NAME}"
  if is_interactive_deploy && [ -z "${EDGEFUSION_LOG_DIR:-}" ]; then
    log_dir="$(prompt_with_default "Log dir" "$log_dir")"
  fi
  EDGEFUSION_LOG_DIR="$log_dir"

  EDGEFUSION_CONFIG_FILE="${EDGEFUSION_CONFIG_FILE:-$EDGEFUSION_CONFIG_DIR/config.yaml}"
  EDGEFUSION_DB_PATH="${EDGEFUSION_DB_PATH:-$EDGEFUSION_DATA_DIR/edgefusion.db}"
  EDGEFUSION_DB_URL="${EDGEFUSION_DB_URL:-sqlite:///$EDGEFUSION_DB_PATH}"

  export EDGEFUSION_SERVICE_NAME
  export EDGEFUSION_USER
  export EDGEFUSION_APP_DIR
  export EDGEFUSION_CONFIG_DIR
  export EDGEFUSION_DATA_DIR
  export EDGEFUSION_LOG_DIR
  export EDGEFUSION_CONFIG_FILE
  export EDGEFUSION_DB_PATH
  export EDGEFUSION_DB_URL
}

sync_project_tree() {
  if command -v rsync >/dev/null 2>&1; then
    rsync -a --delete \
      --exclude '.git/' \
      --exclude '.venv/' \
      --exclude '__pycache__/' \
      --exclude '.local-data/' \
      --exclude 'logs/' \
      --exclude 'edgefusion.db' \
      "$SOURCE_DIR"/ "$EDGEFUSION_APP_DIR"/
    return
  fi

  find "$EDGEFUSION_APP_DIR" -mindepth 1 -maxdepth 1 \
    ! -name '.venv' \
    ! -name '.local-data' \
    ! -name 'logs' \
    ! -name 'edgefusion.db' \
    -exec rm -rf {} +

  tar \
    -C "$SOURCE_DIR" \
    --exclude='.git' \
    --exclude='.venv' \
    --exclude='__pycache__' \
    --exclude='.local-data' \
    --exclude='logs' \
    --exclude='edgefusion.db' \
    -cf - . | tar -xf - -C "$EDGEFUSION_APP_DIR"
}

resolve_python_bin() {
  local candidates=()
  if [ -n "${PYTHON_BIN:-}" ]; then
    candidates=("$PYTHON_BIN")
  else
    candidates=(python3.10 python3.11 python3.12 python3)
  fi

  PYTHON_BIN=""
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

render_systemd_service() {
  local service_file="/etc/systemd/system/${EDGEFUSION_SERVICE_NAME}.service"
  local service_template_file="$EDGEFUSION_APP_DIR/edgefusion.service.template"

  sed \
    -e "s|__EDGEFUSION_SERVICE_NAME__|$EDGEFUSION_SERVICE_NAME|g" \
    -e "s|__EDGEFUSION_USER__|$EDGEFUSION_USER|g" \
    -e "s|__EDGEFUSION_PROJECT_DIR__|$EDGEFUSION_APP_DIR|g" \
    -e "s|__EDGEFUSION_CONFIG_DIR__|$EDGEFUSION_CONFIG_DIR|g" \
    -e "s|__EDGEFUSION_DATA_DIR__|$EDGEFUSION_DATA_DIR|g" \
    -e "s|__EDGEFUSION_LOG_DIR__|$EDGEFUSION_LOG_DIR|g" \
    -e "s|__EDGEFUSION_CONFIG_FILE__|$EDGEFUSION_CONFIG_FILE|g" \
    -e "s|__EDGEFUSION_DB_PATH__|$EDGEFUSION_DB_PATH|g" \
    -e "s|__EDGEFUSION_DB_URL__|$EDGEFUSION_DB_URL|g" \
    "$service_template_file" > "$service_file"
}

if [ "$(id -u)" -ne 0 ]; then
  echo "[ERROR] deploy.sh must run as root."
  echo "[ERROR] Example: sudo ./deploy.sh"
  exit 1
fi

resolve_deploy_settings

SERVICE_FILE="/etc/systemd/system/${EDGEFUSION_SERVICE_NAME}.service"
DEPLOY_MODE="install"
REQ_FILE="${EDGEFUSION_REQUIREMENTS_FILE:-requirements-prod.txt}"

if ! id "$EDGEFUSION_USER" >/dev/null 2>&1; then
  NOLOGIN_SHELL="/usr/sbin/nologin"
  if [ ! -x "$NOLOGIN_SHELL" ]; then
    NOLOGIN_SHELL="/sbin/nologin"
  fi
  if [ ! -x "$NOLOGIN_SHELL" ]; then
    NOLOGIN_SHELL="/bin/false"
  fi

  useradd --system --home-dir "$EDGEFUSION_APP_DIR" --shell "$NOLOGIN_SHELL" "$EDGEFUSION_USER"
fi

if [ -d "$EDGEFUSION_APP_DIR" ] || [ -f "$SERVICE_FILE" ] || [ -f "$EDGEFUSION_CONFIG_FILE" ]; then
  DEPLOY_MODE="upgrade"
fi

mkdir -p \
  "$EDGEFUSION_APP_DIR" \
  "$EDGEFUSION_CONFIG_DIR" \
  "$EDGEFUSION_DATA_DIR" \
  "$EDGEFUSION_LOG_DIR" \
  "$(dirname "$EDGEFUSION_CONFIG_FILE")" \
  "$(dirname "$EDGEFUSION_DB_PATH")"
sync_project_tree

chmod +x \
  "$EDGEFUSION_APP_DIR/deploy.sh" \
  "$EDGEFUSION_APP_DIR/run_local.sh" \
  "$EDGEFUSION_APP_DIR/backup.sh" \
  "$EDGEFUSION_APP_DIR/restore.sh" \
  "$EDGEFUSION_APP_DIR/uninstall.sh"

resolve_python_bin

if [ ! -f "$EDGEFUSION_APP_DIR/$REQ_FILE" ]; then
  echo "[ERROR] Requirements file '$EDGEFUSION_APP_DIR/$REQ_FILE' not found."
  exit 1
fi

if [ ! -x "$EDGEFUSION_APP_DIR/.venv/bin/python" ]; then
  (
    cd "$EDGEFUSION_APP_DIR"
    "$PYTHON_BIN" -m venv .venv
  )
fi

(
  cd "$EDGEFUSION_APP_DIR"
  .venv/bin/python -m pip install --upgrade pip setuptools wheel
  .venv/bin/python -m pip install -r "$REQ_FILE"
)

if [ ! -f "$EDGEFUSION_CONFIG_FILE" ]; then
  if [ ! -f "$EDGEFUSION_APP_DIR/config.yaml" ]; then
    echo "[ERROR] default config template '$EDGEFUSION_APP_DIR/config.yaml' not found."
    exit 1
  fi

  install -m 0644 "$EDGEFUSION_APP_DIR/config.yaml" "$EDGEFUSION_CONFIG_FILE"
fi

touch "$EDGEFUSION_DB_PATH"

chown -R "$EDGEFUSION_USER:$EDGEFUSION_USER" "$EDGEFUSION_DATA_DIR" "$EDGEFUSION_LOG_DIR"
chown "$EDGEFUSION_USER:$EDGEFUSION_USER" "$EDGEFUSION_DB_PATH"

render_systemd_service

systemctl daemon-reload
systemctl enable "$EDGEFUSION_SERVICE_NAME" >/dev/null

if systemctl is-active --quiet "$EDGEFUSION_SERVICE_NAME"; then
  systemctl restart "$EDGEFUSION_SERVICE_NAME"
  SERVICE_ACTION="restarted"
else
  systemctl start "$EDGEFUSION_SERVICE_NAME"
  SERVICE_ACTION="started"
fi

echo "[OK] ${DEPLOY_MODE^} completed."
echo "[INFO] Service: $EDGEFUSION_SERVICE_NAME"
echo "[INFO] Source checkout: $SOURCE_DIR"
echo "[INFO] App dir: $EDGEFUSION_APP_DIR"
echo "[INFO] Config dir: $EDGEFUSION_CONFIG_DIR"
echo "[INFO] Data dir: $EDGEFUSION_DATA_DIR"
echo "[INFO] Log dir: $EDGEFUSION_LOG_DIR"
echo "[INFO] User: $EDGEFUSION_USER"
echo "[INFO] Service action: $SERVICE_ACTION"
echo "[INFO] Status: systemctl status $EDGEFUSION_SERVICE_NAME"
echo "[INFO] Logs: journalctl -u $EDGEFUSION_SERVICE_NAME -f"
