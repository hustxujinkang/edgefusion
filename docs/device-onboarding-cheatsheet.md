# 设备接入速查表

这份文档只回答两件事：

1. 储能和充电桩最小正式字段集是什么
2. 厂家 Modbus 文档到显式映射怎么最快落地

如果你是第一次接真实设备，先看这页，再看：

- [Modbus 真机接入最快路径](/C:/Users/Lenovo/Desktop/桌面工作空间/终端台区智能化项目/后台项目/edgefusion/docs/modbus-device-onboarding-fast-path.md)
- [显式映射模板](/C:/Users/Lenovo/Desktop/桌面工作空间/终端台区智能化项目/后台项目/edgefusion/docs/examples/modbus-explicit-mapping-templates.yaml)

## 1. 最小正式字段集

### 1.1 储能 `energy_storage`

| 类别 | 字段 | 必要性 | 说明 |
|------|------|--------|------|
| 读 | `soc` | 必需 | SOC |
| 读 | `power` | 必需 | 充放电功率，必须确认正负方向 |
| 读 | `mode` | 必需 | 运行模式，必要时配 `mode_map` |
| 读 | `status` | 建议 | 在线/故障/运行状态，必要时配 `status_map` |
| 写 | `mode` | 建议 | 控制模式 |
| 写 | `charge_power` | 建议 | 充电功率目标 |
| 写 | `discharge_power` | 建议 | 放电功率目标 |

可选字段：

- `voltage`
- `current`
- `max_charge_power`
- `max_discharge_power`

联调最小目标：

- `soc` 能稳定读到
- `power` 正负方向确认
- `mode` 能归一
- 至少 1 个控制字段下发成功

### 1.2 充电桩 `charging_station` / `charging_connector`

当前项目约定：

- 资产接入按 `charging_station`
- 采集和控制按 `charging_connector`

#### connector 最小正式字段

| 类别 | 字段 | 必要性 | 说明 |
|------|------|--------|------|
| 读 | `status` | 必需 | 枪状态，必要时配 `status_map` |
| 读 | `power` | 必需 | 实时功率 |
| 写 | `power_limit` | 建议 | 最常用的统一控制字段 |
| 写 | `start_charging` | 可选 | 如果厂家支持启停命令 |
| 写 | `stop_charging` | 可选 | 如果厂家支持启停命令 |
| 写 | `clear_fault` | 可选 | 如果厂家支持故障清除 |
| 写 | `emergency_stop` | 可选 | 如果厂家支持急停 |

connector 可选字段：

- `energy`
- `voltage`
- `current`
- `temperature`
- `max_power`
- `min_power`

联调最小目标：

- connector 视图展开正确
- `status` 能归一成统一语义
- `power` 可读
- 至少 1 个控制字段下发成功

## 2. 厂家文档到显式映射 Checklist

按下面顺序做，不要一上来录完整寄存器表。

### 2.1 先确认基础信息

- [ ] 确认设备统一模型：`energy_storage` 还是 `charging_station`
- [ ] 确认通讯方式：`Modbus TCP` 还是 `Modbus RTU`
- [ ] 确认连接参数：`host/port` 或串口参数、`unit_id/slave_id`
- [ ] 确认寄存器地址基准：文档是 0 基还是 1 基
- [ ] 确认数据类型：`u16/i16/u32/i32`
- [ ] 确认倍率、单位、符号位

### 2.2 只摘最小字段

储能：

- [ ] `soc`
- [ ] `power`
- [ ] `mode`
- [ ] `status`（如有）
- [ ] `mode` 写入
- [ ] `charge_power` 写入
- [ ] `discharge_power` 写入

充电桩：

- [ ] 每个 connector 的 `status`
- [ ] 每个 connector 的 `power`
- [ ] 每个 connector 的 `power_limit`（如有）
- [ ] `start_charging` / `stop_charging`（如有）

### 2.3 先填显式映射，不先做 profile

- [ ] 填 `device_id`
- [ ] 填 `type`
- [ ] 填 `protocol: modbus`
- [ ] 填连接参数
- [ ] 只填最小 `telemetry_map`
- [ ] 只填最小 `control_map`
- [ ] 如有枚举值差异，再补 `status_map` / `mode_map`

### 2.4 先读通

- [ ] 先读最小字段，不先控
- [ ] 确认读值不是地址偏移错误
- [ ] 确认倍率正确
- [ ] 确认 `power` 正负方向正确
- [ ] 确认 `status/mode` 是否需要归一化映射

### 2.5 再控通

- [ ] 先挑 1 个最小控制字段验证
- [ ] 确认写的是单寄存器还是多寄存器
- [ ] 确认控制单位和采集单位一致
- [ ] 确认是否需要固定值、使能位、前置命令
- [ ] 确认写后是否需要回读验证

### 2.6 最后再补扩展字段

- [ ] 厂家私有字段先不要进业务主链
- [ ] 确需保留时，放进 `telemetry_map` / `control_map`
- [ ] 作为扩展字段记录，不要当正式核心字段

### 2.7 联调通过后再沉淀 profile

- [ ] 显式映射已验证通过
- [ ] 设备型号后续会复用
- [ ] 再把映射提炼成 `model/profile`

## 3. 最容易踩的坑

- 文档地址基准不一致，导致整体偏移
- 32 位寄存器拼接顺序理解错误
- `power` 正负方向没确认
- 写值单位和读值单位不一致
- 把厂家私有字段直接当成业务正式字段
- 还没读通就开始设计完整 profile

## 4. 现场默认动作

以后拿到厂家 Modbus 文档，默认动作固定为：

1. 先判断模型
2. 再摘最小字段
3. 先写显式映射
4. 先读通
5. 再控通
6. 最后再沉淀 profile
