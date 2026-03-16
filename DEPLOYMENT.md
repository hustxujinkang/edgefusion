# EdgeFusion Linux 部署说明

本文档用于正式部署到 Linux 工控机核心板环境。安装目录和运行用户由你在部署时自行指定。

## 1. 准备环境

- Python 3.10、3.11 或 3.12
- `python3-venv` / `python3.10-venv`
- `systemd`

如果尚未安装 Python 虚拟环境组件，请先安装对应系统包。

## 2. 部署项目

先约定两个变量：

```bash
export EDGEFUSION_DIR=/path/to/edgefusion
export EDGEFUSION_USER=edgefusion
```

将项目部署到目标目录，例如：

```bash
sudo mkdir -p "$EDGEFUSION_DIR"
sudo chown -R "$EDGEFUSION_USER:$EDGEFUSION_USER" "$EDGEFUSION_DIR"
git clone <your-repo-url> "$EDGEFUSION_DIR"
cd "$EDGEFUSION_DIR"
```

如果是已有项目目录，执行 `git pull` 更新即可。

## 3. 首次安装

为脚本增加执行权限并初始化运行环境：

```bash
chmod +x install.sh run.sh
./install.sh
```

`install.sh` 会执行以下操作：

- 创建 `.venv`
- 安装 `requirements.txt`
- 创建 `logs/`
- 检查 `config.yaml`

## 4. 配置 systemd

项目内提供了示例服务文件 [edgefusion.service](./edgefusion.service)。

`edgefusion.service` 是模板文件，里面包含两个占位符：

- `__EDGEFUSION_USER__`
- `__EDGEFUSION_PROJECT_DIR__`

安装服务前，先替换占位符再写入 systemd：

```bash
sed \
  -e "s|__EDGEFUSION_USER__|$EDGEFUSION_USER|g" \
  -e "s|__EDGEFUSION_PROJECT_DIR__|$EDGEFUSION_DIR|g" \
  edgefusion.service | sudo tee /etc/systemd/system/edgefusion.service >/dev/null

sudo systemctl daemon-reload
sudo systemctl enable --now edgefusion
```

## 5. 常用运维命令

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

## 6. 日志与数据位置

- 应用日志目录：`logs/`
- SQLite 数据库：`edgefusion.db`
- systemd 日志：`journalctl -u edgefusion`

由于当前配置和日志都使用相对路径，`systemd` 必须固定 `WorkingDirectory` 到项目根目录。

## 7. 升级流程

```bash
cd "$EDGEFUSION_DIR"
git pull
./install.sh
sudo systemctl restart edgefusion
```

## 8. Windows 开发联调

Windows 环境请使用仓库根目录下的 `start.bat`。它会在首次运行时自动创建 `.venv` 并安装依赖，后续启动只负责运行程序。
