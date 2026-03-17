#!/usr/bin/env bash
# =============================================================================
#  install-python.sh — 独立 Python 运行时安装脚本
#
#  从 python-build-standalone 项目获取预编译 Python，解压到指定目录。
#  与 deploy.sh / start.sh 完全解耦，跑一次即可。
#
#  用法:
#    sudo ./install-python.sh                         # 自动检测架构，安装 3.11
#    sudo ./install-python.sh --version 3.12          # 指定版本
#    sudo ./install-python.sh --prefix /usr/local     # 自定义安装路径
#    sudo ./install-python.sh --from vendor/cpython-*.tar.gz   # 离线安装
#    sudo ./install-python.sh --mirror nju             # 指定国内镜像
#    sudo ./install-python.sh --check                  # 仅检查，不安装
#    sudo ./install-python.sh --uninstall              # 卸载
#
#  环境变量 (优先级高于命令行默认值):
#    PYTHON_INSTALL_VERSION   目标 Python 版本，如 3.11
#    PYTHON_INSTALL_PREFIX    安装前缀，默认 /opt/python${version}
#    PYTHON_INSTALL_MIRROR    镜像名或完整 URL
# =============================================================================
set -euo pipefail

# ---------------------------------------------------------------------------
#  默认值
# ---------------------------------------------------------------------------
VERSION="${PYTHON_INSTALL_VERSION:-3.11}"
PREFIX=""                       # 留空，后面根据 VERSION 推导
MIRROR="${PYTHON_INSTALL_MIRROR:-auto}"
OFFLINE_TAR=""
CHECK_ONLY=0
UNINSTALL=0
STRIP=1                         # 默认用 stripped 版本，体积更小
RELEASE_TAG="20260310"          # python-build-standalone release tag
SYMLINK=1                       # 是否创建 /usr/local/bin 软链接

# ---------------------------------------------------------------------------
#  国内镜像表
# ---------------------------------------------------------------------------
declare -A MIRRORS=(
  [github]="https://github.com/astral-sh/python-build-standalone/releases/download"
  [nju]="https://mirror.nju.edu.cn/github-release/astral-sh/python-build-standalone"
  [cernet]="https://mirrors.cernet.edu.cn/python-build-standalone"
  [npmmirror]="https://registry.npmmirror.com/-/binary/python-build-standalone"
  [ghproxy]="https://gh-proxy.com/github.com/astral-sh/python-build-standalone/releases/download"
  [ghfast]="https://ghfast.top/github.com/astral-sh/python-build-standalone/releases/download"
)

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

usage() {
  sed -n '/^#  用法:/,/^# ===/{ /^# ===/d; s/^#  \?//; p }' "$0"
  exit 0
}

# ---------------------------------------------------------------------------
#  参数解析
# ---------------------------------------------------------------------------
while [ $# -gt 0 ]; do
  case "$1" in
    --version)     VERSION="$2";      shift 2 ;;
    --prefix)      PREFIX="$2";       shift 2 ;;
    --mirror)      MIRROR="$2";       shift 2 ;;
    --from)        OFFLINE_TAR="$2";  shift 2 ;;
    --tag)         RELEASE_TAG="$2";  shift 2 ;;
    --no-strip)    STRIP=0;           shift   ;;
    --no-symlink)  SYMLINK=0;         shift   ;;
    --check)       CHECK_ONLY=1;      shift   ;;
    --uninstall)   UNINSTALL=1;       shift   ;;
    --help|-h)     usage ;;
    *)             die "未知参数: $1（使用 --help 查看用法）" ;;
  esac
done

# 推导安装前缀
PREFIX="${PREFIX:-/opt/python${VERSION}}"

# ---------------------------------------------------------------------------
#  权限检查
# ---------------------------------------------------------------------------
[ "$(id -u)" -eq 0 ] || die "需要 root 权限。用法: sudo $0"

