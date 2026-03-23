# 设备模型与接入适配说明

> 当前阶段建议优先从 [docs/README.md](/C:/Users/Lenovo/Desktop/桌面工作空间/终端台区智能化项目/后台项目/edgefusion/docs/README.md) 进入文档体系。

本文档用于在正式设备接入前，明确 EdgeFusion 当前对各类设备的统一模型、内置点表能力，以及新增真实设备时的适配方式。

配套资料：

- 最短字段表和接入清单见 [docs/device-onboarding-cheatsheet.md](/C:/Users/Lenovo/Desktop/桌面工作空间/终端台区智能化项目/后台项目/edgefusion/docs/device-onboarding-cheatsheet.md)
- 真机联调最短路径见 `docs/modbus-device-onboarding-fast-path.md`
- 可复制的显式映射模板见 `docs/examples/modbus-explicit-mapping-templates.yaml`

## 1. 目标

系统当前采用“业务语义先行，硬件协议后适配”的方式建模：

- 控制策略、采集器、面板接口只面向统一语义字段和语义命令
- 厂家寄存器地址、寄存器分区、控制报文格式统一收敛到点表和协议层
- 在真实设备未到位前，可以先用仿真和通用模型联调
- 真实设备到位后，原则上只补型号点表或少量协议适配，不改业务控制逻辑

## 2. 当前统一链路

当前主链路如下：

1. 设备注册时提供 `type`、`protocol`、可选 `model`
2. `point_tables.py` 根据 `model` 生成默认 `telemetry_map` / `control_map`
3. `DeviceManager` 将显式配置与默认点表合并
4. `register_map.py` 将语义字段解析为寄存器地址或复杂控制命令
5. 协议层完成真实读写
6. 采集器、模式控制、面板控制都只使用统一语义

这意味着：

- 业务层不会直接读 `0x210E` 这种寄存器
- 业务层只会读 `power`、`soc`、`power_limit`、`charge_power` 这类语义字段
- 复杂控制报文也通过统一 `write_device_data()` 下发

当前项目将 `telemetry_map` / `control_map` 视为**唯一正式运行时映射接口**：

- 显式接入时，设备信息直接声明这两个 map
- 型号点表接入时，profile/point table 负责生成这两个 map
- 不再支持 `read_map` / `write_map` / `register_map` 这类旧别名字段

## 3. 统一建模约定

### 3.1 总表

- `type`: `grid_meter`
- 当前内置通用模型: `generic_grid_meter`

当前语义字段：

- `power`: 总表功率
- `status`: 在线/状态位

核心字段：

- `power`
- `status`

约定：

- 业务层只依赖总表功率语义，不依赖具体寄存器地址
- 若厂家总表有额外字段，可继续扩展到 `telemetry_map`

### 3.2 光伏

- `type`: `pv`
- 当前内置通用模型: `generic_pv`

当前语义字段：

- `power`
- `energy`
- `voltage`
- `current`
- `status`
- `power_limit`
- `min_power_limit`

当前语义控制：

- `power_limit`

核心字段：

- `power`
- `status`
- `power_limit`

可选字段：

- `energy`
- `voltage`
- `current`
- `min_power_limit`

约定：

- 反送保护和模式控制依赖的是 `power_limit` 这类语义控制，不依赖厂家限发寄存器地址
- 如果厂家设备有更复杂的限发方式，可以在 `control_map` 中定义更具体的命令

### 3.3 储能

- `type`: `energy_storage`
- 当前内置通用模型: `generic_storage`

当前语义字段：

- `soc`
- `power`
- `voltage`
- `current`
- `mode`
- `max_charge_power`
- `max_discharge_power`

当前语义控制：

- `mode`
- `charge_power`
- `discharge_power`

核心字段：

- `soc`
- `power`
- `mode`
- `charge_power`
- `discharge_power`

可选字段：

- `status`
- `voltage`
- `current`
- `max_charge_power`
- `max_discharge_power`

约定：

- 策略层只关心储能是否可充、SOC、充放电能力和目标功率
- 厂家内部枚举值、模式码位和寄存器布局应在点表或适配层处理

### 3.4 充电桩

- 桩接入对象: `charging_station`
- 枪控制对象: `charging_connector`

当前内置模型：

- `generic_charger`
- `xj_dc_120kw`
- `xj_dc_240kw`

当前语义字段：

- `status`
- `power`
- `energy`
- `voltage`
- `current`
- `temperature`
- 厂家扩展字段
  - 例如许继枪区里的 `state`、`mode`、`alarm`、`fault`、`meter_reading`

当前语义控制：

- `start_charging`
- `stop_charging`
- `clear_fault`
- `emergency_stop`
- `power_limit`

connector 核心字段：

- `status`
- `power`
- `power_limit`

connector 可选字段：

- `energy`
- `voltage`
- `current`
- `temperature`
- `max_power`
- `min_power`

充电桩的核心约定：

