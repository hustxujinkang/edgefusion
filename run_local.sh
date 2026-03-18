#!/usr/bin/env bash
# =============================================================================
#  EdgeFusion 启动脚本 (工控机优化版)
#
#  用法:
#    ./start.sh                  正常启动（增量检测依赖）
#    ./start.sh --reinstall      强制重装依赖
#    ./start.sh --check          仅做环境检查，不启动服务
# =============================================================================
set -euo pipefail

# ---------------------------------------------------------------------------
#  基础路径 & 环境变量
# ---------------------------------------------------------------------------
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

export EDGEFUSION_SERVICE_NAME="${EDGEFUSION_SERVICE_NAME:-edgefusion-local}"
export EDGEFUSION_CONFIG_FILE="${EDGEFUSION_CONFIG_FILE:-$PROJECT_DIR/config.yaml}"
export EDGEFUSION_LOG_DIR="${EDGEFUSION_LOG_DIR:-$PROJECT_DIR/logs}"
export EDGEFUSION_DATA_DIR="${EDGEFUSION_DATA_DIR:-$PROJECT_DIR/.local-data}"
export EDGEFUSION_DB_PATH="${EDGEFUSION_DB_PATH:-$PROJECT_DIR/edgefusion.db}"
export EDGEFUSION_DB_URL="${EDGEFUSION_DB_URL:-sqlite:///$EDGEFUSION_DB_PATH}"

readonly VENV_DIR="$PROJECT_DIR/.venv"
readonly VENV_PYTHON="$VENV_DIR/bin/python"
readonly REQ_FILE="${EDGEFUSION_REQUIREMENTS_FILE:-requirements.txt}"
readonly REQ_HASH_FILE="$VENV_DIR/.requirements.sha256"
readonly LOCK_FILE="/tmp/edgefusion-${EDGEFUSION_SERVICE_NAME}.lock"
readonly MAX_RETRIES="${EDGEFUSION_MAX_RETRIES:-3}"
readonly RETRY_DELAY="${EDGEFUSION_RETRY_DELAY:-5}"

# ---------------------------------------------------------------------------
#  解析命令行参数
# ---------------------------------------------------------------------------
REINSTALL=0
CHECK_ONLY=0
for arg in "$@"; do
  case "$arg" in
    --reinstall) REINSTALL=1 ;;
    --check)     CHECK_ONLY=1 ;;
    *)           echo "[WARN] 未知参数: $arg" ;;
  esac
done

# ---------------------------------------------------------------------------
#  工具函数
# ---------------------------------------------------------------------------
log() {
  # 带时间戳的日志，方便工控机离线排查
  local level="$1"; shift
  printf '[%s] [%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$level" "$*" >&2
}

cleanup() {
  rm -f "$LOCK_FILE"
}

# ---------------------------------------------------------------------------
#  防重复启动（文件锁）
# ---------------------------------------------------------------------------
acquire_lock() {
  if [ -f "$LOCK_FILE" ]; then
    local old_pid
    old_pid=$(cat "$LOCK_FILE" 2>/dev/null || true)
    if [ -n "$old_pid" ] && kill -0 "$old_pid" 2>/dev/null; then
      log ERROR "服务已在运行 (PID=$old_pid)，如需重启请先停止旧进程。"
      exit 1
    fi
    log WARN "发现残留锁文件(PID=$old_pid 已不存在)，清理后继续。"
    rm -f "$LOCK_FILE"
  fi
  echo $$ > "$LOCK_FILE"
  trap cleanup EXIT INT TERM
}

# ---------------------------------------------------------------------------
#  Python 解释器探测
# ---------------------------------------------------------------------------
find_bootstrap_python() {
  local candidates=()
  if [ -n "${PYTHON_BIN:-}" ]; then
    candidates=("$PYTHON_BIN")
  else
    candidates=(python3.10 python3.11 python3.12 python3)
  fi

  # 版本检查 + pip/venv 可用性检查
  # 仅版本号对但缺少 ensurepip/venv 的解释器（如系统残缺的 python3.10）会被跳过
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
      log INFO "使用 Python 解释器: $(command -v "$PYTHON_BIN") ($("$PYTHON_BIN" --version 2>&1))"
      return
    fi
  done

  log ERROR "未找到可用的 Python 3.10-3.12（需同时具备 pip 和 venv 模块）。"
  log ERROR "系统自带的 Python 可能缺少 pip，请运行: sudo ./install-python.sh"
  exit 1
}

