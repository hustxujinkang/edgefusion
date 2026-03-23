from typing import Any, Dict


STATUS_ALIASES = {
    "available": "idle",
    "idle": "idle",
    "standby": "idle",
    "ready": "idle",
    "preparing": "idle",
    "complete": "idle",
    "charging": "charging",
    "running": "charging",
    "fault": "fault",
    "error": "fault",
    "alarm": "fault",
    "trip": "fault",
    "online": "online",
    "normal": "online",
    "offline": "offline",
    "disconnected": "offline",
}

MODE_ALIASES = {
    "charge": "charge",
    "charging": "charge",
    "discharge": "discharge",
    "discharging": "discharge",
    "idle": "idle",
    "standby": "idle",
    "stop": "idle",
    "auto": "auto",
    "automatic": "auto",
}


DEVICE_SEMANTIC_SCHEMAS = {
    "grid_meter": {
        "core_readable_fields": ("power", "status"),
        "optional_readable_fields": (),
        "core_writable_fields": (),
        "optional_writable_fields": (),
    },
    "pv": {
        "core_readable_fields": ("power", "status"),
        "optional_readable_fields": ("current", "energy", "min_power_limit", "power_limit", "voltage"),
        "core_writable_fields": ("power_limit",),
        "optional_writable_fields": (),
    },
    "energy_storage": {
        "core_readable_fields": ("mode", "power", "soc"),
        "optional_readable_fields": ("current", "max_charge_power", "max_discharge_power", "status", "voltage"),
        "core_writable_fields": ("charge_power", "discharge_power", "mode"),
        "optional_writable_fields": (),
    },
    "charging_station": {
        "core_readable_fields": (),
        "optional_readable_fields": ("connector_count", "gun_count", "status"),
        "core_writable_fields": (),
        "optional_writable_fields": (),
        "connector_child_type": "charging_connector",
    },
    "charging_connector": {
        "core_readable_fields": ("power", "status"),
        "optional_readable_fields": ("current", "energy", "max_power", "min_power", "power_limit", "temperature", "voltage"),
        "core_writable_fields": ("power_limit",),
        "optional_writable_fields": ("clear_fault", "emergency_stop", "start_charging", "stop_charging"),
    },
}


def get_device_semantic_schema(device_type: Any) -> Dict[str, Any]:
    schema = DEVICE_SEMANTIC_SCHEMAS.get(str(device_type or ""), {})
    payload = {
        "device_type": str(device_type or "unknown"),
        "core_readable_fields": sorted(schema.get("core_readable_fields", ())),
        "optional_readable_fields": sorted(schema.get("optional_readable_fields", ())),
        "core_writable_fields": sorted(schema.get("core_writable_fields", ())),
        "optional_writable_fields": sorted(schema.get("optional_writable_fields", ())),
    }
    connector_child_type = schema.get("connector_child_type")
    if connector_child_type:
        payload["connector_child_type"] = connector_child_type
    return payload


def describe_declared_fields(device_info: Dict[str, Any]) -> Dict[str, Any]:
    telemetry_map = device_info.get("telemetry_map")
    control_map = device_info.get("control_map")
    schema = get_device_semantic_schema(device_info.get("type"))

    readable_fields = sorted(telemetry_map.keys()) if isinstance(telemetry_map, dict) else []
    writable_fields = sorted(control_map.keys()) if isinstance(control_map, dict) else []

    known_readable_fields = set(schema["core_readable_fields"]) | set(schema["optional_readable_fields"])
    known_writable_fields = set(schema["core_writable_fields"]) | set(schema["optional_writable_fields"])

    return {
        "schema": schema,
        "unknown_readable_fields": sorted(field for field in readable_fields if field not in known_readable_fields),
        "unknown_writable_fields": sorted(field for field in writable_fields if field not in known_writable_fields),
    }


