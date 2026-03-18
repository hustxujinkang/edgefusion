#!/usr/bin/env bash
# =============================================================================
#  EdgeFusion 部署脚本 (工控机优化版)
#
#  用法:
#    sudo ./deploy.sh                    交互式部署（首次安装/升级）
#    sudo ./deploy.sh --reinstall        强制重建虚拟环境和依赖
#    sudo ./deploy.sh --rollback         回滚到上一次部署快照
#    sudo EDGEFUSION_NONINTERACTIVE=1 EDGEFUSION_SERVICE_NAME=xxx ./deploy.sh
#                                        非交互式（CI/批量部署）
# =============================================================================
set -euo pipefail

SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SOURCE_DIR"

# ---------------------------------------------------------------------------
#  工具函数
# ---------------------------------------------------------------------------
log() {
  local level="$1"; shift
  printf '[%s] [%-5s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$level" "$*" >&2
}

die() {
  log ERROR "$@"
  exit 1
}

is_interactive() {
  [ -t 0 ] && [ -z "${EDGEFUSION_NONINTERACTIVE:-}" ]
}

prompt_with_default() {
  local prompt="$1" default="$2" value=""
  read -r -p "$prompt [$default]: " value
  printf '%s' "${value:-$default}"
}

# ---------------------------------------------------------------------------
#  参数解析
# ---------------------------------------------------------------------------
REINSTALL=0
ROLLBACK=0
for arg in "$@"; do
  case "$arg" in
    --reinstall) REINSTALL=1 ;;
    --rollback)  ROLLBACK=1 ;;
    *)           log WARN "未知参数: $arg" ;;
  esac
done

# ---------------------------------------------------------------------------
#  权限检查
# ---------------------------------------------------------------------------
[ "$(id -u)" -eq 0 ] || die "deploy.sh 必须以 root 运行。用法: sudo ./deploy.sh"

# ---------------------------------------------------------------------------
#  部署参数收集（消除重复代码）
# ---------------------------------------------------------------------------
resolve_setting() {
  local var_name="$1" prompt_text="$2" default_value="$3"
  local current="${!var_name:-}"

  if [ -n "$current" ]; then
    printf '%s' "$current"
  elif is_interactive; then
    prompt_with_default "$prompt_text" "$default_value"
  else
    printf '%s' "$default_value"
  fi
}

resolve_deploy_settings() {
  EDGEFUSION_SERVICE_NAME="$(resolve_setting EDGEFUSION_SERVICE_NAME "Service name" "edgefusion")"
  EDGEFUSION_USER="$(resolve_setting EDGEFUSION_USER "Run as user" "$EDGEFUSION_SERVICE_NAME")"
  EDGEFUSION_APP_DIR="$(resolve_setting EDGEFUSION_APP_DIR "App dir" "/opt/$EDGEFUSION_SERVICE_NAME")"
  EDGEFUSION_CONFIG_DIR="$(resolve_setting EDGEFUSION_CONFIG_DIR "Config dir" "/etc/$EDGEFUSION_SERVICE_NAME")"
  EDGEFUSION_DATA_DIR="$(resolve_setting EDGEFUSION_DATA_DIR "Data dir" "/var/lib/$EDGEFUSION_SERVICE_NAME")"
  EDGEFUSION_LOG_DIR="$(resolve_setting EDGEFUSION_LOG_DIR "Log dir" "/var/log/$EDGEFUSION_SERVICE_NAME")"

  EDGEFUSION_CONFIG_FILE="${EDGEFUSION_CONFIG_FILE:-$EDGEFUSION_CONFIG_DIR/config.yaml}"
  EDGEFUSION_DB_PATH="${EDGEFUSION_DB_PATH:-$EDGEFUSION_DATA_DIR/edgefusion.db}"
  EDGEFUSION_DB_URL="${EDGEFUSION_DB_URL:-sqlite:///$EDGEFUSION_DB_PATH}"

  export EDGEFUSION_SERVICE_NAME EDGEFUSION_USER EDGEFUSION_APP_DIR \
         EDGEFUSION_CONFIG_DIR EDGEFUSION_DATA_DIR EDGEFUSION_LOG_DIR \
         EDGEFUSION_CONFIG_FILE EDGEFUSION_DB_PATH EDGEFUSION_DB_URL
}

