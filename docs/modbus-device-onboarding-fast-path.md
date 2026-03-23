# Modbus 真机接入最快路径

本文档面向“工控机后台开发阶段 + 厂家刚给出 Modbus 协议资料”的场景，目标不是一次性沉淀完整厂家 profile，而是先用最短路径把真实设备接通。

## 1. 先做判断，不要直接抄全表

拿到厂家文档后，先只回答 4 个问题：

1. 这台设备属于哪类统一模型
2. 现场到底走 `Modbus TCP` 还是 `Modbus RTU`
3. 先联调最少哪些字段
4. 这批设备后面是否会重复接入

当前项目统一模型只建议先落到下面几类：

- `grid_meter`
- `pv`
- `energy_storage`
- `charging_station`
- `charging_connector`

如果连模型都还没定清，不要先写点表。

## 2. 先圈最小字段

先只摘最小字段，不要一上来录完整寄存器表。

### 2.1 总表

最小字段：

- `power`
- `status`

### 2.2 光伏

最小字段：

- `power`
- `status`
- 可选 `power_limit`

### 2.3 储能

最小字段：

- `soc`
- `power`
- `mode`
- 可选 `status`

最小控制字段：

- `mode`
- `charge_power`
- `discharge_power`

### 2.4 充电桩

按当前项目约定：

- 资产接入按 `charging_station`
- 采集和控制按 `charging_connector`

单枪最小字段：

- `status`
- `power`
- 可选 `power_limit`

常见控制字段：

- `power_limit`
- `start_charging`
- `stop_charging`
- `clear_fault`
- `emergency_stop`

## 3. 默认先走显式映射

当你第一次接某个厂家设备时，默认先不要补 profile，直接写：

- `telemetry_map`
- `control_map`
- 可选 `status_map`
- 可选 `mode_map`

原因很简单：

- 这是当前项目唯一正式运行时主接口
- 联调速度最快
- 不需要先决定 profile 结构怎么沉淀

只有在满足下面任一条件时，再把这套映射沉淀成 `model/profile`：

- 同型号后面还会继续接
- 已经联调通过
- 映射结构相对稳定

## 4. 接入步骤

### Step 1: 建一份最小设备配置

只填：

- `device_id`
- `type`
- `protocol`
- 连接参数
- 最小 `telemetry_map`
- 最小 `control_map`

不要先录厂家私有扩展字段。

### Step 2: 先读，不要先控

先验证最小读链路：

- 能否稳定读到数据
- 地址、类型、倍率是否正确
- 正负方向是否正确
- 枚举值是否需要 `status_map` / `mode_map`

优先读下面这些字段：

- 总表：`power`
- 光伏：`power`
- 储能：`soc`, `power`, `mode`
- 充电枪：`status`, `power`

### Step 3: 再补控制

读通以后，再补最小控制字段：

- 光伏：`power_limit`
- 储能：`mode`, `charge_power`, `discharge_power`
- 充电枪：`power_limit` 或 `start_charging` / `stop_charging`

如果控制失败，先确认：

- 这是写单寄存器、写多寄存器，还是固定报文
- 厂家是否要求前置使能位
- 写值单位是否和采集单位一致
- 是否需要单独回读确认

### Step 4: 再补状态归一

如果厂家状态值不是统一语义，就补：

- `status_map`
- `mode_map`

目标是让业务层只看到：

- `online / offline`
- `idle / charging / fault`
- `charge / discharge / idle / auto`

### Step 5: 最后再补厂家扩展字段

例如：

- `vendor_alarm_word`
- `vendor_dispatch_code`
- `meter_reading`
- `alarm`
- `fault`

这些字段可以放进 `telemetry_map` / `control_map`，但不要让策略层默认依赖。

## 5. 什么时候要改协议层

大多数设备接入不需要改协议层。

只有下面这些情况才继续改 `ModbusProtocol`：

- 一个语义命令要写多个寄存器
- 一个命令不是普通单值写
- 读取时要特殊拼 32 位或更复杂结构
- 字节序、符号位、倍率有特殊处理

也就是说：

- “地址 + 类型 + 倍率” 这类情况，先在 map 里解决
- “复杂命令报文” 才进协议层

## 6. 联调完成标准

### 6.1 储能

至少满足：

- `soc` 数值可信
- `power` 正负方向确认
- `mode` 能归一
- 最少一个控制字段能正确下发

### 6.2 充电桩

至少满足：

- connector 视图展开正确
- `status` 能归一成统一语义
- `power` 可读
- 最少一个控制字段能正确下发

## 7. 从显式映射升级到 profile

当显式映射已经验证通过，再做这一步：

1. 把设备配置里的 `telemetry_map/control_map` 提炼成 profile
2. 给这个厂家/型号补 `model`
3. 用 `model` 回填设备配置
4. 保留显式覆盖能力，只用于少数现场差异

不要反过来做：

- 不要先设计一套很大的 profile，再去猜现场寄存器
- 不要在业务层加 `if 厂家A`
- 不要把临时联调寄存器写死在策略层

## 8. 推荐使用方式

建议以后拿到厂家 Modbus Excel/PDF 后，固定按下面顺序推进：

1. 判断模型类型
2. 摘最小字段
3. 写显式映射
4. 先读通
5. 再控通
6. 再补状态归一
7. 最后沉淀成 profile

这条路径是当前项目里接真机最快、风险也最低的方式。