# ---------------------------------------------------------------------------
#  架构检测
# ---------------------------------------------------------------------------
detect_arch() {
  local machine
  machine=$(uname -m)
  case "$machine" in
    x86_64)           echo "x86_64"  ;;
    aarch64|arm64)    echo "aarch64" ;;
    armv7l|armhf)     echo "armv7"   ;;
    *)                die "不支持的架构: $machine" ;;
  esac
}

ARCH=$(detect_arch)
log INFO "目标架构: $ARCH"

# ---------------------------------------------------------------------------
#  系统信息收集
# ---------------------------------------------------------------------------
detect_glibc_version() {
  local ver
  ver=$(ldd --version 2>&1 | head -1 | grep -oP '[\d.]+$' || true)
  if [ -z "$ver" ]; then
    # musl 系统
    ver=$(ldd --version 2>&1 | grep -oP 'Version \K[\d.]+' || echo "unknown")
  fi
  echo "$ver"
}

GLIBC_VER=$(detect_glibc_version)
log INFO "系统 glibc: $GLIBC_VER"

# glibc >= 2.17 检查
if [ "$GLIBC_VER" != "unknown" ]; then
  if printf '%s\n2.17\n' "$GLIBC_VER" | sort -V | head -1 | grep -qx "2.17"; then
    : # glibc >= 2.17, OK
  else
    die "glibc $GLIBC_VER 低于 python-build-standalone 要求的最低版本 2.17"
  fi
fi

# ---------------------------------------------------------------------------
#  检查已有安装
# ---------------------------------------------------------------------------
check_existing() {
  if [ -x "$PREFIX/bin/python${VERSION}" ]; then
    local installed_ver
    installed_ver=$("$PREFIX/bin/python${VERSION}" --version 2>&1 || true)
    log INFO "已安装: $installed_ver  (位置: $PREFIX)"
    return 0
  fi
  return 1
}

if [ "$CHECK_ONLY" -eq 1 ]; then
  log INFO "========== 环境检查 =========="
  echo "架构:      $ARCH"
  echo "glibc:     $GLIBC_VER"
  echo "目标版本:  Python $VERSION"
  echo "安装路径:  $PREFIX"
  if check_existing; then
    echo "状态:      已安装"
  else
    echo "状态:      未安装"
  fi

  # 也检查一下 PATH 中能找到哪些 Python
  echo ""
  echo "系统中已有的 Python:"
  for cmd in python3 python3.10 python3.11 python3.12; do
    if command -v "$cmd" >/dev/null 2>&1; then
      printf "  %-20s %s\n" "$(command -v "$cmd")" "$("$cmd" --version 2>&1)"
    fi
  done
  exit 0
fi

# ---------------------------------------------------------------------------
#  卸载
# ---------------------------------------------------------------------------
if [ "$UNINSTALL" -eq 1 ]; then
  log INFO "卸载 Python $VERSION (路径: $PREFIX)"
  if [ ! -d "$PREFIX" ]; then
    log WARN "$PREFIX 不存在，无需卸载。"
    exit 0
  fi

  # 删除软链接
  for bin in python${VERSION} pip${VERSION}; do
    local_link="/usr/local/bin/$bin"
    if [ -L "$local_link" ] && readlink "$local_link" | grep -q "$PREFIX"; then
      rm -f "$local_link"
      log INFO "已删除软链接: $local_link"
    fi
  done

  rm -rf "$PREFIX"
  log INFO "已删除: $PREFIX"
  exit 0
fi

# ---------------------------------------------------------------------------
#  如果已安装则跳过
# ---------------------------------------------------------------------------
if check_existing; then
  log INFO "Python $VERSION 已安装，无需重复安装。如需重装，先运行:"
  log INFO "  sudo $0 --uninstall --version $VERSION"
  exit 0
fi

# ---------------------------------------------------------------------------
#  构造下载文件名
# ---------------------------------------------------------------------------
build_filename() {
  # 找到 VERSION 对应的完整版本号，这里用通配下载
  # 文件名格式: cpython-3.11.x+TAG-ARCH-unknown-linux-gnu-install_only_stripped.tar.gz
  local suffix="install_only"
  [ "$STRIP" -eq 1 ] && suffix="install_only_stripped"

  echo "cpython-${VERSION}.*+${RELEASE_TAG}-${ARCH}-unknown-linux-gnu-${suffix}.tar.gz"
}

