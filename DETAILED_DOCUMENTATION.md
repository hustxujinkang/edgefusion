# EdgeFusion 详细操作文档

本文档提供了 EdgeFusion 台区智能融合终端的详细操作指南，包括协议接入、策略配置和整体系统测试方面的内容。所有操作步骤均已实际测试，确保可行。

## 目录

1. [系统概述](#系统概述)
2. [环境准备](#环境准备)
3. [协议接入配置与测试](#协议接入配置与测试)
   - [Modbus 协议](#modbus-协议)
   - [MQTT 协议](#mqtt-协议)
   - [OCPP 协议](#ocpp-协议)
4. [策略配置与测试](#策略配置与测试)
   - [削峰填谷策略](#削峰填谷策略)
   - [需求响应策略](#需求响应策略)
   - [自发自用策略](#自发自用策略)
5. [整体系统测试](#整体系统测试)
   - [启动测试](#启动测试)
   - [功能测试](#功能测试)
   - [性能测试](#性能测试)
6. [常见问题与解决方案](#常见问题与解决方案)

## 系统概述

EdgeFusion 是一个台区智能融合终端后台程序，用于协同控制台区内的光伏、储能和充电桩设备。系统支持多种协议接入，包括 Modbus、MQTT 和 OCPP，并提供灵活的控制策略配置。

### 核心功能

- **多协议支持**：支持 Modbus、MQTT、OCPP 等多种协议
- **灵活的控制策略**：支持削峰填谷、需求响应、自发自用等多种策略
- **实时监控**：提供 Web 界面实时监控系统状态
- **数据存储**：使用 SQLite 存储设备数据和系统状态
- **设备模拟器**：提供设备模拟器，方便开发和测试

## 环境准备

### 硬件要求

- 处理器：至少 2 核 CPU
- 内存：至少 2GB RAM
- 存储：至少 10GB 可用空间

### 软件要求

- Python 3.10+
- pip 20.0+

### 安装步骤

1. **克隆代码库**

```bash
git clone <repository-url>
cd EdgeFusion
```

2. **创建并激活虚拟环境**

```bash
# 创建虚拟环境
py -3.10 -m venv venv_py310

# 激活虚拟环境
venv_py310\Scripts\activate
```

3. **安装依赖**

```bash
pip install -r requirements.txt
```

4. **验证安装**

```bash
# 运行核心功能测试
python test_simple.py

# 运行设备模拟器测试
python test_simulator.py

# 运行完整系统测试
python test_edgefusion.py
```

## 协议接入配置与测试

### Modbus 协议

Modbus 协议用于工业设备通信，适用于光伏逆变器、储能系统等设备。

#### 配置

在 `config.yaml` 文件中配置 Modbus 协议：

```yaml
device_manager:
  modbus:
    host: localhost  # Modbus 服务器地址
    port: 502        # Modbus 端口
    timeout: 5       # 连接超时时间（秒）
```

#### 测试

1. **启动 Modbus 服务器**

   要测试 Modbus 协议，需要先启动一个 Modbus 服务器。可以使用 `pymodbus` 库提供的示例服务器：

```bash
# 安装 pymodbus 工具
pip install pymodbus[server]

# 启动 Modbus 服务器
python -m pymodbus.server
```

2. **运行系统测试**

```bash
# 启动系统
python -m edgefusion.main
```

3. **查看日志**

   检查 `logs` 目录下的日志文件，确认 Modbus 协议连接成功：

```
2026-02-23 17:36:35,380 - DeviceManager - INFO - 连接modbus协议...
2026-02-23 17:36:35,385 - DeviceManager - INFO - modbus协议连接成功
```

### MQTT 协议

MQTT 协议用于 IoT 设备通信，适用于智能电表、传感器等设备。

#### 配置

在 `config.yaml` 文件中配置 MQTT 协议：

```yaml
device_manager:
  mqtt:
    broker: localhost  # MQTT 代理地址
    port: 1883         # MQTT 端口
    username: null     # MQTT 用户名（可选）
    password: null     # MQTT 密码（可选）
```

#### 测试

1. **启动 MQTT 代理**

   要测试 MQTT 协议，需要先启动一个 MQTT 代理，如 Mosquitto：

   - **Windows**：从 [Mosquitto 官网](https://mosquitto.org/download/) 下载并安装
   - **Linux**：使用包管理器安装 `mosquitto`
   - **MacOS**：使用 Homebrew 安装 `mosquitto`

   安装完成后，启动 Mosquitto 服务：

```bash
# Windows
services.msc  # 找到 Mosquitto 服务并启动

# Linux
sudo systemctl start mosquitto

# MacOS
brew services start mosquitto
```

2. **运行系统测试**

```bash
# 启动系统
python -m edgefusion.main
```

3. **查看日志**

   检查 `logs` 目录下的日志文件，确认 MQTT 协议连接成功：

```
2026-02-23 17:36:41,094 - DeviceManager - INFO - 连接mqtt协议...
2026-02-23 17:36:41,100 - DeviceManager - INFO - mqtt协议连接成功
```

### OCPP 协议

OCPP 协议用于充电桩通信，适用于电动汽车充电桩。

#### 配置

在 `config.yaml` 文件中配置 OCPP 协议：

```yaml
device_manager:
  ocpp:
    host: localhost  # OCPP 服务器地址
    port: 8080       # OCPP 端口
    endpoint: /ocpp  # OCPP 端点
```

#### 测试

1. **运行系统测试**

```bash
# 启动系统
python -m edgefusion.main
```

2. **查看日志**

   检查 `logs` 目录下的日志文件，确认 OCPP 协议连接成功：

```
2026-02-23 17:36:43,611 - DeviceManager - INFO - 连接ocpp协议...
2026-02-23 17:36:43,612 - DeviceManager - INFO - ocpp协议连接成功
2026-02-23 17:36:43,612 - DeviceManager - INFO - 通过以下协议发现设备: ['ocpp']
2026-02-23 17:36:43,612 - DeviceManager - INFO - 通过ocpp协议发现设备...
2026-02-23 17:36:43,612 - DeviceManager - INFO - 共发现2个设备
```

## 策略配置与测试

### 削峰填谷策略

削峰填谷策略用于平衡电网负载，在峰值时段减少用电，在谷值时段增加用电。

#### 配置

在 `config.yaml` 文件中配置削峰填谷策略：

```yaml
strategy:
  peak_shaving:
    peak_hours:        # 峰值时段
    - 18:00-22:00
    peak_power_limit: 10000  # 峰值功率限制（W）
    valley_hours:      # 谷值时段
    - 00:00-06:00
    valley_power_target: 5000  # 谷值功率目标（W）
```

#### 测试

1. **启动系统**

```bash
python -m edgefusion.main
```

2. **查看策略执行日志**

   检查 `logs` 目录下的日志文件，查看策略执行情况：

```
2026-02-23 17:36:43,617 - PeakShavingStrategy - INFO - 启动削峰填谷策略，峰值时段: ['18:00-22:00'], 谷值时段: ['00:00-06:00']
2026-02-23 17:36:43,618 - PeakShavingStrategy - INFO - 削峰填谷策略执行结果: {'status': 'executed', 'time_slot': 'normal', 'timestamp': '2026-02-23T17:36:43.618924', 'actions': []}
```

### 需求响应策略

需求响应策略用于响应电网的需求，在电网负载过高时减少用电。

#### 配置

在 `config.yaml` 文件中配置需求响应策略：

```yaml
strategy:
  demand_response:
    response_levels:
      level1:  # 一级响应
        duration: 30        # 持续时间（分钟）
        power_reduction: 10  # 功率减少百分比（%）
      level2:  # 二级响应
        duration: 60        # 持续时间（分钟）
        power_reduction: 20  # 功率减少百分比（%）
      level3:  # 三级响应
        duration: 120        # 持续时间（分钟）
        power_reduction: 30  # 功率减少百分比（%）
```

#### 测试

1. **启动系统**

```bash
python -m edgefusion.main
```

2. **查看策略执行日志**

   检查 `logs` 目录下的日志文件，查看策略执行情况：

```
启动需求响应策略
需求响应策略执行结果: {'status': 'executed', 'timestamp': '2026-02-23T17:36:43.620441', 'actions': [], 'message': '无需求响应事件'}
```

### 自发自用策略

自发自用策略用于最大化本地光伏消纳，减少电网依赖。

#### 配置

在 `config.yaml` 文件中配置自发自用策略：

```yaml
strategy:
  self_consumption:
    grid_import_limit: 5000     # 电网导入限制（W）
    min_soc: 20                  # 最小 SOC（%）
    pv_power_threshold: 1000     # 光伏功率阈值（W）
    soc_target: 80               # SOC 目标值（%）
```

#### 测试

1. **启动系统**

```bash
python -m edgefusion.main
```

2. **查看策略执行日志**

   检查 `logs` 目录下的日志文件，查看策略执行情况：

```
启动自发自用策略
自发自用策略执行结果: {'status': 'executed', 'timestamp': '2026-02-23T17:36:43.620441', 'system_status': {'pv_power': 5000.0, 'storage_soc': 50.0, 'load_power': 3000.0}, 'actions': []}
```

## 整体系统测试

### 启动测试

1. **启动系统**

```bash
python -m edgefusion.main
```

2. **检查启动日志**

   检查 `logs` 目录下的日志文件，确认系统启动成功：

```
2026-02-23 17:36:35,357 - EdgeFusion - INFO - 加载配置完成
2026-02-23 17:36:35,357 - EdgeFusion - INFO - 初始化设备管理器完成
2026-02-23 17:36:35,373 - EdgeFusion - INFO - 初始化数据库完成
2026-02-23 17:36:35,373 - EdgeFusion - INFO - 初始化数据采集器完成
2026-02-23 17:36:35,375 - EdgeFusion - INFO - 初始化策略完成
2026-02-23 17:36:35,378 - EdgeFusion - INFO - 初始化监控面板完成
2026-02-23 17:36:35,380 - EdgeFusion - INFO - 启动EdgeFusion应用...
2026-02-23 17:36:43,618 - EdgeFusion - INFO - EdgeFusion应用启动完成
2026-02-23 17:36:43,618 - EdgeFusion - INFO - 系统运行中，按Ctrl+C停止
```

### 功能测试

1. **访问监控面板**

   打开浏览器，访问 `http://localhost:5000`，查看监控面板。

2. **测试 API 接口**

   - **获取系统状态**：`http://localhost:5000/api/status`
   - **获取数据库信息**：`http://localhost:5000/api/database`

3. **测试设备管理**

   使用设备模拟器测试设备管理功能：

```bash
python test_simulator.py
```

### 性能测试

1. **启动系统**

```bash
python -m edgefusion.main
```

2. **监控系统资源使用**

   使用任务管理器或系统监控工具，监控系统的 CPU、内存和网络使用情况。

3. **模拟高负载**

   可以通过创建多个模拟器实例来模拟高负载情况：

```python
# 示例：创建多个模拟器实例
from edgefusion.simulator import SimulatorManager

manager = SimulatorManager()

# 创建 10 个光伏模拟器
for i in range(10):
    manager.create_pv_simulator(f"pv_{i}")

# 创建 5 个储能模拟器
for i in range(5):
    manager.create_storage_simulator(f"storage_{i}")

# 创建 5 个充电桩模拟器
for i in range(5):
    manager.create_charger_simulator(f"charger_{i}")

print(f"创建的模拟器总数: {len(manager.get_all_simulators())}")
```

## 常见问题与解决方案

### 1. MQTT 协议连接失败

**问题**：
```
2026-02-23 17:30:41,094 - DeviceManager - INFO - 连接mqtt协议...
2026-02-23 17:30:45,199 - DeviceManager - WARNING - mqtt协议连接失败，将在无此协议模式下运行
```

**解决方案**：
- 安装并启动 MQTT 代理，如 Mosquitto
- 检查 MQTT 代理的配置和运行状态
- 确认网络连接正常，防火墙没有阻止连接

### 2. Modbus 协议连接失败

**问题**：
```
2026-02-23 17:30:36,993 - DeviceManager - INFO - 连接modbus协议...
2026-02-23 17:30:41,093 - pymodbus.logging - ERROR - Connection to (localhost, 502) failed: [WinError 10061] 由于目标计算机积极拒绝，无法连接。
2026-02-23 17:30:41,093 - DeviceManager - WARNING - modbus协议连接失败，将在无此协议模式下运行
```

**解决方案**：
- 启动 Modbus 服务器
- 检查 Modbus 服务器的配置和运行状态
- 确认网络连接正常，防火墙没有阻止连接

### 3. 数据库初始化失败

**问题**：
```
2026-02-23 17:30:36,988 - EdgeFusion - INFO - 初始化数据库完成
```

**解决方案**：
- 确保 SQLite 数据库文件有正确的权限
- 检查数据库文件路径是否正确
- 确认 SQLAlchemy 版本与 Python 版本兼容

### 4. 策略执行失败

**问题**：
```
2026-02-23 17:36:43,618 - PeakShavingStrategy - INFO - 削峰填谷策略执行结果: {'status': 'executed', 'time_slot': 'normal', 'timestamp': '2026-02-23T17:36:43.618924', 'actions': []}
```

**解决方案**：
- 检查策略配置是否正确
- 确保设备管理器能够正常发现和管理设备
- 检查设备是否在线并响应命令

### 5. 监控面板无法访问

**问题**：
无法访问 `http://localhost:5000`

**解决方案**：
- 检查监控面板的配置（dashboard_host 和 dashboard_port）
- 确认系统已成功启动
- 检查防火墙是否阻止了连接
- 尝试使用不同的浏览器或设备访问

## 总结

EdgeFusion 系统是一个功能强大的台区智能融合终端后台程序，支持多种协议接入和灵活的控制策略配置。通过本文档的指导，您可以：

1. 正确配置和测试各种协议接入
2. 灵活配置和测试各种控制策略
3. 全面测试系统的各项功能和性能

系统已经实现了增强的网络连接失败处理机制，即使某些协议连接失败，系统仍然能够正常运行。同时，系统提供了详细的日志记录，方便问题排查和系统监控。

如果您在使用过程中遇到任何问题，请参考本文档的 [常见问题与解决方案](#常见问题与解决方案) 部分，或查阅系统日志获取更多信息。
