# Mode-Based Export Protection Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the current multi-strategy control loop with a first-pass mode-based controller centered on export protection and a single site state source.

**Architecture:** Keep the existing protocol, point-table, collector, and dashboard layers intact. Add a small control core that builds a `SiteState` from collector snapshots, arbitrates between `manual_override`, `safe_hold`, `export_protect`, and `business_normal`, produces an execution plan, and runs it through one controller strategy object so the rest of the app can keep its current start/stop/status shape.

**Tech Stack:** Python 3.10+, pytest, dataclasses, existing `edgefusion` runtime modules

---

## Chunk 1: Control Core

### Task 1: Add failing tests for site state and mode arbitration

**Files:**
- Create: `C:/Users/Lenovo/Desktop/桌面工作空间/终端台区智能化项目/后台项目/edgefusion/.worktrees/export-protect-mode-engine/test_mode_engine.py`

- [ ] **Step 1: Write the failing test**

```python
def test_build_site_state_marks_missing_grid_power_as_untrusted():
    ...


def test_arbitrate_prefers_export_protect_when_export_limit_is_exceeded():
    ...
```

- [ ] **Step 2: Run test to verify it fails**

Run: `C:/Users/Lenovo/Desktop/桌面工作空间/终端台区智能化项目/后台项目/edgefusion/.venv/Scripts/python.exe -m pytest test_mode_engine.py -v`
Expected: FAIL because control core modules do not exist yet

- [ ] **Step 3: Write minimal implementation**

```python
@dataclass
class SiteState:
    ...


def build_site_state(...):
    ...


def arbitrate_mode(...):
    ...
```

- [ ] **Step 4: Run test to verify it passes**

Run: `C:/Users/Lenovo/Desktop/桌面工作空间/终端台区智能化项目/后台项目/edgefusion/.venv/Scripts/python.exe -m pytest test_mode_engine.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add test_mode_engine.py edgefusion/control/*.py
git commit -m "feat: add site state and mode arbitration core"
```

### Task 2: Add failing tests for export protection planning

**Files:**
- Modify: `C:/Users/Lenovo/Desktop/桌面工作空间/终端台区智能化项目/后台项目/edgefusion/.worktrees/export-protect-mode-engine/test_mode_engine.py`
- Modify: `C:/Users/Lenovo/Desktop/桌面工作空间/终端台区智能化项目/后台项目/edgefusion/.worktrees/export-protect-mode-engine/edgefusion/control/*.py`

- [ ] **Step 1: Write the failing test**

```python
def test_export_protect_allocates_storage_then_active_chargers_then_pv_curtailment():
    ...


def test_export_protect_splits_charger_headroom_evenly_with_caps():
    ...
```

- [ ] **Step 2: Run test to verify it fails**

Run: `C:/Users/Lenovo/Desktop/桌面工作空间/终端台区智能化项目/后台项目/edgefusion/.venv/Scripts/python.exe -m pytest test_mode_engine.py -v`
Expected: FAIL because export planning logic is not implemented

- [ ] **Step 3: Write minimal implementation**

```python
def plan_export_protect(...):
    ...
```

- [ ] **Step 4: Run test to verify it passes**

Run: `C:/Users/Lenovo/Desktop/桌面工作空间/终端台区智能化项目/后台项目/edgefusion/.venv/Scripts/python.exe -m pytest test_mode_engine.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add test_mode_engine.py edgefusion/control/*.py
git commit -m "feat: add export protection planning"
```

## Chunk 2: Runtime Integration

### Task 3: Add failing integration tests for a single mode-controller strategy

**Files:**
- Modify: `C:/Users/Lenovo/Desktop/桌面工作空间/终端台区智能化项目/后台项目/edgefusion/.worktrees/export-protect-mode-engine/test_mode_engine.py`
- Create: `C:/Users/Lenovo/Desktop/桌面工作空间/终端台区智能化项目/后台项目/edgefusion/.worktrees/export-protect-mode-engine/edgefusion/strategy/mode_controller.py`