FILENAME_PATTERN=$(build_filename)
log INFO "目标文件匹配: $FILENAME_PATTERN"

# ---------------------------------------------------------------------------
#  镜像选择与 URL 构造
# ---------------------------------------------------------------------------
resolve_mirror_url() {
  local base_url=""

  if [ "$MIRROR" = "auto" ]; then
    # 自动选择：先试国内镜像，不通则 fallback
    log INFO "自动选择镜像..."
    for name in ghproxy nju npmmirror github; do
      local test_url="${MIRRORS[$name]}"
      log INFO "  测试 $name ($test_url) ..."
      if curl -sI --connect-timeout 5 --max-time 10 "$test_url" >/dev/null 2>&1; then
        log INFO "  $name 可达，使用此镜像。"
        MIRROR="$name"
        break
      fi
      log WARN "  $name 不可达，跳过。"
    done
  fi

  # 如果是预定义镜像名
  if [ -n "${MIRRORS[$MIRROR]+x}" ]; then
    base_url="${MIRRORS[$MIRROR]}"
  elif [[ "$MIRROR" == http* ]]; then
    # 自定义 URL
    base_url="$MIRROR"
  else
    die "未知镜像: $MIRROR（可选: ${!MIRRORS[*]}，或传入完整 URL）"
  fi

  echo "$base_url"
}

# ---------------------------------------------------------------------------
#  下载
# ---------------------------------------------------------------------------
download_python() {
  local base_url="$1"
  local tmpdir
  tmpdir=$(mktemp -d /tmp/install-python.XXXXXX)
  trap "rm -rf '$tmpdir'" EXIT

  # 需要知道精确文件名（包含完整版本号）
  # 由于不同镜像的目录结构略有差异，分镜像处理 URL
  # 通用策略：先尝试直接构造 URL，失败了再尝试列目录

  # 列出已知的 Python 小版本号（3.11 系列）
  local -a known_versions
  case "$VERSION" in
    3.10) known_versions=(3.10.20 3.10.19 3.10.18 3.10.17 3.10.16) ;;
    3.11) known_versions=(3.11.12 3.11.11 3.11.10 3.11.9 3.11.8) ;;
    3.12) known_versions=(3.12.10 3.12.9 3.12.8 3.12.7 3.12.6) ;;
    *)    die "不支持的版本: $VERSION（支持 3.10/3.11/3.12）" ;;
  esac

  local suffix="install_only"
  [ "$STRIP" -eq 1 ] && suffix="install_only_stripped"

  local downloaded=""
  for pyver in "${known_versions[@]}"; do
    local filename="cpython-${pyver}+${RELEASE_TAG}-${ARCH}-unknown-linux-gnu-${suffix}.tar.gz"
    local url="${base_url}/${RELEASE_TAG}/${filename}"

    log INFO "尝试下载: $filename"
    log INFO "  URL: $url"

    if curl -fSL --connect-timeout 15 --max-time 300 --retry 2 \
         -o "$tmpdir/$filename" "$url" 2>&1; then
      downloaded="$tmpdir/$filename"
      log INFO "下载成功: $filename ($(du -h "$downloaded" | awk '{print $1}'))"
      break
    fi

    log WARN "  $pyver 下载失败，尝试下一个版本..."
  done

  if [ -z "$downloaded" ]; then
    die "所有版本均下载失败。请检查网络或使用 --from 参数指定离线包。"
  fi

  echo "$downloaded"
}

