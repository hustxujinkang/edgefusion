# Device Candidate Inventory Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Separate "candidate devices" from "currently connected devices" so simulated devices do not auto-join the runtime inventory, while keeping a global dashboard toggle for whether simulated devices participate in mode decisions.

**Architecture:** Keep `DeviceManager.devices` as the active runtime inventory and add a parallel candidate inventory for devices that are available to connect. Simulation startup populates only the candidate inventory; explicit activation moves a candidate into the active inventory. Dashboard gets one control-settings API plus candidate list/connect/delete APIs and renders them as separate sections.

**Tech Stack:** Python, Flask, pytest, Bootstrap, existing EdgeFusion simulation/control modules

---

## Chunk 1: DeviceManager Candidate Pool

### Task 1: Add failing tests for candidate inventory behavior

**Files:**
- Modify: `C:/Users/Lenovo/Desktop/桌面工作空间/终端台区智能化项目/后台项目/edgefusion/test_simulation_runtime.py`
- Modify: `C:/Users/Lenovo/Desktop/桌面工作空间/终端台区智能化项目/后台项目/edgefusion/test_dashboard_device_view.py`

- [ ] **Step 1: Write tests proving simulation devices start as candidates, not active devices**
- [ ] **Step 2: Write tests proving Modbus add creates candidates until explicit activation**
- [ ] **Step 3: Run the focused pytest commands and verify RED**

### Task 2: Implement candidate inventory in the device manager

**Files:**
- Modify: `C:/Users/Lenovo/Desktop/桌面工作空间/终端台区智能化项目/后台项目/edgefusion/edgefusion/device_manager.py`

- [ ] **Step 1: Add `device_candidates` storage and candidate CRUD helpers**
- [ ] **Step 2: Stop auto-registering simulation devices during startup**
- [ ] **Step 3: Populate simulation candidates during startup and scenario refresh**
- [ ] **Step 4: Add explicit activation that moves a candidate into the active inventory**

## Chunk 2: Dashboard APIs

### Task 3: Add control-settings and candidate APIs

**Files:**
- Modify: `C:/Users/Lenovo/Desktop/桌面工作空间/终端台区智能化项目/后台项目/edgefusion/edgefusion/monitor/dashboard.py`

- [ ] **Step 1: Add GET/POST control settings endpoint for `use_simulated_devices`**
- [ ] **Step 2: Add candidate list, activate, and delete endpoints**
- [ ] **Step 3: Make Modbus add route register a candidate instead of an active device**
- [ ] **Step 4: Make simulation scenario switch refresh candidate inventory instead of active devices**

## Chunk 3: Dashboard UI

### Task 4: Render the new inventory model in the dashboard

**Files:**
- Modify: `C:/Users/Lenovo/Desktop/桌面工作空间/终端台区智能化项目/后台项目/edgefusion/edgefusion/templates/index.html`

- [ ] **Step 1: Add a control-settings card with the simulated-device toggle**
- [ ] **Step 2: Add a candidate device list with activate/delete actions**
- [ ] **Step 3: Rename/refocus the existing active device section as the current device list**
- [ ] **Step 4: Refresh both lists and settings after add/delete/scenario actions**

## Chunk 4: Verification

### Task 5: Run focused and full verification

**Files:**
- Verify only

- [ ] **Step 1: Run `pytest test_dashboard_device_view.py test_simulation_runtime.py -q`**
- [ ] **Step 2: Run `pytest test_mode_engine.py test_dashboard_device_view.py test_simulation_runtime.py -q`**
- [ ] **Step 3: Run `pytest -q` in the main workspace**
