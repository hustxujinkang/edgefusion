# Modbus/TCP 充电桩模拟器使用指南

## 📋 概述

本项目提供了一个完整的Modbus/TCP充电桩模拟器，可以在PC上模拟真实的充电桩设备，用于调试和测试后台系统。

## 🚀 快速开始

### 1. 启动Modbus充电桩模拟器

在一个终端中运行：

```bash
conda activate edgefusion-env
python modbus_charger_simulator.py
```

默认配置：
- 监听地址：`0.0.0.0:502`
- 单元ID：`1`

可选参数：
```bash
python modbus_charger_simulator.py --host 127.0.0.1 --port 502 --unit-id 1
```

### 2. 启动后台系统

在另一个终端中运行：

```bash
conda activate edgefusion-env
python -m edgefusion.main
```

访问监控面板：http://localhost:5000

---

## 📊 Modbus寄存器映射

### 保持寄存器 (4x区域)

| 地址 | 描述 | 单位/说明 | 读/写 |
|------|------|-----------|-------|
| 0 | 电压 | V (x10) | 读 |
| 1 | 电流 | A (x10) | 读 |
| 2 | 功率 | W | 读 |
| 3 | 累计充电量 | kWh (x100) | 读 |
| 4 | 温度 | °C (x10) | 读 |
| 5 | 状态码 | 0=可用, 1=充电中, 2=故障 | 读 |
| 6 | 充电会话时间 | 秒 | 读 |
| 10 | 设备类型 | 1=充电桩 | 读 |
| 11 | 额定功率 | kW | 读 |

### 状态码说明
- `0`: Available (空闲可用)
- `1`: Charging (充电中)
- `2`: Fault (故障)

---

## 🔧 测试Modbus连接

### 使用pymodbus客户端测试

创建一个简单的测试脚本：

```python
from pymodbus.client import ModbusTcpClient

# 连接到模拟器
client = ModbusTcpClient('localhost', port=502)
client.connect()

# 读取保持寄存器（地址0-10）
result = client.read_holding_registers(0, 12, slave=1)

if not result.isError():
    print("寄存器值:", result.registers)
    
    voltage = result.registers[0] / 10
    current = result.registers[1] / 10
    power = result.registers[2]
    energy = result.registers[3] / 100
    temp = result.registers[4] / 10
    status = result.registers[5]
    
    print(f"电压: {voltage}V")
    print(f"电流: {current}A")
    print(f"功率: {power}W")
    print(f"能量: {energy}kWh")
    print(f"温度: {temp}°C")
    print(f"状态: {['可用', '充电中', '故障'][status]}")

client.close()
```

---

## 📝 项目架构

### 当前已完成

✅ **Modbus/TCP充电桩模拟器** (`modbus_charger_simulator.py`)
- 完整的Modbus TCP服务器实现
- 真实的充电桩状态模拟
- 支持电压、电流、功率、温度等参数
- 状态机：可用 → 充电中 → 故障
- 实时数据更新（每秒刷新）

✅ **后台系统Modbus客户端** (`edgefusion/protocol/modbus.py`)
- 已实现Modbus TCP连接
- 支持读写保持寄存器
- 支持设备发现

### 待完善功能

🔄 **设备接入引导页面**
- Web表单配置Modbus设备参数
- 设备类型选择
- 连接测试功能

🔄 **设备管理页面增强**
- 设备列表展示
- 实时数据读取
- 寄存器读写操作界面
- 设备状态监控

---

## 🎯 使用示例

### 场景1：基本测试流程

1. **终端1 - 启动模拟器**
```bash
python modbus_charger_simulator.py
```

2. **终端2 - 启动后台**
```bash
python -m edgefusion.main
```

3. **浏览器访问** http://localhost:5000

### 场景2：使用现有Modbus协议类

```python
from edgefusion.protocol import ModbusProtocol

# 创建Modbus协议实例
config = {
    'host': 'localhost',
    'port': 502,
    'timeout': 5
}

modbus = ModbusProtocol(config)

# 连接设备
if modbus.connect():
    print("连接成功！")
    
    # 读取电压（地址0）
    voltage_raw = modbus.read_data('1', '0')
    voltage = voltage_raw / 10
    print(f"电压: {voltage}V")
    
    # 读取功率（地址2）
    power = modbus.read_data('1', '2')
    print(f"功率: {power}W")
    
    modbus.disconnect()
```

---

## 🔍 调试技巧

### 查看模拟器日志

模拟器启动后会输出：
```
============================================================
Modbus/TCP 充电桩模拟器
============================================================
监听地址: 0.0.0.0:502
单元ID: 1
============================================================
模拟器已启动！按 Ctrl+C 停止
当前状态: Available
------------------------------------------------------------
```

### 常见问题

**Q: 连接被拒绝？**
- 检查模拟器是否已启动
- 确认端口502没有被占用
- Windows上可能需要管理员权限

**Q: 读取不到数据？**
- 确认单元ID（slave ID）正确
- 检查寄存器地址是否正确
- 查看模拟器日志是否有连接记录

**Q: 如何改变充电桩状态？**
- 目前通过修改模拟器代码实现
- 后续可以通过Modbus写入特定寄存器控制

---

## 📚 参考资料

- [pymodbus文档](https://pymodbus.readthedocs.io/)
- [Modbus协议规范](http://www.modbus.org/specs.php)