def build_device_capabilities(device_info: Dict[str, Any]) -> Dict[str, Any]:
    telemetry_map = device_info.get("telemetry_map")
    control_map = device_info.get("control_map")
    explicit_capabilities = device_info.get("capabilities")
    declared_fields = describe_declared_fields(device_info)

    readable_fields = sorted(telemetry_map.keys()) if isinstance(telemetry_map, dict) else []
    writable_fields = sorted(control_map.keys()) if isinstance(control_map, dict) else []
    declared = bool(readable_fields or writable_fields or isinstance(explicit_capabilities, dict))

    capabilities = {
        "declared": declared,
        "readable_fields": readable_fields,
        "writable_fields": writable_fields,
        "schema": declared_fields["schema"],
        "unknown_readable_fields": declared_fields["unknown_readable_fields"],
        "unknown_writable_fields": declared_fields["unknown_writable_fields"],
        "supports": {
            "power_limit_control": "power_limit" in writable_fields,
            "mode_control": "mode" in writable_fields,
            "charge_power_control": "charge_power" in writable_fields,
            "discharge_power_control": "discharge_power" in writable_fields,
            "start_charging_control": "start_charging" in writable_fields,
            "stop_charging_control": "stop_charging" in writable_fields,
            "clear_fault_control": "clear_fault" in writable_fields,
            "emergency_stop_control": "emergency_stop" in writable_fields,
        },
    }

    if isinstance(explicit_capabilities, dict):
        merged = dict(capabilities)
        merged.update({key: value for key, value in explicit_capabilities.items() if key != "supports"})
        supports = dict(capabilities["supports"])
        if isinstance(explicit_capabilities.get("supports"), dict):
            supports.update(explicit_capabilities["supports"])
        merged["supports"] = supports
        capabilities = merged

    return capabilities


def field_is_readable(device_info: Dict[str, Any], field: str) -> bool:
    capabilities = device_info.get("capabilities")
    if not isinstance(capabilities, dict):
        return True
    declared = capabilities.get("declared")
    if declared is None:
        declared = any(
            isinstance(capabilities.get(key), list) and capabilities.get(key)
            for key in ("readable_fields", "writable_fields")
        ) or isinstance(capabilities.get("supports"), dict)
    if not declared:
        return True
    readable_fields = capabilities.get("readable_fields")
    if not isinstance(readable_fields, list):
        return True
    return field in readable_fields


def field_is_writable(device_info: Dict[str, Any], field: str) -> bool:
    capabilities = device_info.get("capabilities")
    if not isinstance(capabilities, dict):
        return True
    declared = capabilities.get("declared")
    if declared is None:
        declared = any(
            isinstance(capabilities.get(key), list) and capabilities.get(key)
            for key in ("readable_fields", "writable_fields")
        ) or isinstance(capabilities.get("supports"), dict)
    if not declared:
        return True
    writable_fields = capabilities.get("writable_fields")
    if not isinstance(writable_fields, list):
        return True
    return field in writable_fields


def _resolve_enum_mapping(raw_value: Any, mapping: Dict[Any, Any]) -> Any:
    candidates = [raw_value]

    if isinstance(raw_value, str):
        candidates.append(raw_value.lower())
        try:
            candidates.append(int(raw_value))
        except (TypeError, ValueError):
            pass
    else:
        candidates.append(str(raw_value))
        candidates.append(str(raw_value).lower())

    for candidate in candidates:
        if candidate in mapping:
            return mapping[candidate]
    return raw_value


def normalize_runtime_value(device_info: Dict[str, Any], field: str, raw_value: Any) -> Any:
    if raw_value is None:
        return None

    if field == "status":
        status_map = device_info.get("status_map")
        if isinstance(status_map, dict):
            raw_value = _resolve_enum_mapping(raw_value, status_map)
        if isinstance(raw_value, str):
            return STATUS_ALIASES.get(raw_value.lower(), raw_value.lower())
        return raw_value

    if field == "mode":
        mode_map = device_info.get("mode_map")
        if isinstance(mode_map, dict):
            raw_value = _resolve_enum_mapping(raw_value, mode_map)
        if isinstance(raw_value, str):
            return MODE_ALIASES.get(raw_value.lower(), raw_value.lower())
        return raw_value

    return raw_value


def snapshot_supports_write(snapshot: Dict[str, Any], *fields: str) -> bool:
    capabilities = snapshot.get("capabilities")
    if not isinstance(capabilities, dict):
        return True
    declared = capabilities.get("declared")
    if declared is None:
        declared = any(
            isinstance(capabilities.get(key), list) and capabilities.get(key)
            for key in ("readable_fields", "writable_fields")
        ) or isinstance(capabilities.get("supports"), dict)
    if not declared:
        return True
    writable_fields = capabilities.get("writable_fields")
    if not isinstance(writable_fields, list):
        return True
    return all(field in writable_fields for field in fields)
