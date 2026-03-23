# Modbus 真机接入最快路径

这份文档只讲当前仓库里的真实流程。

目标不是“把寄存器先塞进测试里”，而是：

1. 先离线测通真实设备
2. 把新型号做成后端支持
3. 部署后让它自动出现在接入页下拉框
4. 再通过运行态 UI 正式接入

---

## 1. 先分清你是哪条路径

拿到厂家文档后，先判断设备属于哪一类：

- `grid_meter`
- `pv`
- `energy_storage`
- `charging_station`

然后再判断型号是不是**已经在系统支持目录里**。

### 1.1 已支持型号

如果这个型号已经在后端 profile 里存在，那么你**不用改代码**。

你要做的是：

1. 用 `modbus_probe.py` 离线测通
2. 启动运行态
3. 在“设备接入”页选择：
   - 设备类型
   - 设备厂商
   - 设备型号
   - 接入方式（TCP / RTU）
4. 测试连接并加入候选设备

### 1.2 新厂家 / 新型号

如果目录里没有这个型号，那么你要先改代码，让它变成“已支持型号”。

正常要改的文件是：

- `edgefusion/adapters/modbus/profiles/vendors/<vendor>.py`
- `edgefusion/adapters/modbus/profiles/vendors/__init__.py`
- `test_device_register_mapping.py`

只有在下面这些特殊情况，才继续扩展别的文件：

- 充电桩 connector 组织方式和现有模型不兼容：
  - `edgefusion/adapters/charger_profiles.py`
- 协议层需要新的读写能力：
  - `edgefusion/protocol/modbus.py`

---

## 2. 第一步永远先做：离线测通真实设备

### 2.1 为什么不能直接拿 dashboard 当 bring-up 工具

`python -m edgefusion.main` 会启动整套运行时，包括：

- `Database`
- `DataCollector`
- 策略循环
- dashboard

所以第一轮真机联调不要直接起整套 runtime。

先离线测通，避免把“寄存器没通”和“运行态接入逻辑”混在一起。

### 2.2 统一使用 `modbus_probe.py`

当前仓库已经有独立探测脚本：

- `modbus_probe.py`

它只做单机寄存器探测，不启动 `edgefusion.main`。

先确认虚拟环境：

```powershell
.\.venv\Scripts\python.exe --version
```

### 2.3 如果是已支持型号，优先用“按型号自动探测”

现在 `modbus_probe.py` 支持直接带上：

- `--device-type`
- `--vendor`
- `--model`

如果不传 `--register`，它会自动使用和 dashboard 一样的默认探测寄存器。

储能 TCP 示例：

```powershell
.\.venv\Scripts\python.exe .\modbus_probe.py `
  --host 192.168.1.10 `
  --unit-id 1 `
  --device-type energy_storage `
  --vendor generic `
  --model generic_storage
```

充电桩 RTU 示例：

```powershell
.\.venv\Scripts\python.exe .\modbus_probe.py `
  --transport rtu `
  --serial-port COM3 `
  --baudrate 9600 `
  --bytesize 8 `
  --parity N `
  --stopbits 1 `
  --unit-id 1 `
  --device-type charging_station `
  --vendor xj `
  --model xj_dc_120kw
```

### 2.4 如果是新厂家 / 新型号，先用原始寄存器探测

这时候还没有 profile，所以先显式指定寄存器。

TCP 读寄存器：

```powershell
.\.venv\Scripts\python.exe .\modbus_probe.py `
  --host 192.168.1.10 `
  --port 502 `
  --unit-id 1 `
  --register 32001 `
  --type u16
```

RTU 读寄存器：

```powershell
.\.venv\Scripts\python.exe .\modbus_probe.py `
  --transport rtu `
  --serial-port COM3 `
  --baudrate 9600 `
  --bytesize 8 `
  --parity N `
  --stopbits 1 `
  --unit-id 1 `
  --register 32001 `
  --type u16
```

简单单寄存器写：

```powershell
.\.venv\Scripts\python.exe .\modbus_probe.py `
  --host 192.168.1.10 `
  --unit-id 1 `
  --register 42001 `
  --type u16 `
  --write 3000
```

### 2.5 离线探测通过标准

至少满足这些：

- 退出码为 `0`
- 输出 JSON 里 `success = true`
- 至少读通 2 到 3 个最关键寄存器
- 如果支持写，再写通 1 个安全寄存器

建议最少验证字段：