- [ ] **Step 1: Write the failing test**

```python
def test_mode_controller_uses_collector_snapshots_and_executes_export_actions():
    ...


def test_mode_controller_enters_safe_hold_when_required_state_is_missing():
    ...
```

- [ ] **Step 2: Run test to verify it fails**

Run: `C:/Users/Lenovo/Desktop/桌面工作空间/终端台区智能化项目/后台项目/edgefusion/.venv/Scripts/python.exe -m pytest test_mode_engine.py -v`
Expected: FAIL because mode controller strategy does not exist yet

- [ ] **Step 3: Write minimal implementation**

```python
class ModeControllerStrategy(StrategyBase):
    ...
```

- [ ] **Step 4: Run test to verify it passes**

Run: `C:/Users/Lenovo/Desktop/桌面工作空间/终端台区智能化项目/后台项目/edgefusion/.venv/Scripts/python.exe -m pytest test_mode_engine.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add test_mode_engine.py edgefusion/strategy/mode_controller.py edgefusion/strategy/__init__.py
git commit -m "feat: add mode controller strategy"
```

### Task 4: Integrate the controller into app startup and verify targeted runtime tests

**Files:**
- Modify: `C:/Users/Lenovo/Desktop/桌面工作空间/终端台区智能化项目/后台项目/edgefusion/.worktrees/export-protect-mode-engine/edgefusion/main.py`
- Modify: `C:/Users/Lenovo/Desktop/桌面工作空间/终端台区智能化项目/后台项目/edgefusion/.worktrees/export-protect-mode-engine/test_edgefusion.py`

- [ ] **Step 1: Write the failing test**

```python
def test_edgefusion_initializes_single_mode_controller_strategy():
    ...
```

- [ ] **Step 2: Run test to verify it fails**

Run: `C:/Users/Lenovo/Desktop/桌面工作空间/终端台区智能化项目/后台项目/edgefusion/.venv/Scripts/python.exe -m pytest test_edgefusion.py::test_edgefusion_initializes_single_mode_controller_strategy -v`
Expected: FAIL because app still initializes the old strategy pool

- [ ] **Step 3: Write minimal implementation**

```python
def _init_strategies(self):
    self.strategies['mode_controller'] = ModeControllerStrategy(...)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `C:/Users/Lenovo/Desktop/桌面工作空间/终端台区智能化项目/后台项目/edgefusion/.venv/Scripts/python.exe -m pytest test_mode_engine.py test_edgefusion.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add edgefusion/main.py test_edgefusion.py
git commit -m "feat: use mode-based export protection controller"
```

### Task 5: Verify the focused regression surface

**Files:**
- Modify: `C:/Users/Lenovo/Desktop/桌面工作空间/终端台区智能化项目/后台项目/edgefusion/.worktrees/export-protect-mode-engine/test_mode_engine.py`
- Modify: `C:/Users/Lenovo/Desktop/桌面工作空间/终端台区智能化项目/后台项目/edgefusion/.worktrees/export-protect-mode-engine/test_edgefusion.py`

- [ ] **Step 1: Run focused verification**

Run: `C:/Users/Lenovo/Desktop/桌面工作空间/终端台区智能化项目/后台项目/edgefusion/.venv/Scripts/python.exe -m pytest test_mode_engine.py test_edgefusion.py test_simple.py -v`
Expected: PASS

- [ ] **Step 2: If needed, make small green refactors**

```python
# keep behavior unchanged while improving names or duplication only
```

- [ ] **Step 3: Re-run focused verification**

Run: `C:/Users/Lenovo/Desktop/桌面工作空间/终端台区智能化项目/后台项目/edgefusion/.venv/Scripts/python.exe -m pytest test_mode_engine.py test_edgefusion.py test_simple.py -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add test_mode_engine.py test_edgefusion.py edgefusion
git commit -m "test: verify mode-based export protection flow"
```
