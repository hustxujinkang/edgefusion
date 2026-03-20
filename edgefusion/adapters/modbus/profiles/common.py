from typing import Any, Dict


def reg(addr: int, reg_type: str = "u16", scale: float = 1, unit: str = "") -> Dict[str, Any]:
    return {"addr": addr, "type": reg_type, "scale": scale, "unit": unit}


def copy_map(mapping: Dict[str, Any] | None) -> Dict[str, Any]:
    if not isinstance(mapping, dict):
        return {}
    return {key: value for key, value in mapping.items()}


def register_like(mapping: Any) -> bool:
    return isinstance(mapping, dict) and any(key in mapping for key in ("addr", "address", "register"))


def get_nested_registers(table: Dict[str, Any], key: str) -> Dict[str, Any]:
    registers = table.get("registers", {})
    section = registers.get(key, {})
    if isinstance(section, dict):
        return section
    return {}