# ---------------------------------------------------------------------------
#  Python 解释器探测
# ---------------------------------------------------------------------------
resolve_python_bin() {
  local candidates=()
  if [ -n "${PYTHON_BIN:-}" ]; then
    candidates=("$PYTHON_BIN")
  else
    candidates=(python3.10 python3.11 python3.12 python3)
  fi

  local version_check='
import sys, importlib.util
ver_ok = (3,10) <= sys.version_info[:2] < (3,13)
has_venv = importlib.util.find_spec("venv") is not None
has_pip = importlib.util.find_spec("ensurepip") is not None or importlib.util.find_spec("pip") is not None
raise SystemExit(0 if ver_ok and has_venv and has_pip else 1)
'

  for candidate in "${candidates[@]}"; do
    command -v "$candidate" >/dev/null 2>&1 || continue
    if "$candidate" -c "$version_check" 2>/dev/null; then
      PYTHON_BIN="$candidate"
      export PYTHON_BIN
      log INFO "Python 解释器: $(command -v "$PYTHON_BIN") ($("$PYTHON_BIN" --version 2>&1))"
      return
    fi
  done

  die "未找到可用的 Python 3.10-3.12（需同时具备 pip 和 venv 模块）。请运行: sudo ./install-python.sh"
}

# ---------------------------------------------------------------------------
#  文件同步
# ---------------------------------------------------------------------------
sync_project_tree() {
  local exclude_list=(.git .venv __pycache__ .local-data logs edgefusion.db)

  if command -v rsync >/dev/null 2>&1; then
    local rsync_excludes=()
    for item in "${exclude_list[@]}"; do
      rsync_excludes+=(--exclude "${item}/")
    done
    rsync -a --delete "${rsync_excludes[@]}" "$SOURCE_DIR"/ "$EDGEFUSION_APP_DIR"/
    return
  fi

  # fallback: tar 方式
  find "$EDGEFUSION_APP_DIR" -mindepth 1 -maxdepth 1 \
    $(printf "! -name '%s' " "${exclude_list[@]}") \
    -exec rm -rf {} +

  local tar_excludes=()
  for item in "${exclude_list[@]}"; do
    tar_excludes+=(--exclude="$item")
  done
  tar -C "$SOURCE_DIR" "${tar_excludes[@]}" -cf - . \
    | tar -xf - -C "$EDGEFUSION_APP_DIR"
}

# ---------------------------------------------------------------------------
#  部署前快照（用于回滚）
# ---------------------------------------------------------------------------
readonly SNAPSHOT_DIR="/var/backups/edgefusion-snapshots"

create_snapshot() {
  if [ ! -d "$EDGEFUSION_APP_DIR" ]; then
    log INFO "首次部署，无需创建快照。"
    return
  fi

  mkdir -p "$SNAPSHOT_DIR"

  local snapshot_name
  snapshot_name="${EDGEFUSION_SERVICE_NAME}_$(date '+%Y%m%d_%H%M%S').tar.gz"

  log INFO "创建部署快照: $SNAPSHOT_DIR/$snapshot_name"
  tar -czf "$SNAPSHOT_DIR/$snapshot_name" \
    -C "$(dirname "$EDGEFUSION_APP_DIR")" "$(basename "$EDGEFUSION_APP_DIR")" \
    2>/dev/null || log WARN "快照创建失败（非致命），继续部署。"

  # 只保留最近 3 个快照，工控机存储有限
  # shellcheck disable=SC2012
  ls -1t "$SNAPSHOT_DIR"/"${EDGEFUSION_SERVICE_NAME}"_*.tar.gz 2>/dev/null \
    | tail -n +4 | xargs -r rm -f
}

do_rollback() {
  local latest
  latest=$(ls -1t "$SNAPSHOT_DIR"/"${EDGEFUSION_SERVICE_NAME}"_*.tar.gz 2>/dev/null | head -1)

  if [ -z "$latest" ]; then
    die "没有找到可用的快照，无法回滚。"
  fi

  log INFO "回滚到快照: $latest"

  # 停止服务
  systemctl stop "$EDGEFUSION_SERVICE_NAME" 2>/dev/null || true

  # 清空并还原
  rm -rf "$EDGEFUSION_APP_DIR"
  mkdir -p "$(dirname "$EDGEFUSION_APP_DIR")"
  tar -xzf "$latest" -C "$(dirname "$EDGEFUSION_APP_DIR")"

  systemctl start "$EDGEFUSION_SERVICE_NAME"
  log INFO "回滚完成，服务已重启。"
}