- `grid_meter`: `power`, `status`
- `pv`: `power`, `status`
- `energy_storage`: `soc`, `power`, `mode`
- `charging_station`: 某个枪口的 `status`, `power`

如果这一步没通，不要继续做 profile。

---

## 3. 路径 A：已支持型号，怎么正式接入

这条路径不改代码。

### 3.1 启动运行态

```powershell
.\.venv\Scripts\python.exe -m edgefusion.main
```

### 3.2 在接入页完成接入

现在接入页已经改成动态型号目录。

你要在页面里选择：

- 设备类型
- 设备厂商
- 设备型号
- 接入方式（Modbus TCP / Modbus RTU）

然后填写对应端点参数：

- TCP：
  - `host`
  - `port`
  - `unit_id`
- RTU：
  - `serial_port`
  - `baudrate`
  - `bytesize`
  - `parity`
  - `stopbits`
  - `unit_id`

接入步骤：

1. 点“测试连接”
2. 成功后点“加入候选设备”
3. 在“候选设备”表格里点“接入”

### 3.3 判断是否成功

成功标准：

- 候选设备里出现该设备
- 当前设备列表里出现该设备
- 设备的 `capabilities` 符合该型号语义字段

---

## 4. 路径 B：新厂家 / 新型号，怎么做成系统支持

这条路径才需要改代码。

### 4.1 先从厂家文档摘最小字段

不要先抄完整寄存器表，只摘最小正式字段。

建议最低集：

- `grid_meter`: `power`, `status`
- `pv`: `power`, `status`, 可选 `power_limit`
- `energy_storage`: `soc`, `power`, `mode`, 可选 `status`
- `charging_station`: `status`, `power`, 可选 `power_limit`

### 4.2 新增 vendor profile 文件

新增或修改：

- `edgefusion/adapters/modbus/profiles/vendors/<vendor>.py`

最小目标是让它返回一个能被系统识别的 point table。

你至少要写出：

- `device_type`
- `name`
- `manufacturer`
- `telemetry`
- `control`（如果设备支持控制）
- `status_map` / `mode_map`（如果厂家枚举值不等于系统标准值）

### 4.3 把 vendor 注册进目录

修改：

- `edgefusion/adapters/modbus/profiles/vendors/__init__.py`

至少做两件事：

1. import 新 vendor 模块
2. 把它加入 `VENDOR_PROFILES`

如果这一步没做，前端下拉框不会出现新厂商 / 新型号。

### 4.4 补映射测试

修改：

- `test_device_register_mapping.py`

这里的目标不是“模拟 UI”，而是确认 profile 产出的：

- `telemetry_map`
- `control_map`
- `status_map`
- `mode_map`

都能让设备语义层正常工作。

第一次新增型号，至少补一个最小测试：

- 构造 `device_info`
- 指定 `type`
- 指定 `vendor`
- 指定 `model`
- 验证关键字段读写

### 4.5 什么时候才允许改协议层

只有遇到下面情况，才去改：

- `edgefusion/protocol/modbus.py`

典型触发条件：

- 厂家不是 holding register
- 需要 coil / discrete input / input register
- 需要特殊功能码
- 需要复杂多寄存器拼包 / 解包

如果只是普通 holding register + 单寄存器 / 多寄存器写，不要先动协议层。

---

## 5. 新厂家接入后怎么验证它真的进入了型号目录

代码改完后，先跑测试：

```powershell
.\.venv\Scripts\python.exe -m pytest `
  test_device_register_mapping.py `
  test_dashboard_device_view.py `
  test_protocol_registry.py -q
```

通过后再启动运行态：

```powershell
.\.venv\Scripts\python.exe -m edgefusion.main
```

然后验证：

1. 接入页的“设备类型 / 设备厂商 / 设备型号”下拉里出现新型号
2. 选择它以后，测试连接成功
3. 能加入候选设备
4. 能接入当前设备列表

如果下拉框里没有：

- 先查 `vendors/__init__.py` 有没有注册
- 再查 profile 的 `device_type` 是否写对

---

## 6. 一个最实用的决策原则

以后实习生接设备时，先问这句话：

> 这个型号是不是已经在系统支持目录里？

如果答案是“是”：

- 不改代码
- 只做离线探测 + UI 接入

如果答案是“否”：

- 先离线探测
- 再补 vendor profile 和测试
- 最后让它自动出现在 UI 下拉框里

这就是当前仓库的真实最快路径。
