from typing import Any, Dict


READ_MAPPING_KEY = "telemetry_map"
WRITE_MAPPING_KEY = "control_map"
LEGACY_READ_MAPPING_KEYS = ("read_map", "register_map")
LEGACY_WRITE_MAPPING_KEYS = ("write_map", "register_map")


def _extract_read_register(raw_mapping: Any) -> Any:
    if isinstance(raw_mapping, dict):
        if any(key in raw_mapping for key in ("register", "address", "addr")):
            return dict(raw_mapping)
        for key in ("register", "address", "addr"):
            if key in raw_mapping:
                value = raw_mapping[key]
                return str(value) if isinstance(value, int) else value
    if isinstance(raw_mapping, int):
        return str(raw_mapping)
    return raw_mapping


def _extract_write_register(raw_mapping: Any) -> Any:
    if isinstance(raw_mapping, dict):
        if "cmd" in raw_mapping or "builder" in raw_mapping:
            return dict(raw_mapping)
        if any(key in raw_mapping for key in ("register", "address", "addr")):
            return dict(raw_mapping)
        return _extract_read_register(raw_mapping)
    return _extract_read_register(raw_mapping)


def _resolve_from_mapping(device_info: Dict[str, Any], register: str, mapping_key: str, *, write: bool = False) -> Any:
    mapping = device_info.get(mapping_key)
    if isinstance(mapping, dict) and register in mapping:
        if write:
            return _extract_write_register(mapping[register])
        return _extract_read_register(mapping[register])
    return register


def _resolve_from_keys(device_info: Dict[str, Any], register: str, keys: tuple[str, ...], *, write: bool = False) -> Any:
    for key in keys:
        resolved = _resolve_from_mapping(device_info, register, key, write=write)
        if resolved != register:
            return resolved
    return register


def _merge_mapping(target: Dict[str, Any], source: Any) -> Dict[str, Any]:
    merged = dict(target)
    if isinstance(source, dict):
        for key, value in source.items():
            merged.setdefault(key, value)
    return merged


def normalize_mapping_aliases(device_info: Dict[str, Any]) -> Dict[str, Any]:
    normalized = dict(device_info)

    telemetry_map = normalized.get(READ_MAPPING_KEY)
    control_map = normalized.get(WRITE_MAPPING_KEY)

    normalized[READ_MAPPING_KEY] = _merge_mapping(
        telemetry_map if isinstance(telemetry_map, dict) else {},
        normalized.get("read_map"),
    )
    normalized[READ_MAPPING_KEY] = _merge_mapping(
        normalized[READ_MAPPING_KEY],
        normalized.get("register_map"),
    )

    normalized[WRITE_MAPPING_KEY] = _merge_mapping(
        control_map if isinstance(control_map, dict) else {},
        normalized.get("write_map"),
    )
    normalized[WRITE_MAPPING_KEY] = _merge_mapping(
        normalized[WRITE_MAPPING_KEY],
        normalized.get("register_map"),
    )

    if not normalized[READ_MAPPING_KEY]:
        normalized.pop(READ_MAPPING_KEY, None)
    if not normalized[WRITE_MAPPING_KEY]:
        normalized.pop(WRITE_MAPPING_KEY, None)

    return normalized


def resolve_read_definition(device_info: Dict[str, Any], register: str) -> Any:
    return _resolve_from_mapping(device_info, register, READ_MAPPING_KEY)


def resolve_write_definition(device_info: Dict[str, Any], register: str) -> Any:
    return _resolve_from_mapping(device_info, register, WRITE_MAPPING_KEY, write=True)


def resolve_read_register(device_info: Dict[str, Any], register: str) -> Any:
    resolved = resolve_read_definition(device_info, register)
    if resolved != register:
        return resolved
    return _resolve_from_keys(device_info, register, LEGACY_READ_MAPPING_KEYS)


def resolve_write_register(device_info: Dict[str, Any], register: str) -> Any:
    resolved = resolve_write_definition(device_info, register)
    if resolved != register:
        return resolved
    return _resolve_from_keys(device_info, register, LEGACY_WRITE_MAPPING_KEYS, write=True)


__all__ = [
    "LEGACY_READ_MAPPING_KEYS",
    "LEGACY_WRITE_MAPPING_KEYS",
    "READ_MAPPING_KEY",
    "WRITE_MAPPING_KEY",
    "normalize_mapping_aliases",
    "resolve_read_definition",
    "resolve_read_register",
    "resolve_write_definition",
    "resolve_write_register",
]