# ---------------------------------------------------------------------------
#  创建系统用户
# ---------------------------------------------------------------------------
ensure_service_user() {
  if id "$EDGEFUSION_USER" >/dev/null 2>&1; then
    log INFO "服务用户 '$EDGEFUSION_USER' 已存在。"
    return
  fi

  local nologin=""
  for shell in /usr/sbin/nologin /sbin/nologin /bin/false; do
    [ -x "$shell" ] && nologin="$shell" && break
  done
  [ -z "$nologin" ] && die "找不到 nologin shell。"

  useradd --system --home-dir "$EDGEFUSION_APP_DIR" --shell "$nologin" "$EDGEFUSION_USER"
  log INFO "已创建系统用户: $EDGEFUSION_USER"
}

# ---------------------------------------------------------------------------
#  虚拟环境 & 依赖安装
# ---------------------------------------------------------------------------
setup_venv_and_deps() {
  local req_file="${EDGEFUSION_REQUIREMENTS_FILE:-requirements-prod.txt}"
  local venv_python="$EDGEFUSION_APP_DIR/.venv/bin/python"
  local req_path="$EDGEFUSION_APP_DIR/$req_file"

  [ -f "$req_path" ] || die "依赖文件 '$req_path' 不存在。"

  # 如果 --reinstall 或 venv 不存在，重建
  if [ "$REINSTALL" -eq 1 ] && [ -d "$EDGEFUSION_APP_DIR/.venv" ]; then
    log INFO "--reinstall: 删除现有虚拟环境..."
    rm -rf "$EDGEFUSION_APP_DIR/.venv"
  fi

  if [ ! -x "$venv_python" ]; then
    log INFO "创建虚拟环境..."
    (cd "$EDGEFUSION_APP_DIR" && "$PYTHON_BIN" -m venv .venv)
  fi

  # 哈希检测：requirements 未变且非强制重装则跳过
  local hash_file="$EDGEFUSION_APP_DIR/.venv/.requirements.sha256"
  local current_hash
  current_hash=$(sha256sum "$req_path" | awk '{print $1}')

  local need_install=1
  if [ "$REINSTALL" -eq 0 ] && [ -f "$hash_file" ] && [ "$(cat "$hash_file")" = "$current_hash" ]; then
    log INFO "依赖未变更，跳过安装。"
    need_install=0
  fi

  if [ "$need_install" -eq 1 ]; then
    log INFO "升级 pip（失败不阻塞）..."
    "$venv_python" -m pip install --upgrade pip setuptools wheel 2>/dev/null \
      || log WARN "pip 升级失败（可能离线），继续使用现有版本。"

    log INFO "安装依赖: $req_file"
    (cd "$EDGEFUSION_APP_DIR" && "$venv_python" -m pip install -r "$req_file")

    echo "$current_hash" > "$hash_file"
    log INFO "依赖安装完成。"
  fi
}

# ---------------------------------------------------------------------------
#  配置文件 & 数据库
# ---------------------------------------------------------------------------
setup_config_and_db() {
  if [ ! -f "$EDGEFUSION_CONFIG_FILE" ]; then
    local template="$EDGEFUSION_APP_DIR/config.yaml"
    [ -f "$template" ] || die "默认配置模板 '$template' 不存在。"
    install -m 0644 "$template" "$EDGEFUSION_CONFIG_FILE"
    log INFO "已从模板初始化配置: $EDGEFUSION_CONFIG_FILE"
  fi

  [ -f "$EDGEFUSION_DB_PATH" ] || touch "$EDGEFUSION_DB_PATH"
}

# ---------------------------------------------------------------------------
#  权限设置（避免不必要的递归 chown）
# ---------------------------------------------------------------------------
fix_permissions() {
  # 对数据和日志目录，仅在 owner 不对时才 chown -R
  for dir in "$EDGEFUSION_DATA_DIR" "$EDGEFUSION_LOG_DIR"; do
    local current_owner
    current_owner=$(stat -c '%U' "$dir" 2>/dev/null || echo "")
    if [ "$current_owner" != "$EDGEFUSION_USER" ]; then
      log INFO "修正目录权限: $dir -> $EDGEFUSION_USER"
      chown -R "$EDGEFUSION_USER:$EDGEFUSION_USER" "$dir"
    fi
  done

  # DB 文件单独处理
  chown "$EDGEFUSION_USER:$EDGEFUSION_USER" "$EDGEFUSION_DB_PATH"
}

