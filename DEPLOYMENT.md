# EdgeFusion Linux 部署说明

本文档用于正式部署到 Linux 工控机核心板环境。推荐使用 `deploy.sh` 完成首次部署和后续升级。

## 1. 准备环境

- Python 3.10、3.11 或 3.12
- `python3-venv` / `python3.10-venv`
- `systemd`

如果尚未安装 Python 虚拟环境组件，请先安装对应系统包。

## 2. 源码目录与部署目录

源码仓库可以放在任意工作目录，例如：

```bash
git clone <your-repo-url> ~/src/edgefusion
cd ~/src/edgefusion
```

默认部署目录遵循 Linux 常见约定：

- 程序目录：`/opt/edgefusion`
- 配置目录：`/etc/edgefusion`
- 数据目录：`/var/lib/edgefusion`
- 日志目录：`/var/log/edgefusion`
- 服务文件：`/etc/systemd/system/edgefusion.service`

也就是说，源码目录和部署目录不是同一个位置。

## 3. 一键部署

首次部署推荐直接执行：

```bash
chmod +x deploy.sh run_local.sh backup.sh restore.sh
sudo ./deploy.sh
```

如果你希望指定运行用户、服务名或目录：

```bash
sudo \
  EDGEFUSION_USER=edgefusion \
  EDGEFUSION_SERVICE_NAME=edgefusion \
  EDGEFUSION_APP_DIR=/opt/edgefusion \
  EDGEFUSION_CONFIG_DIR=/etc/edgefusion \
  EDGEFUSION_DATA_DIR=/var/lib/edgefusion \
  EDGEFUSION_LOG_DIR=/var/log/edgefusion \
  ./deploy.sh
```

`deploy.sh` 会自动完成以下动作：

- 在未预设 `EDGEFUSION_*` 时交互式提示服务名、用户和目录
- 将当前源码同步到部署目录
- 创建/复用 `.venv`
- 安装生产依赖 `requirements-prod.txt`
- 首次部署时复制默认 `config.yaml`
- 通过环境变量将配置、数据库和日志固定到标准目录
- 生成 `systemd` 服务文件
- `daemon-reload`
- 首次启动服务，或在升级时重启服务

部署完成后可直接查看：

```bash
systemctl status edgefusion
journalctl -u edgefusion -f
```

## 4. 升级流程

升级时，不需要进入部署目录，只需要在新的源码目录执行：

```bash
cd ~/src/edgefusion
git pull
sudo ./deploy.sh
```

再次执行 `deploy.sh` 会进入升级逻辑：

- 保留 `/etc/edgefusion/config.yaml`
- 保留 `/var/lib/edgefusion/edgefusion.db`
- 保留 `/var/log/edgefusion/`
- 同步新的程序文件到 `/opt/edgefusion`
- 重新安装生产依赖
- 重启 `edgefusion` 服务

## 5. 自定义部署参数

`deploy.sh` 是 Linux 正式部署的唯一入口。默认情况下，如果没有预先设置环境变量，它会像 `ssh-keygen` 一样逐项提示，直接回车即可采用默认值：

```bash
Service name [edgefusion]:
Run as user [edgefusion]:
App dir [/opt/edgefusion]:
Config dir [/etc/edgefusion]:
Data dir [/var/lib/edgefusion]:
Log dir [/var/log/edgefusion]:
```

如果要完全跳过交互，适合自动化或批量部署，可显式传入变量并设置 `EDGEFUSION_NONINTERACTIVE=1`：

```bash
sudo \
  EDGEFUSION_NONINTERACTIVE=1 \
  EDGEFUSION_USER=edgefusion \
  EDGEFUSION_SERVICE_NAME=edgefusion \
  EDGEFUSION_APP_DIR=/opt/edgefusion \
  EDGEFUSION_CONFIG_DIR=/etc/edgefusion \
  EDGEFUSION_DATA_DIR=/var/lib/edgefusion \
  EDGEFUSION_LOG_DIR=/var/log/edgefusion \
  ./deploy.sh
```

正式部署时仍然固定采用以下标准目录语义：

- 配置文件：`/etc/edgefusion/config.yaml`
- 数据库：`/var/lib/edgefusion/edgefusion.db`
- 日志目录：`/var/log/edgefusion/`

如果只是本地联调，请使用：

```bash
./run_local.sh
```

## 6. 手动配置 systemd

项目内提供了示例服务模板 [edgefusion.service.template](./edgefusion.service.template)。

