# Site Simulation Runtime Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an in-process site simulation runtime that exposes virtual devices through a protocol so the main app can start a full local光储充+总表 environment without extra scripts.

**Architecture:** Add a `SimulationProtocol` below `DeviceManager`, backed by a `SiteSimulator` that owns `base_load`, `pv`, `storage`, `chargers`, and a derived `grid_meter`. Keep the app's control path unchanged: `DeviceManager -> DataCollector -> ModeControllerStrategy`.

**Tech Stack:** Python 3.10+, pytest, existing simulator and protocol modules

---

## Chunk 1: Simulation Core

### Task 1: Add failing tests for site-level energy balance and protocol discovery

**Files:**
- Create: `C:/Users/Lenovo/Desktop/桌面工作空间/终端台区智能化项目/后台项目/edgefusion/.worktrees/export-protect-mode-engine/test_simulation_runtime.py`

- [ ] **Step 1: Write the failing test**

```python
def test_site_simulator_derives_grid_power_from_device_balance():
    ...


def test_simulation_protocol_discovers_virtual_devices_and_reads_values():
    ...
```

- [ ] **Step 2: Run test to verify it fails**

Run: `C:/Users/Lenovo/Desktop/桌面工作空间/终端台区智能化项目/后台项目/edgefusion/.venv/Scripts/python.exe -m pytest test_simulation_runtime.py -v`
Expected: FAIL because site simulation runtime does not exist yet

- [ ] **Step 3: Write minimal implementation**

```python
class SiteSimulator:
    ...


class SimulationProtocol(ProtocolBase):
    ...
```

- [ ] **Step 4: Run test to verify it passes**

Run: `C:/Users/Lenovo/Desktop/桌面工作空间/终端台区智能化项目/后台项目/edgefusion/.venv/Scripts/python.exe -m pytest test_simulation_runtime.py -v`
Expected: PASS

### Task 2: Add failing tests for collector support and one-key app wiring

**Files:**
- Modify: `C:/Users/Lenovo/Desktop/桌面工作空间/终端台区智能化项目/后台项目/edgefusion/.worktrees/export-protect-mode-engine/test_simulation_runtime.py`
- Modify: `C:/Users/Lenovo/Desktop/桌面工作空间/终端台区智能化项目/后台项目/edgefusion/.worktrees/export-protect-mode-engine/test_edgefusion.py`

- [ ] **Step 1: Write the failing test**

```python
def test_data_collector_captures_grid_meter_and_control_capability_fields_from_simulation():
    ...


def test_edgefusion_wires_simulation_protocol_when_enabled():
    ...
```

- [ ] **Step 2: Run test to verify it fails**

Run: `C:/Users/Lenovo/Desktop/桌面工作空间/终端台区智能化项目/后台项目/edgefusion/.venv/Scripts/python.exe -m pytest test_simulation_runtime.py test_edgefusion.py::test_edgefusion_wires_simulation_protocol_when_enabled -v`
Expected: FAIL because collector and app wiring are incomplete

- [ ] **Step 3: Write minimal implementation**

```python
def _collect_grid_meter_data(...):
    ...
```

- [ ] **Step 4: Run test to verify it passes**

Run: `C:/Users/Lenovo/Desktop/桌面工作空间/终端台区智能化项目/后台项目/edgefusion/.venv/Scripts/python.exe -m pytest test_simulation_runtime.py test_edgefusion.py -v`
Expected: PASS

## Chunk 2: Focused Verification

### Task 3: Run focused regression coverage

**Files:**
- Modify: `C:/Users/Lenovo/Desktop/桌面工作空间/终端台区智能化项目/后台项目/edgefusion/.worktrees/export-protect-mode-engine/test_simulation_runtime.py`

- [ ] **Step 1: Run focused verification**

Run: `C:/Users/Lenovo/Desktop/桌面工作空间/终端台区智能化项目/后台项目/edgefusion/.venv/Scripts/python.exe -m pytest test_simulation_runtime.py test_mode_engine.py test_edgefusion.py test_simple.py test_simulator.py -v`
Expected: PASS

- [ ] **Step 2: Apply any small green refactors if needed**

```python
# refactor without changing behavior
```

- [ ] **Step 3: Re-run focused verification**

Run: `C:/Users/Lenovo/Desktop/桌面工作空间/终端台区智能化项目/后台项目/edgefusion/.venv/Scripts/python.exe -m pytest test_simulation_runtime.py test_mode_engine.py test_edgefusion.py test_simple.py test_simulator.py -v`
Expected: PASS
