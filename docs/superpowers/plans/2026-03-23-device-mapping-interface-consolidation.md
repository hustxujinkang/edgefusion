# Device Mapping Interface Consolidation Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `telemetry_map` and `control_map` the only supported device I/O mapping interfaces and remove legacy compatibility aliases.

**Architecture:** Keep the runtime device I/O contract centered on semantic field maps. Remove alias absorption from `register_map.py`, update tests and docs to describe explicit maps and model/profile generation as two sources for the same runtime structure.

**Tech Stack:** Python, pytest, Markdown docs

---

## Chunk 1: Lock the Runtime Interface

### Task 1: Capture the desired behavior in tests

**Files:**
- Modify: `test_device_adapter_layer.py`
- Test: `test_device_adapter_layer.py`

- [ ] **Step 1: Write failing tests**

Add tests asserting:
- legacy `read_map` / `write_map` / `register_map` are not promoted into primary maps
- `resolve_protocol_read()` and `resolve_protocol_write()` only respect `telemetry_map` / `control_map`

- [ ] **Step 2: Run targeted tests to verify they fail**

Run: `pytest test_device_adapter_layer.py -q`

- [ ] **Step 3: Write the minimal implementation**

Remove alias absorption from `edgefusion/register_map.py` and keep resolution logic centered on the primary maps.

- [ ] **Step 4: Run targeted tests to verify they pass**

Run: `pytest test_device_adapter_layer.py -q`

## Chunk 2: Align Documentation and Normalization

### Task 2: Update docs and device-profile wording

**Files:**
- Modify: `edgefusion/register_map.py`
- Modify: `docs/device-models-and-adaptation.md`
- Modify: `docs/architecture-layering-and-device-adaptation.md`

- [ ] **Step 1: Update runtime mapping comments/docstrings**

Clarify that only `telemetry_map` / `control_map` are supported runtime interfaces.

- [ ] **Step 2: Update documentation**

Rewrite relevant sections so that:
- explicit mapping means hand-authored `telemetry_map` / `control_map`
- model/profile means generated default `telemetry_map` / `control_map`
- legacy alias fields are no longer described as supported

- [ ] **Step 3: Run targeted tests again**

Run: `pytest test_device_adapter_layer.py test_protocol_registry.py -q`

## Chunk 3: Verify the Consolidation

### Task 3: Run focused regression checks

**Files:**
- Test: `test_device_adapter_layer.py`
- Test: `test_protocol_registry.py`
- Test: `test_device_register_mapping.py`

- [ ] **Step 1: Run focused regression suite**

Run: `pytest test_device_adapter_layer.py test_protocol_registry.py test_device_register_mapping.py -q`

- [ ] **Step 2: Review failures and apply minimal fixes if needed**

Only adjust code or tests if the failure is directly caused by the interface consolidation.

- [ ] **Step 3: Re-run the focused regression suite**

Run: `pytest test_device_adapter_layer.py test_protocol_registry.py test_device_register_mapping.py -q`
