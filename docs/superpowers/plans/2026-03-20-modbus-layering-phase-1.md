# Modbus Layering Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将当前以 Modbus TCP 为核心的真实设备主链路拆成更清晰的“厂家适配层 / Modbus 传输协议层 / TCP 物理连接层”，同时保持现有业务语义和外部行为不变。

**Architecture:** 本次只做 Modbus 一期重构，不引入 RTU 和 MQTT 真读链路。`DeviceManager` 改为依赖设备适配模块获取语义映射，并通过独立的 Modbus TCP transport 承载连接细节；`ModbusProtocol` 只保留 Modbus 请求/响应和寄存器编码逻辑。保留原有 `point_tables.py` 和 `register_map.py` 对外兼容，但逐步让新代码走 `adapters/` 和 `transport/`。

**Tech Stack:** Python, pytest, pymodbus

---

## Chunk 1: Layering Skeleton

### Task 1: 设备适配层入口

**Files:**
- Create: `edgefusion/adapters/__init__.py`
- Create: `edgefusion/adapters/device_profiles.py`
- Modify: `edgefusion/device_manager.py`
- Test: `test_device_adapter_layer.py`

- [ ] **Step 1: Write the failing test**

```python
from edgefusion.adapters.device_profiles import normalize_device_profile, resolve_protocol_read


def test_normalize_device_profile_merges_point_table_defaults():
    device = normalize_device_profile({
        "device_id": "storage_1",
        "type": "energy_storage",
        "model": "generic_storage",
        "protocol": "modbus",
    })
    assert "telemetry_map" in device
    assert resolve_protocol_read(device, "soc")["addr"] == 52001
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest -q test_device_adapter_layer.py`
Expected: FAIL with import error or missing function

- [ ] **Step 3: Write minimal implementation**

Create adapter helpers that:
- merge point-table defaults into device info
- preserve current `source/status` normalization
- expose protocol read/write resolution

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest -q test_device_adapter_layer.py`
Expected: PASS

### Task 2: DeviceManager 改走适配层

**Files:**
- Modify: `edgefusion/device_manager.py`
- Test: `test_device_register_mapping.py`

- [ ] **Step 1: Write/adjust failing test**

Add an assertion that `DeviceManager` still resolves model defaults and connector views correctly after adapter extraction.

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest -q test_device_register_mapping.py`
Expected: FAIL when `DeviceManager` is partially switched

- [ ] **Step 3: Write minimal implementation**

Refactor `DeviceManager` to import and use adapter helpers instead of directly depending on `point_tables.py` and `register_map.py`.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest -q test_device_register_mapping.py`
Expected: PASS

## Chunk 2: Modbus Protocol vs TCP Transport

### Task 3: 拆出 TCP transport

**Files:**
- Create: `edgefusion/transport/__init__.py`
- Create: `edgefusion/transport/modbus_transport.py`
- Create: `edgefusion/transport/modbus_tcp.py`
- Modify: `edgefusion/protocol/modbus.py`
- Test: `test_modbus_transport_layer.py`

- [ ] **Step 1: Write the failing test**

```python
from edgefusion.protocol.modbus import ModbusProtocol


class DummyTransport:
    def connect(self): return True
    def disconnect(self): return True
    def read_holding_registers(self, addr, count, slave): ...
    def write_register(self, addr, value, slave): ...
    def write_registers(self, addr, values, slave): ...


def test_modbus_protocol_uses_transport_object_instead_of_tcp_client():
    protocol = ModbusProtocol({}, transport=DummyTransport())
    assert protocol.transport is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest -q test_modbus_transport_layer.py`
Expected: FAIL because protocol does not yet accept transport injection

- [ ] **Step 3: Write minimal implementation**

Introduce transport abstraction and move TCP client details out of `ModbusProtocol`.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest -q test_modbus_transport_layer.py`
Expected: PASS

### Task 4: 保持现有 Modbus 行为不回退

**Files:**
- Modify: `edgefusion/protocol/modbus.py`
- Test: `test_modbus_protocol_commands.py`
- Test: `test_device_register_mapping.py`

- [ ] **Step 1: Use existing tests as regression guards**

Ensure typed reads, scaled reads, complex register batch writes, and endpoint-isolated behavior still work after protocol/transport split.

- [ ] **Step 2: Run tests to verify any regression fails**

Run: `python -m pytest -q test_modbus_protocol_commands.py test_device_register_mapping.py`
Expected: FAIL if transport split breaks semantics

- [ ] **Step 3: Write minimal implementation**

Refactor only enough to preserve:
- typed register decode
- fixed-value writes
- complex batch commands
- per-endpoint protocol creation

- [ ] **Step 4: Run tests to verify it passes**

Run: `python -m pytest -q test_modbus_protocol_commands.py test_device_register_mapping.py`
Expected: PASS

## Chunk 3: Docs and Verification

### Task 5: 更新架构文档口径

**Files:**
- Modify: `ARCHITECTURE.md`
- Modify: `docs/architecture-layering-and-device-adaptation.md`

- [ ] **Step 1: Update docs**

Document that:
- Modbus TCP transport has been separated
- adapters are now the primary semantic mapping entry
- RTU and MQTT remain next steps

- [ ] **Step 2: Verify docs reflect current code**

Run: manual review of affected sections
Expected: wording matches implementation

### Task 6: 全量验证

**Files:**
- Test: full suite

- [ ] **Step 1: Run targeted tests**

Run: `python -m pytest -q test_device_adapter_layer.py test_modbus_transport_layer.py test_modbus_protocol_commands.py test_device_register_mapping.py`
Expected: PASS

- [ ] **Step 2: Run full suite**

Run: `python -m pytest -q`
Expected: PASS with only pre-existing warnings

- [ ] **Step 3: Review diff**

Run: `git diff --stat`
Expected: changes limited to adapters, transport, protocol, device manager, docs, and tests
