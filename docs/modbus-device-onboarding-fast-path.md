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

## 4. 当前仓库里，具体改哪个文件

先说当前真实情况：

- 当前仓库**还没有**稳定的“持久化设备清单配置文件”
- 所以你如果要把一个新厂商设备真正接进当前后台，**多数情况下还是要改代码**
- 真正的差别只在于：你是先做**临时联调代码**，还是直接做**可复用 profile 代码**

建议按下面三档理解。

### 4.1 只想先测通 Modbus 连通性，不做语义接入

这时先不要碰 profile。

看和用这些位置：

- `edgefusion/monitor/dashboard.py`

当前已有的能力：

- `/api/devices/add-modbus`
- `/api/devices/<device_id>/read-register`
- `/api/devices/<device_id>/write-register`

这条线适合做：

- IP/端口/从站号是否能连通
- 原始寄存器能不能读到
- 原始寄存器能不能写进去

这一步的目标只是确认“设备通不通”，不是确认“语义字段已经接入”。

### 4.2 想最快把语义字段接进当前后台

这是当前项目里最现实的第一落点。

直接参考这些文件：

- `test_device_register_mapping.py`
- `test_device_adapter_layer.py`
- `docs/examples/modbus-explicit-mapping-templates.yaml`

当前最快做法是：

1. 先在 `docs/examples/modbus-explicit-mapping-templates.yaml` 按厂家文档填一份最小 `device_info`
2. 再把同样结构的 `device_info` 临时放进你自己的联调脚本或测试里
3. 调用 `DeviceManager.register_device(...)` 或 `register_device_candidate(...)`
4. 用 `read_device_data(...)` / `write_device_data(...)` 走统一语义链路

在当前仓库里，最直接可照抄的示例就是：

- `test_device_register_mapping.py`

这里已经有：

- `grid_meter`
- `pv`
- `energy_storage`
- `charging_station`

的显式 `telemetry_map` / `control_map` 写法。

如果你现在要接第一家真机，建议先按这个方式改：

- 新建一个本地联调脚本，或者
- 临时在现有测试/验证脚本里加一个真实 `device_info`

**不要**第一步就去改 profile。

### 4.3 想把这个厂家做成后续可复用支持

等显式映射已经联调通过，再走这条线。

优先改这些文件：

- `edgefusion/adapters/modbus/profiles/vendors/<vendor>.py`
- `edgefusion/adapters/modbus/profiles/__init__.py`
- 如是充电桩，还要关注 `edgefusion/adapters/charger_profiles.py`
- 必要时补 `test_device_adapter_layer.py`
- 必要时补 `test_device_register_mapping.py`

这里的职责是：

- 给厂家型号补默认 `telemetry_map`
- 给厂家型号补默认 `control_map`
- 补 `status_map` / `mode_map`
- 如果是充电桩，补 connector 级默认映射

这一步完成后，后面同型号设备就不必再手写整份显式映射。

## 5. 接入步骤

### Step 1: 建一份最小设备配置

只填：

- `device_id`
- `type`
- `protocol`
- 连接参数
- 最小 `telemetry_map`
- 最小 `control_map`

不要先录厂家私有扩展字段。

如果按当前仓库实际落地：

- 临时联调：先在测试/脚本里构造 `device_info`
- 可复用接入：联调通过后再转成 `adapters/modbus/profiles/vendors/` 里的 profile

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

## 6. 什么时候要改协议层

大多数设备接入不需要改协议层。

只有下面这些情况才继续改 `ModbusProtocol`：

- 一个语义命令要写多个寄存器
- 一个命令不是普通单值写
- 读取时要特殊拼 32 位或更复杂结构
- 字节序、符号位、倍率有特殊处理

也就是说：

- “地址 + 类型 + 倍率” 这类情况，先在 map 里解决
- “复杂命令报文” 才进协议层

如果真要改，优先看：

- `edgefusion/protocol/modbus.py`

当前复杂命令的现成例子也是在这里展开的。

## 7. 联调完成标准

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

## 8. 从显式映射升级到 profile

当显式映射已经验证通过，再做这一步：

1. 把设备配置里的 `telemetry_map/control_map` 提炼成 profile
2. 给这个厂家/型号补 `model`
3. 用 `model` 回填设备配置
4. 保留显式覆盖能力，只用于少数现场差异

不要反过来做：

- 不要先设计一套很大的 profile，再去猜现场寄存器
- 不要在业务层加 `if 厂家A`
- 不要把临时联调寄存器写死在策略层

## 9. 推荐使用方式

建议以后拿到厂家 Modbus Excel/PDF 后，固定按下面顺序推进：

1. 判断模型类型
2. 摘最小字段
3. 写显式映射
4. 先读通
5. 再控通
6. 再补状态归一
7. 最后沉淀成 profile

这条路径是当前项目里接真机最快、风险也最低的方式。
