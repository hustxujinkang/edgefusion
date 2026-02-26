# EdgeFusion - 台区智能融合终端后台系统

基于 Python 的台区智能融合终端后台程序，用于对台区内的光伏、储能、充电桩等设备进行协同控制和监控。

## 功能特性

- **设备管理**：支持光伏、储能、充电桩等设备接入（Modbus TCP/RTU、MQTT、OCPP）
- **型号配置**：支持不同型号充电桩的点表配置（120kW/240kW直流桩、通用桩）
- **设备模拟器**：内置Modbus充电桩模拟器，支持双枪充电、功率限制等高级功能
- **Web监控面板**：实时监测设备状态和充电枪数据，提供可视化界面
- **设备控制**：支持启动/停止充电、功率限制调节、急停等远程控制
- **控制策略**：支持削峰填谷、需求响应、自发自用等策略
- **数据采集**：定期采集设备数据并存储到SQLite数据库

## 快速开始

### 1. 环境准备

```bash
# 创建并激活Python 3.10虚拟环境
conda create -n edgefusion-env python=3.10 -y
conda activate edgefusion-env

# 安装依赖
pip install -r requirements.txt
```

### 2. 启动系统

**方式一：使用快速测试向导**
```bash
python quick_test.py
```

**方式二：手动启动**

终端1 - 启动Modbus模拟器（支持型号选择）：
```bash
# 启动120kW双枪直流桩模拟器
python modbus_charger_simulator.py --model xj_dc_120kw

# 或启动240kW型号
python modbus_charger_simulator.py --model xj_dc_240kw

# 或启动通用充电桩
python modbus_charger_simulator.py --model generic
```

终端2 - 启动主程序：
```bash
python -m edgefusion.main
```

### 3. 访问Web界面

打开浏览器访问：**http://localhost:5000**

## 文档

- [使用指南](USAGE.md) - 详细的使用说明和操作指南
- [架构设计](ARCHITECTURE.md) - 系统架构和技术选型说明

## 项目结构

```
edgefusion/
├── edgefusion/
│   ├── main.py              # 主程序入口
│   ├── config.py            # 配置管理
│   ├── device_manager.py    # 设备管理
│   ├── point_tables.py      # 型号点表定义
│   ├── devices/
│   │   └── charger_controller.py  # 充电桩控制器
│   ├── protocol/            # 协议实现（Modbus/MQTT/OCPP）
│   ├── strategy/            # 控制策略
│   ├── monitor/             # 监控模块
│   │   ├── dashboard.py     # Web监控面板
│   │   ├── database.py      # 数据库操作
│   │   └── collector.py     # 数据采集
│   └── simulator/           # 设备模拟器
├── modbus_charger_simulator.py  # Modbus充电桩模拟器
├── quick_test.py           # 快速测试向导
├── config.yaml             # 配置文件
└── requirements.txt        # 依赖列表
```

## 支持的设备型号

| 型号 | 协议 | 最大功率 | 枪数 | 特点 |
|------|------|----------|------|------|
| 120kW直流桩 | Modbus TCP | 120kW | 2 | 支持功率限制、SOC监控 |
| 240kW直流桩 | Modbus TCP | 240kW | 2 | 支持功率限制、SOC监控 |
| 通用充电桩 | Modbus TCP/RTU | - | 1 | 简单寄存器映射 |

## 版本信息

- **版本**：0.3.0
- **更新日期**：2026-02-26

## 许可证

本项目仅供学习和研究使用。
