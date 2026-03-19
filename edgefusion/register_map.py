from typing import Any, Dict


def _extract_read_register(raw_mapping: Any) -> Any:
    if isinstance(raw_mapping, dict):
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
        return _extract_read_register(raw_mapping)
    return _extract_read_register(raw_mapping)


def _resolve_from_keys(device_info: Dict[str, Any], register: str, keys: tuple[str, ...], *, write: bool = False) -> Any:
    for key in keys:
        mapping = device_info.get(key)
        if isinstance(mapping, dict) and register in mapping:
            if write:
                return _extract_write_register(mapping[register])
            return _extract_read_register(mapping[register])
    return register


def resolve_read_register(device_info: Dict[str, Any], register: str) -> Any:
    return _resolve_from_keys(device_info, register, ("telemetry_map", "read_map", "register_map"))


def resolve_write_register(device_info: Dict[str, Any], register: str) -> Any:
    return _resolve_from_keys(
        device_info,
        register,
        ("control_map", "write_map", "register_map"),
        write=True,
    )