# ---------------------------------------------------------------------------
#  虚拟环境检查 & 创建
# ---------------------------------------------------------------------------
ensure_venv() {
  local version_check='import sys; raise SystemExit(0 if (3,10) <= sys.version_info[:2] < (3,13) else 1)'

  if [ -x "$VENV_PYTHON" ]; then
    if ! "$VENV_PYTHON" -c "$version_check" 2>/dev/null; then
      log ERROR "现有 .venv 的 Python 版本不受支持，请删除 .venv 后重试。"
      exit 1
    fi
    log INFO "虚拟环境已存在，Python=$($VENV_PYTHON --version 2>&1)"
  else
    find_bootstrap_python
    log INFO "创建虚拟环境..."
    "$PYTHON_BIN" -m venv "$VENV_DIR"
    REINSTALL=1
  fi
}

# ---------------------------------------------------------------------------
#  依赖安装（基于 requirements.txt 哈希做增量判断）
# ---------------------------------------------------------------------------
install_deps() {
  if [ ! -f "$REQ_FILE" ]; then
    log ERROR "依赖文件 '$REQ_FILE' 不存在。"
    exit 1
  fi

  # 用 requirements.txt 的哈希判断是否需要重装，比 import 探测更准确
  local current_hash
  current_hash=$(sha256sum "$REQ_FILE" | awk '{print $1}')

  if [ "$REINSTALL" -eq 0 ]; then
    if [ -f "$REQ_HASH_FILE" ] && [ "$(cat "$REQ_HASH_FILE")" = "$current_hash" ]; then
      # 哈希一致，再做一次快速 import 兜底
      if "$VENV_PYTHON" -c 'import yaml, flask, sqlalchemy' 2>/dev/null; then
        log INFO "依赖未变更，跳过安装。"
        return
      fi
    fi
    log INFO "检测到依赖变更，执行安装..."
    REINSTALL=1
  fi

  if [ "$REINSTALL" -eq 1 ]; then
    # 工控机可能离线，pip upgrade 失败不应阻塞启动
    log INFO "升级 pip（失败不阻塞）..."
    "$VENV_PYTHON" -m pip install --upgrade pip setuptools wheel 2>/dev/null || \
      log WARN "pip 升级失败（可能离线），继续使用现有版本。"

    log INFO "安装依赖: $REQ_FILE"
    "$VENV_PYTHON" -m pip install -r "$REQ_FILE"

    # 记录哈希，下次可跳过
    echo "$current_hash" > "$REQ_HASH_FILE"
    log INFO "依赖安装完成。"
  fi
}

# ---------------------------------------------------------------------------
#  运行前检查
# ---------------------------------------------------------------------------
preflight_check() {
  if [ ! -f "$EDGEFUSION_CONFIG_FILE" ]; then
    log ERROR "配置文件 '$EDGEFUSION_CONFIG_FILE' 不存在。"
    exit 1
  fi

  mkdir -p "$EDGEFUSION_LOG_DIR" "$EDGEFUSION_DATA_DIR"

  # 仅在 DB 文件不存在时创建，避免不必要地修改 mtime
  [ -f "$EDGEFUSION_DB_PATH" ] || touch "$EDGEFUSION_DB_PATH"

  # 磁盘空间预警（工控机存储有限）
  local avail_kb
  avail_kb=$(df -P "$PROJECT_DIR" | awk 'NR==2 {print $4}')
  if [ "${avail_kb:-0}" -lt 102400 ]; then
    log WARN "磁盘剩余空间不足 100MB (${avail_kb}KB)，请注意清理。"
  fi
}

# ---------------------------------------------------------------------------
#  启动服务（带自动重试）
# ---------------------------------------------------------------------------
run_service() {
  local attempt=0
  while [ "$attempt" -lt "$MAX_RETRIES" ]; do
    attempt=$((attempt + 1))
    log INFO "启动 EdgeFusion 服务 (第 ${attempt}/${MAX_RETRIES} 次)..."

    # 使用 exec 仅在最后一次尝试，前几次需要捕获退出码
    if [ "$attempt" -eq "$MAX_RETRIES" ]; then
      exec "$VENV_PYTHON" -m edgefusion.main
    fi

    set +e
    "$VENV_PYTHON" -m edgefusion.main
    local exit_code=$?
    set -e

    if [ "$exit_code" -eq 0 ]; then
      log INFO "服务正常退出。"
      break
    fi

    log WARN "服务异常退出 (code=$exit_code)，${RETRY_DELAY}s 后重试..."
    sleep "$RETRY_DELAY"
  done
}

# ---------------------------------------------------------------------------
#  主流程
# ---------------------------------------------------------------------------
main() {
  log INFO "========== EdgeFusion 启动 =========="
  log INFO "项目目录: $PROJECT_DIR"

  acquire_lock
  ensure_venv
  install_deps
  preflight_check

  if [ "$CHECK_ONLY" -eq 1 ]; then
    log INFO "环境检查通过（--check 模式，不启动服务）。"
    exit 0
  fi

  run_service
}

main

