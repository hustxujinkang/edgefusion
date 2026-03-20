from dataclasses import dataclass, field
from typing import Any

from .site_state import SiteState


@dataclass
class ControlAction:
    device_id: str
    action: str
    value_w: int
    delta_w: int
    reason: str


@dataclass
class ExecutionPlan:
    mode: str
    actions: list[ControlAction] = field(default_factory=list)
    remaining_gap_w: int = 0


def _snapshot_data(state: SiteState, device_type: str) -> list[dict[str, Any]]:
    if isinstance(device_type, tuple):
        valid_types = set(device_type)
        return [
            snapshot
            for snapshot in state.snapshots.values()
            if snapshot.get("device_type") in valid_types
        ]
    return [
        snapshot
        for snapshot in state.snapshots.values()
        if snapshot.get("device_type") == device_type
    ]


def _is_online(snapshot: dict[str, Any]) -> bool:
    return str(snapshot.get("data", {}).get("status", "online")).lower() != "offline"


def _int_value(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def _allocate_evenly(total_w: int, headroom_by_device: dict[str, int]) -> dict[str, int]:
    allocations = {device_id: 0 for device_id in headroom_by_device}
    remaining = total_w
    remaining_headroom = {
        device_id: headroom
        for device_id, headroom in headroom_by_device.items()
        if headroom > 0
    }

    while remaining > 0 and remaining_headroom:
        device_ids = sorted(remaining_headroom)
        participant_count = len(device_ids)
        base_share = remaining // participant_count
        extra = remaining % participant_count
        progress = 0

        for index, device_id in enumerate(device_ids):
            desired = base_share + (1 if index < extra else 0)
            granted = min(desired, remaining_headroom[device_id])
            if granted <= 0:
                continue

            allocations[device_id] += granted
            remaining -= granted
            progress += granted
            remaining_headroom[device_id] -= granted

        remaining_headroom = {
            device_id: headroom
            for device_id, headroom in remaining_headroom.items()
            if headroom > 0
        }

        if progress == 0:
            break

    return allocations


def plan_export_protect(state: SiteState, config: dict[str, Any] | None = None) -> ExecutionPlan:
    config = config or {}
    export_limit_w = int(config.get("export_limit_w", 0))
    storage_soc_soft_limit = float(config.get("storage_soc_soft_limit", 95))

    export_gap_w = max(0, int(round(-(state.grid_power_w or 0) - export_limit_w)))
    remaining_gap_w = export_gap_w
    actions: list[ControlAction] = []

    for snapshot in _snapshot_data(state, "energy_storage"):
        if remaining_gap_w <= 0 or not _is_online(snapshot):
            continue

        data = snapshot.get("data", {})
        soc = float(data.get("soc", 0) or 0)
        if soc >= storage_soc_soft_limit:
            continue

        available_charge_w = max(0, _int_value(data.get("max_charge_power")))
        allocated_w = min(remaining_gap_w, available_charge_w)
        if allocated_w <= 0:
            continue

        actions.append(
            ControlAction(
                device_id=snapshot["device_id"],
                action="set_charge_power",
                value_w=allocated_w,
                delta_w=allocated_w,
                reason="absorb_export_with_storage",
            )
        )
        remaining_gap_w -= allocated_w

    charger_headroom_by_device: dict[str, int] = {}
    charger_current_power_by_device: dict[str, int] = {}
    for snapshot in _snapshot_data(state, ("charging_connector", "charging_station")):
        if not _is_online(snapshot):
            continue

        data = snapshot.get("data", {})
        current_power_w = _int_value(data.get("power"))
        max_power_w = _int_value(data.get("max_power"), current_power_w)

        if current_power_w <= 0:
            continue

        headroom_w = max(0, max_power_w - current_power_w)
        if headroom_w <= 0:
            continue

        charger_headroom_by_device[snapshot["device_id"]] = headroom_w
        charger_current_power_by_device[snapshot["device_id"]] = current_power_w

    if remaining_gap_w > 0 and charger_headroom_by_device:
        charger_allocations = _allocate_evenly(remaining_gap_w, charger_headroom_by_device)
        for device_id in sorted(charger_allocations):
            allocation_w = charger_allocations[device_id]
            if allocation_w <= 0:
                continue

            actions.append(
                ControlAction(
                    device_id=device_id,
                    action="set_power_limit",
                    value_w=charger_current_power_by_device[device_id] + allocation_w,
                    delta_w=allocation_w,
                    reason="increase_active_charger_load",
                )
            )
            remaining_gap_w -= allocation_w

    for snapshot in _snapshot_data(state, "pv"):
        if remaining_gap_w <= 0 or not _is_online(snapshot):
            continue

        data = snapshot.get("data", {})
        current_limit_w = _int_value(data.get("power_limit"), _int_value(data.get("power")))
        min_power_limit_w = _int_value(data.get("min_power_limit"))
        curtailable_w = max(0, current_limit_w - min_power_limit_w)
        curtailment_w = min(remaining_gap_w, curtailable_w)

        if curtailment_w <= 0:
            continue

        actions.append(
            ControlAction(
                device_id=snapshot["device_id"],
                action="set_power_limit",
                value_w=current_limit_w - curtailment_w,
                delta_w=-curtailment_w,
                reason="curtail_pv_export",
            )
        )
        remaining_gap_w -= curtailment_w

    return ExecutionPlan(
        mode="export_protect",
        actions=actions,
        remaining_gap_w=remaining_gap_w,
    )
