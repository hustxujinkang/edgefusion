from typing import Any, Dict

from ..charger_layout import normalize_charger_pile
from ..device_semantics import build_device_capabilities, normalize_runtime_value
from ..point_tables import get_device_default_maps
from ..register_map import resolve_read_register, resolve_write_register


def normalize_device_profile(device_info: Dict[str, Any]) -> Dict[str, Any]:
    normalized = dict(device_info)
    default_maps = get_device_default_maps(normalized)
    for key, value in default_maps.items():
        if key in {"telemetry_map", "control_map"} and isinstance(value, dict):
            merged = dict(value)
            if isinstance(normalized.get(key), dict):
                merged.update(normalized[key])
            normalized[key] = merged
        else:
            normalized.setdefault(key, value)

    protocol_name = normalized.get("protocol")
    if normalized.get("source") not in {"real", "simulated"}:
        normalized["source"] = "simulated" if protocol_name == "simulation" else "real"

    raw_status = str(normalized.get("status", "online")).lower()
    normalized["status"] = "offline" if raw_status == "offline" else "online"
    normalized["capabilities"] = build_device_capabilities(normalized)
    return normalize_charger_pile(normalized)


def resolve_protocol_read(device_info: Dict[str, Any], field: str) -> Any:
    return resolve_read_register(device_info, field)


def resolve_protocol_write(device_info: Dict[str, Any], field: str) -> Any:
    return resolve_write_register(device_info, field)


def normalize_field_value(device_info: Dict[str, Any], field: str, raw_value: Any) -> Any:
    return normalize_runtime_value(device_info, field, raw_value)
