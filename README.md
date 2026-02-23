# EdgeFusion 台区智能融合终端后台程序

## 项目简介

EdgeFusion 是一个基于 Python 的台区智能融合终端后台程序，用于对台区内的光伏、储能、充电桩等设备进行协同控制和监控。系统采用模块化设计，具有良好的扩展性和灵活性。

## 核心功能

- **设备管理**：支持光伏、储能、充电桩等设备的协议接入（Modbus、MQTT、OCPP）
- **控制策略**：支持削峰填谷、需求响应、自发自用等多种协同控制策略
- **后台监控**：实时监测设备状态和系统运行情况，提供Web监控面板
- **数据采集**：定期采集设备运行数据并存储
- **灵活配置**：通过配置文件调整系统参数和策略设置

## 系统架构

```
├── edgefusion/
│   ├── __init__.py
│   ├── main.py              # 主程序入口
│   ├── config.py            # 配置管理
│   ├── device_manager.py    # 设备管理模块
│   ├── protocol/            # 协议支持模块
│   │   ├── __init__.py
│   │   ├── base.py          # 协议基类
│   │   ├── modbus.py        # Modbus协议实现
│   │   ├── mqtt.py          # MQTT协议实现
│   │   └── ocpp.py          # OCPP协议实现（充电桩）
│   ├── strategy/            # 控制策略模块
│   │   ├── __init__.py
│   │   ├── base.py          # 策略基类
│   │   ├── peak_shaving.py  # 削峰填谷策略
│   │   ├── demand_response.py # 需求响应策略
│   │   └── self_consumption.py # 自发自用策略
│   ├── monitor/             # 监控模块
│   │   ├── __init__.py
│   │   ├── collector.py     # 数据采集器
│   │   ├── database.py      # 数据存储
│   │   └── dashboard.py     # 监控面板
│   └── utils/               # 工具模块
│       └── __init__.py
├── requirements.txt         # 依赖管理
├── start.bat                # Windows启动脚本
├── config.yaml              # 配置文件（自动生成）
└── README.md                # 项目说明
```

## 安装方法

### 1. 环境要求

- Python 3.8+
- pip 20.0+

### 2. 安装依赖

```bash
# 方法1：使用启动脚本自动安装
# 直接运行 start.bat 脚本，会自动检查并安装依赖

# 方法2：手动安装
pip install -r requirements.txt
```

### 3. 配置文件

首次运行时，系统会自动生成 `config.yaml` 配置文件，包含默认配置。您可以根据实际情况修改配置参数。

## 使用说明

### 1. 启动系统

```bash
# Windows系统
双击 start.bat 脚本

# 或使用命令行
python -m edgefusion.main
```

### 2. 访问监控面板

系统启动后，可通过浏览器访问监控面板：

```
http://localhost:5000
```

### 3. API 接口

监控面板提供以下API接口：

- **系统状态**：`/api/status`
- **设备列表**：`/api/devices`
- **设备详情**：`/api/devices/{device_id}`
- **设备数据**：`/api/devices/{device_id}/data`
- **策略列表**：`/api/strategies`
- **策略详情**：`/api/strategies/{strategy_name}`
- **数据采集状态**：`/api/collector`
- **数据库统计**：`/api/database`

### 4. 配置说明

配置文件 `config.yaml` 包含以下主要配置项：

- **device_manager**：设备管理器配置，包括Modbus、MQTT、OCPP协议的连接参数
- **strategy**：控制策略配置，包括削峰填谷、需求响应、自发自用策略的参数
- **monitor**：监控模块配置，包括数据采集间隔、数据库连接、监控面板端口等

## 设备支持

### 支持的设备类型

- **光伏逆变器**：支持Modbus、MQTT协议
- **储能系统**：支持Modbus、MQTT协议
- **充电桩**：支持OCPP、MQTT协议

### 协议支持

- **Modbus TCP**：用于工业设备通信
- **MQTT**：用于物联网设备通信
- **OCPP 1.6**：用于充电桩通信

## 控制策略

### 1. 削峰填谷策略

- **功能**：在用电高峰期限制功率，低谷期储存电能
- **配置**：可设置峰值时段、谷值时段、功率限制等参数

### 2. 需求响应策略

- **功能**：响应电网的需求侧管理信号，调整用电功率
- **配置**：可设置不同级别的响应策略，包括功率削减比例和持续时间

### 3. 自发自用策略

- **功能**：最大化利用本地光伏发电，优先使用光伏电能
- **配置**：可设置储能SOC目标、最小SOC、光伏功率阈值等参数

## 监控与维护

### 数据存储

系统使用SQLite数据库存储设备运行数据，默认存储在 `edgefusion.db` 文件中。

### 日志记录

系统运行日志输出到控制台，可根据需要重定向到日志文件。

### 常见问题

1. **设备连接失败**：检查设备IP地址、端口号、协议参数是否正确
2. **数据采集失败**：检查设备是否正常运行，协议配置是否正确
3. **策略执行失败**：检查策略配置参数是否合理，设备状态是否正常

## 开发与扩展

### 扩展设备协议

1. 在 `edgefusion/protocol/` 目录下创建新的协议实现文件
2. 继承 `ProtocolBase` 基类，实现必要的方法
3. 在 `protocol/__init__.py` 中注册新协议

### 扩展控制策略

1. 在 `edgefusion/strategy/` 目录下创建新的策略实现文件
2. 继承 `StrategyBase` 基类，实现必要的方法
3. 在 `strategy/__init__.py` 中注册新策略
4. 在 `main.py` 中初始化新策略

## 版本信息

- **版本**：0.1.0
- **更新日期**：2026-02-23

## 联系方式

如有问题或建议，请联系：
- Email: support@edgefusion.com
- GitHub: https://github.com/edgefusion/edgefusion
