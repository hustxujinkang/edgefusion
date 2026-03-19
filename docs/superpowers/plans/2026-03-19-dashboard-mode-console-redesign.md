# Dashboard Mode Console Redesign Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rework the Dashboard into a mode-machine oriented operations console with clear overview, device access, mode center, mode config, and diagnostics pages.

**Architecture:** Extend the mode controller with reusable diagnostics/config access, expose dedicated Dashboard APIs for mode summary and mode config, then reshape the HTML tabs so the UI consumes these focused APIs instead of the old strategy-centric layout. Keep candidate/current device inventory intact and move misleading historical/database metrics into a diagnostics section.

**Tech Stack:** Python, Flask, Jinja HTML template, Bootstrap, pytest

---

## Chunk 1: Backend Mode APIs

### Task 1: Add failing tests for mode summary/config endpoints

**Files:**
- Modify: `C:\Users\Lenovo\Desktop\桌面工作空间\终端台区智能化项目\后台项目\edgefusion\test_dashboard_device_view.py`

- [ ] Add tests for `/api/modes/summary` and `/api/modes/config`.
- [ ] Verify the tests fail because the endpoints do not exist yet.

### Task 2: Extend mode controller diagnostics and config update support

**Files:**
- Modify: `C:\Users\Lenovo\Desktop\桌面工作空间\终端台区智能化项目\后台项目\edgefusion\edgefusion\strategy\mode_controller.py`
- Modify: `C:\Users\Lenovo\Desktop\桌面工作空间\终端台区智能化项目\后台项目\edgefusion\edgefusion\control\mode_engine.py`

- [ ] Add a diagnostics method that returns filtered snapshots, site trust, mode availability, current mode, reason, and recent actions.
- [ ] Add a minimal config update path for mode enable flags and thresholds used by the Dashboard.
- [ ] Run targeted tests and make them pass.

### Task 3: Expose Dashboard mode APIs

**Files:**
- Modify: `C:\Users\Lenovo\Desktop\桌面工作空间\终端台区智能化项目\后台项目\edgefusion\edgefusion\monitor\dashboard.py`

- [ ] Add `/api/modes/summary` with a stable shape for overview and mode center pages.
- [ ] Add `/api/modes/config` GET/POST for global toggle and export-protect parameters.
- [ ] Keep `/api/control/settings` working as a compatibility alias or wrapper if needed.
- [ ] Run focused pytest for Dashboard tests.

## Chunk 2: Template Restructure

### Task 4: Add failing UI text assertions for new information architecture

**Files:**
- Modify: `C:\Users\Lenovo\Desktop\桌面工作空间\终端台区智能化项目\后台项目\edgefusion\test_dashboard_device_view.py`

- [ ] Assert the root page contains the new tab labels: `运行总览`、`设备接入`、`模式中心`、`模式配置`、`诊断`.
- [ ] Verify the test fails before the template is changed.

### Task 5: Rework the Dashboard template into the new five-page layout

**Files:**
- Modify: `C:\Users\Lenovo\Desktop\桌面工作空间\终端台区智能化项目\后台项目\edgefusion\edgefusion\templates\index.html`

- [ ] Rename tabs and move existing cards into the new sections.
- [ ] Replace the old strategy-centric page with a mode-center view.
- [ ] Move `数据库统计` and historical counters into diagnostics instead of overview.
- [ ] Surface `模拟设备参与模式判断` in the mode config page.
- [ ] Keep candidate/current device actions available from the device access page.

## Chunk 3: Wiring and Verification

### Task 6: Align refresh logic and summaries with the new layout

**Files:**
- Modify: `C:\Users\Lenovo\Desktop\桌面工作空间\终端台区智能化项目\后台项目\edgefusion\edgefusion\templates\index.html`
- Modify: `C:\Users\Lenovo\Desktop\桌面工作空间\终端台区智能化项目\后台项目\edgefusion\edgefusion\monitor\dashboard.py`

- [ ] Update frontend refresh functions to load mode summary/config instead of old strategy-centric blocks.
- [ ] Ensure overview cards report operationally useful counts: active devices, online devices, participating devices.
- [ ] Keep diagnostics fetching collector/database/raw snapshot data.

### Task 7: Run verification

**Files:**
- Test: `C:\Users\Lenovo\Desktop\桌面工作空间\终端台区智能化项目\后台项目\edgefusion\test_dashboard_device_view.py`
- Test: `C:\Users\Lenovo\Desktop\桌面工作空间\终端台区智能化项目\后台项目\edgefusion\test_mode_engine.py`

- [ ] Run focused Dashboard and mode tests.
- [ ] Run full `pytest -q`.
- [ ] Fix regressions until green.
