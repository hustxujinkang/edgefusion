from __future__ import annotations

from typing import Any, Dict, List, Optional

from .modbus.profiles import get_modbus_charger_connector_telemetry_map, get_modbus_point_table, vendors
from .modbus.profiles.common import get_nested_registers, register_like


DEVICE_TYPE_ORDER = [
    "grid_meter",
    "pv",
    "energy_storage",
    "charging_station",
]

DEVICE_TYPE_LABELS = {
    "grid_meter": "总表",
    "pv": "光伏逆变器",
    "energy_storage": "储能系统",
    "charging_station": "充电桩",
}


def _copy_register_definition(register: Any) -> Optional[Dict[str, Any]]:
    if not register_like(register):
        return None
    return dict(register)


def _first_register(mapping: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(mapping, dict):
        return None
    for value in mapping.values():
        copied = _copy_register_definition(value)
        if copied:
            return copied
    return None


def _resolve_vendor_label(vendor_key: str, profile: Dict[str, Any], vendor_tables: Dict[str, Any]) -> str:
    for table in vendor_tables.values():
        manufacturer = table.get("manufacturer")
        if manufacturer:
            return str(manufacturer)

    for alias in profile.get("aliases", []):
        normalized = str(alias).strip()
        if normalized and normalized.lower() != vendor_key.lower():
            return normalized

    return vendor_key


def _resolve_connector_count(table: Dict[str, Any]) -> int | None:
    raw = table.get("connector_count", table.get("max_guns"))
    try:
        if raw is None:
            return None
        return max(1, int(raw))
    except (TypeError, ValueError):
        return None


def get_modbus_device_model_catalog() -> Dict[str, Any]:
    device_types: List[Dict[str, Any]] = []

    for device_type in DEVICE_TYPE_ORDER:
        vendors_for_type: List[Dict[str, Any]] = []

        for vendor_key, profile in vendors.VENDOR_PROFILES.items():
            vendor_tables = profile.get("tables", {})
            models: List[Dict[str, Any]] = []
            default_model = profile.get("default_models", {}).get(device_type)

            for model_key, table in vendor_tables.items():
                if table.get("device_type") != device_type:
                    continue

                models.append(
                    {
                        "key": model_key,
                        "label": str(table.get("name", model_key)),
                        "manufacturer": str(table.get("manufacturer", vendor_key)),
                        "aliases": list(table.get("model_aliases", [])),
                        "default": model_key == default_model,
                        "connector_count": _resolve_connector_count(table),
                    }
                )

            if not models:
                continue

            models.sort(key=lambda item: (not item["default"], item["label"]))
            vendors_for_type.append(
                {
                    "key": vendor_key,
                    "label": _resolve_vendor_label(vendor_key, profile, vendor_tables),
                    "models": models,
                }
            )

        if not vendors_for_type:
            continue

        vendors_for_type.sort(key=lambda item: item["label"])
        device_types.append(
            {
                "key": device_type,
                "label": DEVICE_TYPE_LABELS.get(device_type, device_type),
                "vendors": vendors_for_type,
            }
        )

    return {
        "protocol": "modbus",
        "device_types": device_types,
    }


def get_modbus_model_probe_register(
    *,
    device_type: str | None,
    model: str | None,
    vendor: str | None = None,
) -> Optional[Dict[str, Any]]:
    if not model:
        return None

    table = get_modbus_point_table(model, vendor=vendor, device_type=device_type, fallback_model=None)
    if not table:
        return None

    if device_type == "charging_station":
        probe = _first_register(get_nested_registers(table, "pile"))
        if probe:
            return probe

        probe = _first_register(table.get("connector_telemetry"))
        if probe:
            return probe

        probe = _first_register(get_modbus_charger_connector_telemetry_map(model, 1))
        if probe:
            return probe

    return _first_register(table.get("telemetry"))


__all__ = [
    "DEVICE_TYPE_LABELS",
    "DEVICE_TYPE_ORDER",
    "get_modbus_device_model_catalog",
    "get_modbus_model_probe_register",
]
