# Simulated Device Mode Filter Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make simulated devices visible in the system while allowing a single global control setting to exclude them from mode decisions and control execution.

**Architecture:** Keep device inventory broad and simple: devices expose only `source` (`real` or `simulated`) and `status` (`online` or `offline`). Apply the simulated-device toggle in the mode-controller path before site-state aggregation so the dashboard can still show all devices while control logic only sees the allowed subset.

**Tech Stack:** Python, pytest, Flask, existing EdgeFusion control/simulation modules

---

## Chunk 1: Mode Decision Filter

### Task 1: Add red tests for simulated-device filtering

**Files:**
- Modify: `C:/Users/Lenovo/Desktop/桌面工作空间/终端台区智能化项目/后台项目/edgefusion/test_mode_engine.py`

- [ ] **Step 1: Write failing tests**
- [ ] **Step 2: Run `pytest test_mode_engine.py -q` and verify the new tests fail for the expected reason**
- [ ] **Step 3: Implement the minimal filtering and mode-availability changes**
- [ ] **Step 4: Re-run `pytest test_mode_engine.py -q` until green**

### Task 2: Wire the global toggle into the control path

**Files:**
- Modify: `C:/Users/Lenovo/Desktop/桌面工作空间/终端台区智能化项目/后台项目/edgefusion/edgefusion/config.py`
- Modify: `C:/Users/Lenovo/Desktop/桌面工作空间/终端台区智能化项目/后台项目/edgefusion/config.yaml`
- Modify: `C:/Users/Lenovo/Desktop/桌面工作空间/终端台区智能化项目/后台项目/edgefusion/edgefusion/main.py`
- Modify: `C:/Users/Lenovo/Desktop/桌面工作空间/终端台区智能化项目/后台项目/edgefusion/edgefusion/strategy/mode_controller.py`
- Modify: `C:/Users/Lenovo/Desktop/桌面工作空间/终端台区智能化项目/后台项目/edgefusion/edgefusion/control/site_state.py`
- Modify: `C:/Users/Lenovo/Desktop/桌面工作空间/终端台区智能化项目/后台项目/edgefusion/edgefusion/control/mode_engine.py`

- [ ] **Step 1: Add `control.use_simulated_devices` to config defaults and sample config**
- [ ] **Step 2: Pass the toggle into the mode-controller config**
- [ ] **Step 3: Filter snapshots before building `SiteState`**
- [ ] **Step 4: Require at least one usable export-control path before entering `export_protect`**

## Chunk 2: Device Inventory Metadata

### Task 3: Normalize device source and status metadata

**Files:**
- Modify: `C:/Users/Lenovo/Desktop/桌面工作空间/终端台区智能化项目/后台项目/edgefusion/edgefusion/device_manager.py`
- Modify: `C:/Users/Lenovo/Desktop/桌面工作空间/终端台区智能化项目/后台项目/edgefusion/edgefusion/protocol/simulation.py`
- Modify: `C:/Users/Lenovo/Desktop/桌面工作空间/终端台区智能化项目/后台项目/edgefusion/edgefusion/simulator/site.py`
- Modify: `C:/Users/Lenovo/Desktop/桌面工作空间/终端台区智能化项目/后台项目/edgefusion/test_dashboard_device_view.py`

- [ ] **Step 1: Write a dashboard/inventory test that expects `source` and `online/offline` status**
- [ ] **Step 2: Run the targeted dashboard test and verify it fails**
- [ ] **Step 3: Make simulation devices report `source=simulated` and normalized status**
- [ ] **Step 4: Make registered/discovered real devices default to `source=real` and normalized status**
- [ ] **Step 5: Re-run targeted dashboard tests until green**

## Chunk 3: Verification

### Task 4: Prove the main workspace is green

**Files:**
- Verify only

- [ ] **Step 1: Run `pytest test_mode_engine.py test_dashboard_device_view.py test_simulation_runtime.py -q`**
- [ ] **Step 2: Run `pytest -q`**
- [ ] **Step 3: Record any remaining warnings separately without expanding scope**