# ---------------------------------------------------------------------------
#  systemd 单元渲染 & 管理
# ---------------------------------------------------------------------------
render_systemd_service() {
  local service_file="/etc/systemd/system/${EDGEFUSION_SERVICE_NAME}.service"
  local template="$EDGEFUSION_APP_DIR/edgefusion.service.template"

  [ -f "$template" ] || die "systemd 模板 '$template' 不存在。"

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
    "$template" > "$service_file"

  log INFO "systemd 单元已写入: $service_file"
}

manage_service() {
  systemctl daemon-reload
  systemctl enable "$EDGEFUSION_SERVICE_NAME" >/dev/null

  local action
  if systemctl is-active --quiet "$EDGEFUSION_SERVICE_NAME"; then
    systemctl restart "$EDGEFUSION_SERVICE_NAME"
    action="restarted"
  else
    systemctl start "$EDGEFUSION_SERVICE_NAME"
    action="started"
  fi

  # 等待几秒后验证服务是否存活
  sleep 2
  if systemctl is-active --quiet "$EDGEFUSION_SERVICE_NAME"; then
    log INFO "服务已${action}且运行正常。"
  else
    log ERROR "服务${action}后未能正常运行！请检查日志:"
    log ERROR "  journalctl -u $EDGEFUSION_SERVICE_NAME -n 30 --no-pager"
    exit 1
  fi
}

# ---------------------------------------------------------------------------
#  部署摘要
# ---------------------------------------------------------------------------
print_summary() {
  local mode="$1"
  cat >&2 <<EOF

============================================================
  [OK] ${mode^} 完成
------------------------------------------------------------
  Service : $EDGEFUSION_SERVICE_NAME
  Source  : $SOURCE_DIR
  App dir : $EDGEFUSION_APP_DIR
  Config  : $EDGEFUSION_CONFIG_DIR
  Data    : $EDGEFUSION_DATA_DIR
  Logs    : $EDGEFUSION_LOG_DIR
  User    : $EDGEFUSION_USER
------------------------------------------------------------
  查看状态 : systemctl status $EDGEFUSION_SERVICE_NAME
  查看日志 : journalctl -u $EDGEFUSION_SERVICE_NAME -f
============================================================
EOF
}

# ---------------------------------------------------------------------------
#  主流程
# ---------------------------------------------------------------------------
main() {
  log INFO "========== EdgeFusion 部署开始 =========="

  resolve_deploy_settings

  # 回滚模式：直接回滚并退出
  if [ "$ROLLBACK" -eq 1 ]; then
    do_rollback
    exit 0
  fi

  # 判断安装/升级模式
  local deploy_mode="install"
  local service_file="/etc/systemd/system/${EDGEFUSION_SERVICE_NAME}.service"
  if [ -d "$EDGEFUSION_APP_DIR" ] || [ -f "$service_file" ] || [ -f "$EDGEFUSION_CONFIG_FILE" ]; then
    deploy_mode="upgrade"
  fi

  log INFO "部署模式: $deploy_mode"

  # 升级前创建快照
  [ "$deploy_mode" = "upgrade" ] && create_snapshot

  ensure_service_user

  mkdir -p "$EDGEFUSION_APP_DIR" "$EDGEFUSION_CONFIG_DIR" \
           "$EDGEFUSION_DATA_DIR" "$EDGEFUSION_LOG_DIR" \
           "$(dirname "$EDGEFUSION_CONFIG_FILE")" \
           "$(dirname "$EDGEFUSION_DB_PATH")"

  sync_project_tree

  # chmod 只对实际存在的脚本生效
  for script in deploy.sh run_local.sh backup.sh restore.sh; do
    local path="$EDGEFUSION_APP_DIR/$script"
    [ -f "$path" ] && chmod +x "$path"
  done

  resolve_python_bin
  setup_venv_and_deps
  setup_config_and_db
  fix_permissions
  render_systemd_service
  manage_service

  print_summary "$deploy_mode"
}

main