# ---------------------------------------------------------------------------
#  安装（从 tar.gz 解压）
# ---------------------------------------------------------------------------
install_from_tar() {
  local tarball="$1"

  # 验证文件
  if ! file "$tarball" | grep -qiE 'gzip|tar'; then
    die "文件格式异常: $tarball（期望 tar.gz）"
  fi

  log INFO "安装到: $PREFIX"
  mkdir -p "$PREFIX"

  # python-build-standalone 的 install_only 包解压出来是 python/ 目录
  # 需要把内容移到 $PREFIX
  local tmpextract
  tmpextract=$(mktemp -d /tmp/pyextract.XXXXXX)

  tar xzf "$tarball" -C "$tmpextract"

  # 内容可能在 python/ 子目录，也可能直接在根
  local src_dir="$tmpextract"
  if [ -d "$tmpextract/python" ]; then
    src_dir="$tmpextract/python"
  elif [ -d "$tmpextract/install" ]; then
    src_dir="$tmpextract/install"
  fi

  # 使用 rsync 或 cp 同步
  if command -v rsync >/dev/null 2>&1; then
    rsync -a "$src_dir/" "$PREFIX/"
  else
    cp -a "$src_dir/." "$PREFIX/"
  fi

  rm -rf "$tmpextract"

  # 验证安装
  local python_bin="$PREFIX/bin/python${VERSION}"
  if [ ! -x "$python_bin" ]; then
    # 有些版本的 bin 下只有 python3，没有 python3.11
    if [ -x "$PREFIX/bin/python3" ]; then
      python_bin="$PREFIX/bin/python3"
    else
      die "安装后未找到可执行文件，请检查 $PREFIX/bin/"
    fi
  fi

  local actual_ver
  actual_ver=$("$python_bin" --version 2>&1)
  log INFO "验证通过: $actual_ver"
}

# ---------------------------------------------------------------------------
#  创建软链接
# ---------------------------------------------------------------------------
create_symlinks() {
  [ "$SYMLINK" -eq 0 ] && return

  local python_bin="$PREFIX/bin/python${VERSION}"
  [ -x "$python_bin" ] || python_bin="$PREFIX/bin/python3"

  local pip_bin="$PREFIX/bin/pip${VERSION}"
  [ -x "$pip_bin" ] || pip_bin="$PREFIX/bin/pip3"

  for pair in "$python_bin:python${VERSION}" "$pip_bin:pip${VERSION}"; do
    local src="${pair%%:*}"
    local name="${pair##*:}"
    local dest="/usr/local/bin/$name"

    if [ -x "$src" ]; then
      ln -sf "$src" "$dest"
      log INFO "软链接: $dest -> $src"
    fi
  done
}

# ---------------------------------------------------------------------------
#  主流程
# ---------------------------------------------------------------------------
main() {
  log INFO "=========================================="
  log INFO "  Python $VERSION 安装脚本"
  log INFO "  架构: $ARCH | glibc: $GLIBC_VER"
  log INFO "  安装路径: $PREFIX"
  log INFO "=========================================="

  local tarball=""

  if [ -n "$OFFLINE_TAR" ]; then
    # ---- 离线模式 ----
    # 支持通配符：--from "vendor/cpython-3.11*aarch64*.tar.gz"
    local resolved
    resolved=$(ls $OFFLINE_TAR 2>/dev/null | head -1 || true)
    [ -f "$resolved" ] || die "离线包不存在: $OFFLINE_TAR"
    tarball="$resolved"
    log INFO "离线安装: $tarball"
  else
    # ---- 在线模式 ----
    local base_url
    base_url=$(resolve_mirror_url)
    tarball=$(download_python "$base_url")
  fi

  install_from_tar "$tarball"
  create_symlinks

  echo ""
  log INFO "========== 安装完成 =========="
  log INFO "Python:  $PREFIX/bin/python${VERSION}"
  log INFO "Pip:     $PREFIX/bin/pip${VERSION}"
  log INFO ""
  log INFO "验证:    $PREFIX/bin/python${VERSION} --version"
  log INFO "创建venv: $PREFIX/bin/python${VERSION} -m venv /path/to/.venv"
  log INFO "卸载:    sudo $0 --uninstall --version $VERSION"
}

main