- 资产和接入按桩建模
- 采集和控制按枪建模
- 面板控制和策略控制共用同一条 connector 级语义下发链路

## 4. 目前内置点表能力

当前仓库已内置以下类型的默认点表：

| 模型 | 类型 | 说明 |
|------|------|------|
| `generic_grid_meter` | 总表 | 通用总表语义字段映射 |
| `generic_pv` | 光伏 | 通用光伏读写语义映射 |
| `generic_storage` | 储能 | 通用储能读写语义映射 |
| `generic_charger` | 充电桩 | 单枪通用桩语义字段和固定控制命令 |
| `xj_dc_120kw` | 充电桩 | 双枪许继直流桩，支持复杂控制报文 |
| `xj_dc_240kw` | 充电桩 | 双枪许继直流桩，支持复杂控制报文 |

说明：

- 总表、光伏、储能当前内置的是“通用模型”
- 充电桩除了通用模型外，已经有许继型号点表和复杂控制命令适配
- 如果真实设备型号不在上表中，需要新增对应点表或显式映射

## 5. 设备接入时如何适配

### 5.1 最简单的方式：显式映射

如果现场只需要快速接入某个设备，且暂时不打算沉淀型号点表，可在设备信息中直接给出运行时主接口：

- `telemetry_map`
- `control_map`

适用场景：

- 单一设备快速联调
- 厂家资料还不完整
- 设备数量少，暂时不需要复用

示例：

```python
{
    "device_id": "pv_real_1",
    "type": "pv",
    "protocol": "modbus",
    "telemetry_map": {
        "power": "31001",
        "status": "31005",
        "power_limit": "31006",
    },
    "control_map": {
        "power_limit": "41001",
    },
}
```

### 5.2 推荐方式：新增型号点表

如果某类设备会重复接入，或者现场后续会扩多台同型号设备，建议直接在 `point_tables.py` 中新增型号点表。

适用场景：

- 同型号设备会复用
- 需要沉淀厂家的标准接入方式
- 需要把厂家差异完全收敛到模型层

这里要强调的是：**型号点表不是另一套运行时接口。**

- 点表/profile 的职责是生成默认 `telemetry_map` / `control_map`
- 运行时读写仍然只走这两个正式主接口

厂家扩展字段处理原则：

- 厂家私有字段仍允许放进 `telemetry_map` / `control_map`
- 这类字段不会阻塞设备接入
- 运行时 `capabilities` 会把它们标成未知扩展字段，提醒业务层不要默认依赖

基本步骤：

1. 确认设备属于哪一类 `type`
2. 新增 `model`
3. 为该 `model` 定义 `telemetry` 或枪区/桩区寄存器
4. 如有控制能力，补 `control` 或 `connector_control`
5. 通过 `model` 注册设备
6. 用采集和控制测试确认语义读写正常

### 5.3 什么时候需要协议层扩展

大多数设备只需要点表即可。

只有在以下情况，才需要继续改协议层：

- 一个语义命令需要写多个寄存器
- 控制命令不是“地址 + 单值”的普通写法
- 一个控制命令需要特定报文结构
- 读取时需要特殊拼寄存器、字节序或额外解码

当前仓库里，许继充电桩就是这类例子：

- 点表定义控制入口地址
- `control_map` 中附带命令构造信息
- `ModbusProtocol.write_data()` 在协议层展开为批量寄存器写

## 6. 各类设备接入检查表

### 6.1 总表

- 确认 `power` 的正负号约定
- 确认在线状态字段是否存在
- 确认是否需要额外倍率或寄存器拼接

### 6.2 光伏

- 确认 `power`、`status`、`power_limit` 是否可读
- 确认 `power_limit` 是否可写
- 确认功率单位和倍率

### 6.3 储能

- 确认 `soc`、`power`、`mode` 是否可读
- 确认 `charge_power` / `discharge_power` / `mode` 是否可写
- 确认模式枚举值是否需要转换

### 6.4 充电桩

- 确认桩是单枪还是双枪
- 确认枪区寄存器是否独立
- 确认控制是单寄存器写还是复杂报文
- 确认人工控制和策略控制是否都可通过 connector 级语义命令下发

## 7. 当前边界

当前系统已经完成：

- 光、储、总表、充电桩的统一语义建模
- 点表到语义映射的主链路
- 充电桩按“桩接入、枪控制”的主链路
- 复杂充电桩控制命令的统一下发

当前仍需按现场继续补的内容：

- 具体厂家总表点表
- 具体厂家光伏点表
- 具体厂家储能点表
- 如有特殊报文格式的协议层扩展

## 8. 推荐接入顺序

在正式设备接入时，建议按以下顺序推进：

1. 总表
2. 储能
3. 光伏
4. 充电桩

理由：

- 总表是站级判断的基准
- 储能和光伏是主控制对象
- 充电桩已经具备较完整模型，但现场型号差异仍可能存在