`edgefusion.service.template` 是模板文件，里面包含以下占位符：

- `__EDGEFUSION_SERVICE_NAME__`
- `__EDGEFUSION_USER__`
- `__EDGEFUSION_PROJECT_DIR__`
- `__EDGEFUSION_CONFIG_DIR__`
- `__EDGEFUSION_DATA_DIR__`
- `__EDGEFUSION_LOG_DIR__`
- `__EDGEFUSION_CONFIG_FILE__`
- `__EDGEFUSION_DB_PATH__`
- `__EDGEFUSION_DB_URL__`

如果不用 `deploy.sh` 自动生成服务，也可以手工替换占位符再写入 systemd：

```bash
export EDGEFUSION_SERVICE_NAME=edgefusion
export EDGEFUSION_DIR=/opt/edgefusion
export EDGEFUSION_USER=edgefusion
export EDGEFUSION_CONFIG_DIR=/etc/edgefusion
export EDGEFUSION_DATA_DIR=/var/lib/edgefusion
export EDGEFUSION_LOG_DIR=/var/log/edgefusion
export EDGEFUSION_CONFIG_FILE="$EDGEFUSION_CONFIG_DIR/config.yaml"
export EDGEFUSION_DB_PATH="$EDGEFUSION_DATA_DIR/edgefusion.db"
export EDGEFUSION_DB_URL="sqlite:///$EDGEFUSION_DB_PATH"

sed \
  -e "s|__EDGEFUSION_SERVICE_NAME__|$EDGEFUSION_SERVICE_NAME|g" \
  -e "s|__EDGEFUSION_USER__|$EDGEFUSION_USER|g" \
  -e "s|__EDGEFUSION_PROJECT_DIR__|$EDGEFUSION_DIR|g" \
  -e "s|__EDGEFUSION_CONFIG_DIR__|$EDGEFUSION_CONFIG_DIR|g" \
  -e "s|__EDGEFUSION_DATA_DIR__|$EDGEFUSION_DATA_DIR|g" \
  -e "s|__EDGEFUSION_LOG_DIR__|$EDGEFUSION_LOG_DIR|g" \
  -e "s|__EDGEFUSION_CONFIG_FILE__|$EDGEFUSION_CONFIG_FILE|g" \
  -e "s|__EDGEFUSION_DB_PATH__|$EDGEFUSION_DB_PATH|g" \
  -e "s|__EDGEFUSION_DB_URL__|$EDGEFUSION_DB_URL|g" \
  edgefusion.service.template | sudo tee /etc/systemd/system/edgefusion.service >/dev/null

sudo systemctl daemon-reload
sudo systemctl enable --now edgefusion
```

## 7. 常用运维命令

查看服务状态：

```bash
sudo systemctl status edgefusion
```

实时查看 systemd 日志：

```bash
sudo journalctl -u edgefusion -f
```

重启服务：

```bash
sudo systemctl restart edgefusion
```

停止服务：

```bash
sudo systemctl stop edgefusion
```

## 8. 日志与数据位置

- 应用日志目录：`/var/log/edgefusion`
- SQLite 数据库：`/var/lib/edgefusion/edgefusion.db`
- 部署程序目录：`/opt/edgefusion`
- 配置文件：`/etc/edgefusion/config.yaml`
- systemd 日志：`journalctl -u edgefusion`

应用现在直接读取这些标准目录，不再依赖程序目录内的符号链接。

## 9. 备份与恢复

生产环境常规备份只需要配置文件和 SQLite 数据库：

```bash
sudo ./backup.sh
```

默认会生成到 `/var/backups/edgefusion/<timestamp>/`。也可以指定备份根目录：

```bash
sudo ./backup.sh /srv/backups/edgefusion
```

恢复时使用：

```bash
sudo ./restore.sh /var/backups/edgefusion/20260317-103000
```

`backup.sh` 在服务运行时会先停服务、复制配置和数据库、再恢复服务。`restore.sh` 会停止服务、恢复配置和数据库，并在检测到 `systemd` 服务时重新启动服务。

## 10. 仅重新部署当前版本

如果你只是想重新安装依赖并重启服务，仍然推荐在当前源码目录直接再次执行：

```bash
sudo ./deploy.sh
```

它会保留配置、数据库和日志，只更新程序文件、依赖和 service。

## 11. Windows 开发联调

Windows 环境请使用仓库根目录下的 `start.bat`。它会在首次运行时自动创建 `.venv` 并安装依赖，后续启动只负责运行程序。
