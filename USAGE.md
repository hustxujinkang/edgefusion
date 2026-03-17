# EdgeFusion 使用指南

本文档面向开发联调和功能测试，重点说明本地虚拟环境、模拟器、Web 界面和 API 的使用方式。Linux 正式部署请优先使用 `deploy.sh`，详见 [DEPLOYMENT.md](DEPLOYMENT.md)。

## 目录

- [环境准备](#环境准备)
- [快速联调流程](#快速联调流程)
- [Modbus 模拟器使用](#modbus-模拟器使用)
- [Web 界面操作](#web-界面操作)
- [API 接口](#api-接口)
- [常见问题](#常见问题)

## 环境准备

推荐使用项目本地虚拟环境 `.venv`，并使用 Python 3.10、3.11 或 3.12。

### Linux

```bash
./run_local.sh
```

`run_local.sh` 会自动创建 `.venv`、安装 `requirements.txt`，并使用项目目录内的本地配置、日志和数据库路径启动程序。  
如需强制重装依赖，可执行：

```bash
./run_local.sh --reinstall
```

### Windows PowerShell

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 检查依赖

可以运行快速测试向导做基础依赖检查：

```bash
python quick_test.py
```

## 快速联调流程

### 步骤 1：启动 Modbus 充电桩模拟器

根据你要测试的设备型号选择对应的模拟器：

```bash
# 120kW 双枪直流桩（支持功率控制、SOC 监控）
python modbus_charger_simulator.py --model xj_dc_120kw

# 240kW 双枪直流桩
python modbus_charger_simulator.py --model xj_dc_240kw

# 通用充电桩（简单寄存器）
python modbus_charger_simulator.py --model generic
```

模拟器默认监听 `localhost:502`。

**120kW/240kW 型号寄存器说明**

| 区域 | 地址范围 | 描述 |
|------|----------|------|
| 桩信息区 | 0x1000-0x10FF | 充电桩基本信息（枪数、功率等） |
| 枪1数据区 | 0x2000-0x20FF | 枪1状态、电压、电流、SOC 等 |
| 枪2数据区 | 0x2100-0x21FF | 枪2状态、电压、电流、SOC 等 |
| 控制区 | 0x4000-0x400B | 启动/停止/功率控制命令 |
| 控制寄存器 | 0x3000-0x3006 | 内部控制状态存储 |

**通用型号寄存器说明**

| 寄存器地址 | 描述 | 单位 | 说明 |
|------------|------|------|------|
| 0 | 电压 | V | 倍数10 (2200 = 220V) |
| 1 | 电流 | A | 倍数10 |
| 2 | 功率 | W | - |
| 3 | 累计能量 | kWh | 倍数100 |
| 4 | 温度 | °C | 倍数10 |
| 5 | 状态 | - | 0=可用, 1=充电中, 2=故障 |

### 步骤 2：启动 EdgeFusion 主程序

在另一个终端中启动主程序：

```bash
./run_local.sh
```

如果没有激活虚拟环境，也可以直接使用虚拟环境解释器：

```bash
.venv/bin/python -m edgefusion.main
```

```powershell
.\.venv\Scripts\python.exe -m edgefusion.main
```

### 步骤 3：访问 Web 监控界面

打开浏览器访问：

```text
http://localhost:5000
```

界面标签页：

1. **仪表板** - 系统总览
2. **添加设备** - 配置和添加新设备
3. **设备管理** - 管理已连接设备，读写寄存器，控制充电
4. **控制策略** - 查看和执行策略
5. **API 文档** - 完整的 API 接口说明

## Modbus 模拟器使用

### 功能特性

- 真实模拟双枪充电桩状态变化
- 支持功率限制调节（3kW/s 渐进调节）
- 支持 SOC 监控和自动充满停止
- 支持外部控制命令（启动/停止/急停）
- 状态同步和日志输出

### 启动参数

```bash
python modbus_charger_simulator.py [选项]

选项：
  --host      监听地址 (默认: 0.0.0.0)
  --port      监听端口 (默认: 502)
  --unit-id   Modbus 单元 ID (默认: 1)
  --model     设备型号 (默认: generic)
              可选: generic, xj_dc_120kw, xj_dc_240kw
```

示例：

```bash
# 启动 120kW 型号到 5020 端口
python modbus_charger_simulator.py --port 5020 --model xj_dc_120kw
```

### 模拟器行为

1. **空闲状态 (Available)**
   - 电压: ~220V
   - 电流: 0A
   - 功率: 0W
   - SOC: 保持当前值
2. **充电状态 (Charging)**
   - 功率: 渐进增加到设定值（3kW/s）
   - 电流: 随功率变化
   - SOC: 每秒增加 0.5% 直到目标值
   - 充满后自动停止
3. **故障状态 (Fault)**
   - 功率: 0W
   - 电流: 0A

## Web 界面操作

### 添加设备

1. 点击“添加设备”标签页。
2. 填写设备配置：
   - **设备ID**：例如 `charger_001`
   - **设备类型**：选择“充电桩”
   - **协议**：选择“Modbus TCP”
   - **主机地址**：`localhost`
   - **端口**：`502`
   - **单元ID**：`1`
   - **设备型号**：选择对应型号（120kW/240kW/通用）
3. 点击“测试连接”，应显示“连接成功”。
4. 点击“添加设备”。

### 设备管理

1. 点击“设备管理”标签页。
2. 查看已添加的设备列表。
3. 点击设备右侧“操作”按钮。

#### 充电枪数据监控

设备连接后，界面会显示：

- **枪数量** - 该充电桩支持的充电枪数
- **各枪状态** - Available/Charging/Fault
- **实时数据** - 电压、电流、功率、SOC、温度
- **充电进度** - 当前 SOC 和目标 SOC

数据每 5 秒自动刷新。

#### 控制充电

1. **启动充电**
   - 选择枪号（1 或 2）
   - 点击“开始充电”
   - 枪状态变为 `Charging`
   - 功率从零开始渐进增加
2. **停止充电**
   - 点击“停止充电”
   - 枪状态恢复 `Available`
3. **功率限制**
   - 拖动功率限制滑块（0-120kW 或 0-240kW）
   - 或输入具体数值
   - 点击“设置功率”
   - 充电功率平滑过渡到新值
4. **急停**
   - 点击“急停”立即切断充电
   - 枪状态变为 `Fault`

#### 读写寄存器

- 使用“读取寄存器”区域读取任意地址
- 使用“写入寄存器”区域写入数值
- “快速访问表格”显示型号相关的重要寄存器，点击即可读取

寄存器下拉框会根据设备型号自动填充常用地址：

- 120kW/240kW 型号：0x1000、0x2000、0x2100、0x4000 等
- 通用型号：0-5

### 删除设备

在设备列表中点击“删除”按钮，确认后即可删除设备。

## API 接口

### 设备管理 API

| 接口 | 方法 | 描述 |
|------|------|------|
| `/api/devices` | GET | 获取所有设备列表 |
| `/api/devices` | POST | 添加新设备 |
| `/api/devices/<id>` | DELETE | 删除设备 |
| `/api/devices/<id>/connect` | POST | 连接设备 |
| `/api/devices/<id>/disconnect` | POST | 断开设备 |
| `/api/devices/<id>/gun-data` | GET | 获取充电枪数据 |

### 控制 API

| 接口 | 方法 | 描述 |
|------|------|------|
| `/api/devices/<id>/control` | POST | 执行控制命令 |

控制命令格式：

```json
{
  "action": "start_charging",
  "gun_id": 1,
  "params": {
    "power_kw": 60
  }
}
```

支持的 `action`：

- `start_charging` - 启动充电（可选 `power_kw` 参数）
- `stop_charging` - 停止充电
- `set_power` - 设置功率限制（需 `power_kw` 参数）
- `emergency_stop` - 急停

### 寄存器操作 API

| 接口 | 方法 | 描述 |
|------|------|------|
| `/api/devices/<id>/read` | POST | 读取寄存器 |
| `/api/devices/<id>/write` | POST | 写入寄存器 |

读取示例：

```json
{
  "register": "0x2000",
  "count": 10
}
```

## 常见问题

### Q: 提示“连接失败”怎么办？

**A：**

- 确保模拟器正在运行
- 检查主机地址和端口配置是否正确（默认 `localhost:502`）
- 确认选择了正确的设备型号
- 查看模拟器终端是否有错误信息

### Q: 写入寄存器后读出来还是旧值？

**A：** 请确保使用最新版本的模拟器。模拟器支持双向同步：

- 外部写入会同步到内部状态
- 会有 `[同步] 外部写入...` 日志提示
- 模拟器会基于新状态继续运行

### Q: 功率调节为什么是渐进的而不是立即生效？

**A：** 这是模拟真实充电桩的行为。真实充电桩功率不能跳变，需要平滑过渡以保护电池和电网。模拟器实现了 3kW/s 的渐进调节速率。

### Q: 如何模拟双枪同时充电？

**A：**

1. 确保使用的是 120kW 或 240kW 型号
2. 在设备管理页面先启动枪 1 充电
3. 再启动枪 2 充电
4. 两枪独立控制，可设置不同功率限制

### Q: 控制命令发送后没有立即生效？

**A：**

- 控制命令需要写入 `0x4000` 控制区，然后模拟器会同步到内部状态
- 正常情况下延迟不超过 1 秒
- 可在模拟器日志中查看 `[同步]` 提示

### Q: 如何停止程序？

**A：** 在运行程序的终端按 `Ctrl+C` 停止。

### Q: 数据保存在哪里？

**A：**

- 本地联调使用 `./run_local.sh` 或直接运行 `python -m edgefusion.main` 时：
  - 设备数据：`edgefusion.db`
  - 日志文件：`logs/` 目录（按日期分割）
- Linux 生产部署使用 `deploy.sh` 时：
  - 设备数据：`/var/lib/edgefusion/edgefusion.db`
  - 日志文件：`/var/log/edgefusion/`

### Q: Web 界面无法访问？

**A：**

- 确认主程序已成功启动
- 检查端口 `5000` 是否被占用
- 尝试使用 `http://127.0.0.1:5000` 代替 `localhost`

### Q: 如何查看 API 文档？

**A：** 在 Web 界面中点击“API 文档”标签页，或者直接访问各个 API 端点。
