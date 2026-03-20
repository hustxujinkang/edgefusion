from typing import Any, Dict

from . import charger, grid_meter, pv, storage, vendors
from .charger import CHARGER_POINT_TABLES
from .common import copy_map, get_nested_registers, register_like
from .grid_meter import GRID_METER_POINT_TABLES
from .pv import PV_POINT_TABLES
from .storage import STORAGE_POINT_TABLES


MODBUS_POINT_TABLES = {
    **GRID_METER_POINT_TABLES,
    **PV_POINT_TABLES,
    **STORAGE_POINT_TABLES,
    **CHARGER_POINT_TABLES,
}


def resolve_modbus_model_key(
    model: str | None,
    *,
    vendor: str | None = None,
    device_type: str | None = None,
) -> str | None:
    if model and model in MODBUS_POINT_TABLES:
        return model
    return vendors.resolve_vendor_model(model, vendor=vendor, device_type=device_type)


def get_modbus_point_table(
    model: str | None,
    *,
    vendor: str | None = None,
    device_type: str | None = None,
    fallback_model: str | None = "generic_charger",
) -> dict:
    resolved_model = resolve_modbus_model_key(model, vendor=vendor, device_type=device_type)
    if resolved_model and resolved_model in MODBUS_POINT_TABLES:
        return MODBUS_POINT_TABLES[resolved_model]
    if fallback_model:
        return MODBUS_POINT_TABLES.get(fallback_model, {})
    return {}


def get_modbus_gun_registers(model: str, gun_id: int = 1) -> dict:
    table = get_modbus_point_table(model)
    registers = table.get("registers", {})
    gun_key = f"gun{gun_id}"
    gun_registers = registers.get(gun_key, {})
    if isinstance(gun_registers, dict) and gun_registers:
        return gun_registers
    return get_modbus_charger_connector_telemetry_map(model, gun_id)


def get_modbus_charger_connector_count(model: str | None) -> int | None:
    if not model:
        return None
    table = get_modbus_point_table(model, fallback_model=None)
    if not table:
        return None
    raw_count = table.get("connector_count", table.get("max_guns"))
    try:
        if raw_count is None:
            return None
        return max(1, int(raw_count))
    except (TypeError, ValueError):
        return None


def get_modbus_charger_connector_telemetry_map(model: str | None, connector_id: int) -> Dict[str, Any]:
    if not model:
        return {}

    table = get_modbus_point_table(model, fallback_model=None)
    if not table:
        return {}

    connector_telemetry = table.get("connector_telemetry")
    if isinstance(connector_telemetry, dict):
        return copy_map(connector_telemetry)

    gun_registers = get_nested_registers(table, f"gun{connector_id}")
    if not gun_registers:
        return {}

    telemetry = {key: value for key, value in gun_registers.items() if register_like(value)}
    if "state" in telemetry and "status" not in telemetry:
        telemetry["status"] = telemetry["state"]
    return telemetry


def get_modbus_charger_connector_control_map(model: str | None, connector_id: int) -> Dict[str, Any]:
    if not model:
        return {}

    table = get_modbus_point_table(model, fallback_model=None)
    if not table:
        return {}

    connector_control = table.get("connector_control")
    if isinstance(connector_control, dict):
        normalized: Dict[str, Any] = {}
        for key, value in connector_control.items():
            if isinstance(value, dict):
                entry = dict(value)
                entry.setdefault("connector_id", connector_id)
                normalized[key] = entry
            else:
                normalized[key] = value
        return normalized

    control = table.get("control", {})
    if not isinstance(control, dict):
        return {}

    derived_controls: Dict[str, Any] = {}
    if "power_limit" in control and register_like(control["power_limit"]):
        derived_controls["power_limit"] = control["power_limit"]
    if "power_absolute" in control and register_like(control["power_absolute"]):
        derived_controls["power_limit"] = {
            **control["power_absolute"],
            "builder": "xj_power_absolute",
            "connector_id": connector_id,
            "control_type": 0x02,
            "register_count": 12,
        }
        derived_controls["stop_charging"] = {
            **control["power_absolute"],
            "builder": "xj_power_absolute",
            "connector_id": connector_id,
            "control_type": 0x02,
            "register_count": 12,
            "fixed_value": 0,
        }
        derived_controls["clear_fault"] = {
            **control["power_absolute"],
            "builder": "xj_power_absolute",
            "connector_id": connector_id,
            "control_type": 0x02,
            "register_count": 12,
            "fixed_value": 0,
        }
        derived_controls["emergency_stop"] = {
            **control["power_absolute"],
            "builder": "xj_power_absolute",
            "connector_id": connector_id,
            "control_type": 0x02,
            "register_count": 12,
            "fixed_value": 0xFFFFFFFF,
        }
    return derived_controls


def get_modbus_charger_connector_status_map(model: str | None) -> Dict[Any, Any]:
    if not model:
        return {}
    table = get_modbus_point_table(model, fallback_model=None)
    mapping = table.get("connector_status_map")
    if isinstance(mapping, dict):
        return dict(mapping)
    return {}


def get_modbus_charger_connector_mode_map(model: str | None) -> Dict[Any, Any]:
    if not model:
        return {}
    table = get_modbus_point_table(model, fallback_model=None)
    mapping = table.get("connector_mode_map")
    if isinstance(mapping, dict):
        return dict(mapping)
    return {}


def get_modbus_device_default_maps(device_info: Dict[str, Any]) -> Dict[str, Any]:
    model = device_info.get("model")
    device_type = device_info.get("type")
    vendor = device_info.get("vendor") or device_info.get("manufacturer")

    table = get_modbus_point_table(
        str(model) if model is not None else None,
        vendor=str(vendor) if vendor is not None else None,
        device_type=str(device_type) if device_type is not None else None,
        fallback_model=None,
    )
    if not table:
        return {}

    defaults: Dict[str, Any] = {}

    if device_type == "charging_station":
        pile_registers = get_nested_registers(table, "pile")
        if pile_registers:
            defaults["telemetry_map"] = copy_map(pile_registers)
        connector_count = get_modbus_charger_connector_count(str(model))
        if connector_count is not None:
            defaults["connector_count"] = connector_count
        return defaults

    telemetry = table.get("telemetry")
    if isinstance(telemetry, dict):
        defaults["telemetry_map"] = copy_map(telemetry)

    control = table.get("control")
    if isinstance(control, dict):
        defaults["control_map"] = {
            key: value
            for key, value in control.items()
            if register_like(value)
        }

    status_map = table.get("status_map")
    if isinstance(status_map, dict):
        defaults["status_map"] = dict(status_map)

    mode_map = table.get("mode_map")
    if isinstance(mode_map, dict):
        defaults["mode_map"] = dict(mode_map)

    return defaults


__all__ = [
    "MODBUS_POINT_TABLES",
    "charger",
    "grid_meter",
    "pv",
    "storage",
    "vendors",
    "get_modbus_charger_connector_control_map",
    "get_modbus_charger_connector_count",
    "get_modbus_charger_connector_mode_map",
    "get_modbus_charger_connector_status_map",
    "get_modbus_charger_connector_telemetry_map",
    "get_modbus_device_default_maps",
    "get_modbus_gun_registers",
    "get_modbus_point_table",
    "resolve_modbus_model_key",
]
