from typing import Any, Dict, List
from .device_semantics import build_device_capabilities
from .adapters.modbus import (
    get_charger_connector_control_map,
    get_charger_connector_count,
    get_charger_connector_mode_map,
    get_charger_connector_status_map,
    get_charger_connector_telemetry_map,
)


CHARGER_PILE_TYPE = "charging_station"
CHARGER_CONNECTOR_TYPE = "charging_connector"


def build_connector_device_id(pile_id: str, connector_id: int) -> str:
    return f"{pile_id}:{connector_id}"


def is_charger_pile(device_info: Dict[str, Any] | None) -> bool:
    if not device_info:
        return False
    return device_info.get("type") == CHARGER_PILE_TYPE


def _normalize_connector_count(device_info: Dict[str, Any]) -> int:
    model_count = get_charger_connector_count(device_info.get("model"))
    raw = device_info.get("connector_count", device_info.get("gun_count", model_count or 1))
    try:
        return max(1, int(raw))
    except (TypeError, ValueError):
        return 1


def build_connector_views(device_info: Dict[str, Any]) -> List[Dict[str, Any]]:
    if not is_charger_pile(device_info):
        return []

    pile_id = str(device_info.get("device_id", ""))
    connector_defs = device_info.get("connectors") or []
    connector_views: List[Dict[str, Any]] = []

    if not connector_defs:
        for connector_index in range(1, _normalize_connector_count(device_info) + 1):
            connector_defs.append(
                {
                    "connector_id": connector_index,
                    "device_id": build_connector_device_id(pile_id, connector_index),
                    "io_device_id": pile_id,
                }
            )

    for fallback_index, connector in enumerate(connector_defs, start=1):
        connector_id = int(connector.get("connector_id", fallback_index))
        connector_device_id = connector.get("device_id", build_connector_device_id(pile_id, connector_id))
        default_telemetry_map = get_charger_connector_telemetry_map(device_info.get("model"), connector_id)
        default_control_map = get_charger_connector_control_map(device_info.get("model"), connector_id)
        default_status_map = get_charger_connector_status_map(device_info.get("model"))
        default_mode_map = get_charger_connector_mode_map(device_info.get("model"))
        explicit_capabilities = connector.get("capabilities")
        connector_view = dict(device_info)
        connector_view.pop("capabilities", None)
        if default_telemetry_map:
            connector_view["telemetry_map"] = default_telemetry_map
        if default_control_map:
            connector_view["control_map"] = default_control_map
        if default_status_map:
            connector_view["status_map"] = default_status_map
        if default_mode_map:
            connector_view["mode_map"] = default_mode_map
        connector_view.update(connector)
        if default_telemetry_map and isinstance(connector.get("telemetry_map"), dict):
            merged_telemetry_map = dict(default_telemetry_map)
            merged_telemetry_map.update(connector["telemetry_map"])
            connector_view["telemetry_map"] = merged_telemetry_map
        if default_control_map and isinstance(connector.get("control_map"), dict):
            merged_control_map = dict(default_control_map)
            merged_control_map.update(connector["control_map"])
            connector_view["control_map"] = merged_control_map
        connector_view["device_id"] = connector_device_id
        connector_view["type"] = CHARGER_CONNECTOR_TYPE
        connector_view["pile_id"] = pile_id
        connector_view["connector_id"] = connector_id
        connector_view.setdefault("io_device_id", pile_id)
        if explicit_capabilities is not None:
            connector_view["capabilities"] = explicit_capabilities
        connector_view["capabilities"] = build_device_capabilities(connector_view)
        connector_views.append(connector_view)

    return connector_views


def normalize_charger_pile(device_info: Dict[str, Any]) -> Dict[str, Any]:
    normalized = dict(device_info)
    if not is_charger_pile(normalized):
        return normalized

    connector_views = build_connector_views(normalized)
    normalized["connector_count"] = len(connector_views) or 1
    normalized["connectors"] = [
        {
            **connector,
            "device_id": connector["device_id"],
            "connector_id": connector["connector_id"],
            "io_device_id": connector.get("io_device_id", normalized.get("device_id")),
        }
        for connector in connector_views
    ]
    return normalized
