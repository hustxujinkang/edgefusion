from typing import Any, Dict

from .modbus.profiles import get_modbus_point_table
from .modbus.profiles.common import copy_map, get_nested_registers, register_like


def _get_modbus_charger_table(device_info: Dict[str, Any]) -> Dict[str, Any]:
    model = device_info.get("model")
    vendor = device_info.get("vendor") or device_info.get("manufacturer")
    device_type = device_info.get("type")
    return get_modbus_point_table(
        str(model) if model is not None else None,
        vendor=str(vendor) if vendor is not None else None,
        device_type=str(device_type) if device_type is not None else None,
        fallback_model=None,
    )


def get_charger_connector_count(device_info: Dict[str, Any]) -> int | None:
    if device_info.get("protocol") != "modbus":
        return None

    table = _get_modbus_charger_table(device_info)
    if not table:
        return None

    raw_count = table.get("connector_count", table.get("max_guns"))
    try:
        if raw_count is None:
            return None
        return max(1, int(raw_count))
    except (TypeError, ValueError):
        return None


def get_charger_connector_profile_defaults(device_info: Dict[str, Any], connector_id: int) -> Dict[str, Any]:
    if device_info.get("protocol") != "modbus":
        return {}

    table = _get_modbus_charger_table(device_info)
    if not table:
        return {}

    defaults: Dict[str, Any] = {}

    connector_telemetry = table.get("connector_telemetry")
    if isinstance(connector_telemetry, dict):
        defaults["telemetry_map"] = copy_map(connector_telemetry)
    else:
        gun_registers = get_nested_registers(table, f"gun{connector_id}")
        if gun_registers:
            telemetry = {key: value for key, value in gun_registers.items() if register_like(value)}
            if "state" in telemetry and "status" not in telemetry:
                telemetry["status"] = telemetry["state"]
            defaults["telemetry_map"] = telemetry

    connector_control = table.get("connector_control")
    if isinstance(connector_control, dict):
        normalized_control: Dict[str, Any] = {}
        for key, value in connector_control.items():
            if isinstance(value, dict):
                entry = dict(value)
                entry.setdefault("connector_id", connector_id)
                normalized_control[key] = entry
            else:
                normalized_control[key] = value
        defaults["control_map"] = normalized_control
    else:
        control = table.get("control", {})
        if isinstance(control, dict):
            derived_controls: Dict[str, Any] = {}
            if "power_limit" in control and register_like(control["power_limit"]):
                derived_controls["power_limit"] = control["power_limit"]
            if "power_absolute" in control and register_like(control["power_absolute"]):
                base = {
                    **control["power_absolute"],
                    "builder": "xj_power_absolute",
                    "connector_id": connector_id,
                    "control_type": 0x02,
                    "register_count": 12,
                }
                derived_controls["power_limit"] = base
                derived_controls["stop_charging"] = {**base, "fixed_value": 0}
                derived_controls["clear_fault"] = {**base, "fixed_value": 0}
                derived_controls["emergency_stop"] = {**base, "fixed_value": 0xFFFFFFFF}
            if derived_controls:
                defaults["control_map"] = derived_controls

    connector_status_map = table.get("connector_status_map")
    if isinstance(connector_status_map, dict):
        defaults["status_map"] = dict(connector_status_map)

    connector_mode_map = table.get("connector_mode_map")
    if isinstance(connector_mode_map, dict):
        defaults["mode_map"] = dict(connector_mode_map)

    return defaults
