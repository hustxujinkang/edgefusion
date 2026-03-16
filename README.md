# EdgeFusion - 台区智能融合终端后台系统

基于 Python 的台区智能融合终端后台程序，用于对台区内的光伏、储能、充电桩等设备进行协同控制和监控。

项目定位如下：

- Linux 是正式部署环境，推荐通过 `install.sh + run.sh + systemd` 管理
- Windows 的 `start.bat` 仅用于开发和联调阶段的一键启动

## 功能特性

- **设备管理**：支持光伏、储能、充电桩等设备接入（Modbus TCP/RTU、MQTT、OCPP）
- **型号配置**：支持不同型号充电桩的点表配置（120kW/240kW直流桩、通用桩）
- **设备模拟器**：内置 Modbus 充电桩模拟器，支持双枪充电、功率限制等高级功能
- **Web监控面板**：实时监测设备状态和充电枪数据，提供可视化界面
- **设备控制**：支持启动/停止充电、功率限制调节、急停等远程控制
- **控制策略**：支持削峰填谷、需求响应、自发自用等策略
- **数据采集**：定期采集设备数据并存储到 SQLite 数据库

## 快速开始

### Linux 正式部署

```bash
chmod +x install.sh run.sh
./install.sh
./run.sh
```

推荐进一步使用 `systemd` 托管服务，详见 [DEPLOYMENT.md](DEPLOYMENT.md)。

### Windows 开发联调

首次运行直接执行：

```bat
start.bat
```

`start.bat` 会自动执行以下动作：

- 检测并创建 `.venv`
- 安装 `requirements.txt`
- 启动 `python -m edgefusion.main`

如需强制重装依赖，可执行：

```bat
start.bat --reinstall
```

### 手动启动主程序

如果你希望手动使用虚拟环境，建议使用 Python 3.10、3.11 或 3.12：

```bash
# Linux
python3.10 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python -m edgefusion.main
```

```powershell
# Windows PowerShell
py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m edgefusion.main
```

### 访问 Web 界面

启动成功后，打开浏览器访问：**http://localhost:5000**

## 联调说明

联调时可先启动 Modbus 模拟器：

```bash
# 启动 120kW 双枪直流桩模拟器
python modbus_charger_simulator.py --model xj_dc_120kw

# 或启动 240kW 型号
python modbus_charger_simulator.py --model xj_dc_240kw

# 或启动通用充电桩
python modbus_charger_simulator.py --model generic
```

也可以运行：

```bash
python quick_test.py
```

该脚本用于联调辅助和依赖检查，不是正式部署入口。

## 文档

- [DEPLOYMENT.md](DEPLOYMENT.md) - Linux 部署与 `systemd` 运维说明
- [USAGE.md](USAGE.md) - 联调、模拟器、Web 界面和 API 使用说明
- [ARCHITECTURE.md](ARCHITECTURE.md) - 系统架构和技术选型说明

## 项目结构

```text
edgefusion/
├── edgefusion/
│   ├── main.py
│   ├── config.py
│   ├── device_manager.py
│   ├── point_tables.py
│   ├── protocol/
│   ├── strategy/
│   ├── monitor/
│   └── simulator/
├── config.yaml
├── requirements.txt
├── start.bat
├── install.sh
├── run.sh
├── edgefusion.service
└── DEPLOYMENT.md
```

## 支持的设备型号

| 型号 | 协议 | 最大功率 | 枪数 | 特点 |
|------|------|----------|------|------|
| 120kW 直流桩 | Modbus TCP | 120kW | 2 | 支持功率限制、SOC 监控 |
| 240kW 直流桩 | Modbus TCP | 240kW | 2 | 支持功率限制、SOC 监控 |
| 通用充电桩 | Modbus TCP/RTU | - | 1 | 简单寄存器映射 |

## 版本信息

- **版本**：0.3.0
- **更新日期**：2026-02-26

## 许可证

本项目仅供学习和研究使用。
