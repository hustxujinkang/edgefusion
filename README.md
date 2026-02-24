# EdgeFusion - 台区智能融合终端后台系统

基于 Python 的台区智能融合终端后台程序，用于对台区内的光伏、储能、充电桩等设备进行协同控制和监控。

## 功能特性

- **设备管理**：支持光伏、储能、充电桩等设备接入（Modbus、MQTT、OCPP）
- **设备模拟器**：内置Modbus充电桩模拟器，支持无真实设备调试
- **Web监控面板**：实时监测设备状态，提供可视化界面
- **设备管理UI**：Web界面添加设备、测试连接、读写寄存器
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

终端1 - 启动Modbus模拟器：
```bash
python modbus_charger_simulator.py
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

## 版本信息

- **版本**：0.2.0
- **更新日期**：2026-02-24

## 许可证

本项目仅供学习和研究使用。
