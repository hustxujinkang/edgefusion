# 设备型号点表配置
# 定义不同型号设备的语义字段到协议寄存器的映射

from typing import Any, Dict


def _reg(addr: int, reg_type: str = "u16", scale: float = 1, unit: str = "") -> Dict[str, Any]:
    return {"addr": addr, "type": reg_type, "scale": scale, "unit": unit}


POINT_TABLES = {
    "generic_grid_meter": {
        "name": "通用总表",
        "manufacturer": "Generic",
        "device_type": "grid_meter",
        "status_map": {
            0: "offline",
            1: "online",
            2: "fault",
        },
        "telemetry": {
            "power": _reg(50001, "i32", 1, "W"),
            "status": _reg(50002, "u16", 1, ""),
        },
    },
    "generic_pv": {
        "name": "通用光伏逆变器",
        "manufacturer": "Generic",
        "device_type": "pv",
        "status_map": {
            0: "offline",
            1: "online",
            2: "fault",
        },
        "telemetry": {
            "power": _reg(51001, "i32", 1, "W"),
            "energy": _reg(51002, "u32", 0.1, "kWh"),
            "voltage": _reg(51003, "u16", 0.1, "V"),
            "current": _reg(51004, "u16", 0.1, "A"),
            "status": _reg(51005, "u16", 1, ""),
            "power_limit": _reg(51006, "u16", 1, "W"),
            "min_power_limit": _reg(51007, "u16", 1, "W"),
        },
        "control": {
            "power_limit": _reg(41001, "u16", 1, "W"),
        },
    },
    "generic_storage": {
        "name": "通用储能",
        "manufacturer": "Generic",
        "device_type": "energy_storage",
        "mode_map": {
            0: "idle",
            1: "charge",
            2: "discharge",
            3: "auto",
        },
        "telemetry": {
            "soc": _reg(52001, "u16", 1, "%"),
            "power": _reg(52002, "i32", 1, "W"),
            "voltage": _reg(52003, "u16", 0.1, "V"),
            "current": _reg(52004, "i16", 0.1, "A"),
            "mode": _reg(52005, "u16", 1, ""),
            "max_charge_power": _reg(52006, "u16", 1, "W"),
            "max_discharge_power": _reg(52007, "u16", 1, "W"),
        },
        "control": {
            "mode": _reg(42001, "u16", 1, ""),
            "charge_power": _reg(42002, "u16", 1, "W"),
            "discharge_power": _reg(42003, "u16", 1, "W"),
        },
    },
    "generic_charger": {
        "name": "通用充电桩",
        "manufacturer": "Generic",
        "device_type": "charging_station",
        "connector_count": 1,
        "connector_status_map": {
            0: "idle",
            1: "charging",
            2: "fault",
        },
        "connector_telemetry": {
            "voltage": _reg(0, "u16", 0.1, "V"),
            "current": _reg(1, "u16", 0.01, "A"),
            "power": _reg(2, "u16", 1, "W"),
            "energy": _reg(3, "u16", 0.01, "kWh"),
            "temperature": _reg(4, "u16", 0.1, "°C"),
            "status": _reg(5, "u16", 1, ""),
        },
        "connector_control": {
            "start_charging": {"addr": 5, "fixed_value": 1},
            "stop_charging": {"addr": 5, "fixed_value": 0},
            "clear_fault": {"addr": 5, "fixed_value": 0},
            "emergency_stop": {"addr": 5, "fixed_value": 2},
        },
    },
    "xj_dc_120kw": {
        "name": "许继 120kW 直流充电桩",
        "manufacturer": "许继",
        "device_type": "charging_station",
        "max_power": 120,
        "max_guns": 2,
        "connector_status_map": {
            0: "idle",
            1: "idle",
            2: "idle",
            3: "charging",
            4: "fault",
            5: "fault",
        },
        "registers": {
            "pile": {
                "gun_count": _reg(0x1000, "u16", 1, "个"),
                "max_power": _reg(0x1001, "u16", 1, "kW"),
            },
            "gun1": {
                "state": _reg(0x2000, "u16", 1, ""),
                "mode": _reg(0x2001, "u16", 1, ""),
                "alarm": _reg(0x2002, "u32", 1, ""),
                "fault": _reg(0x2004, "u32", 1, ""),
                "meter_reading": _reg(0x2006, "u32", 0.001, "kWh"),
                "amount": _reg(0x2008, "u32", 0.01, "元"),
                "energy": _reg(0x200A, "u32", 0.001, "kWh"),
                "duration": _reg(0x200C, "u32", 1, "秒"),
                "power": _reg(0x200E, "u32", 0.001, "kW"),
                "voltage": _reg(0x2010, "u16", 0.1, "V"),
                "current": _reg(0x2011, "u16", 0.01, "A"),
                "soc": _reg(0x2012, "u16", 1, "%"),
                "temperature": _reg(0x2013, "u16", 1, "°C"),
            },
            "gun2": {
                "state": _reg(0x2100, "u16", 1, ""),
                "mode": _reg(0x2101, "u16", 1, ""),
                "alarm": _reg(0x2102, "u32", 1, ""),
                "fault": _reg(0x2104, "u32", 1, ""),
                "meter_reading": _reg(0x2106, "u32", 0.001, "kWh"),
                "amount": _reg(0x2108, "u32", 0.01, "元"),
                "energy": _reg(0x210A, "u32", 0.001, "kWh"),
                "duration": _reg(0x210C, "u32", 1, "秒"),
                "power": _reg(0x210E, "u32", 0.001, "kW"),
                "voltage": _reg(0x2110, "u16", 0.1, "V"),
                "current": _reg(0x2111, "u16", 0.01, "A"),
                "soc": _reg(0x2112, "u16", 1, "%"),
                "temperature": _reg(0x2113, "u16", 1, "°C"),
            },
        },
        "control": {
            "power_absolute": {"addr": 0x4000, "cmd": "write_registers"},
            "power_percentage": {"addr": 0x4000, "cmd": "write_registers"},
        },
    },
    "xj_dc_240kw": {
        "name": "许继 240kW 直流充电桩",
        "manufacturer": "许继",
        "device_type": "charging_station",
        "max_power": 240,
        "max_guns": 2,
        "connector_status_map": {
            0: "idle",
            1: "idle",
            2: "idle",
            3: "charging",
            4: "fault",
            5: "fault",
        },
        "registers": {
            "pile": {
                "gun_count": _reg(0x1000, "u16", 1, "个"),
                "max_power": _reg(0x1001, "u16", 1, "kW"),
            },
            "gun1": {
                "state": _reg(0x2000, "u16", 1, ""),
                "mode": _reg(0x2001, "u16", 1, ""),
                "voltage": _reg(0x2010, "u16", 0.1, "V"),
                "current": _reg(0x2011, "u16", 0.01, "A"),
                "power": _reg(0x200E, "u32", 0.001, "kW"),
                "soc": _reg(0x2012, "u16", 1, "%"),
                "temperature": _reg(0x2013, "u16", 1, "°C"),
            },
            "gun2": {
                "state": _reg(0x2100, "u16", 1, ""),
                "mode": _reg(0x2101, "u16", 1, ""),
                "voltage": _reg(0x2110, "u16", 0.1, "V"),
                "current": _reg(0x2111, "u16", 0.01, "A"),
                "power": _reg(0x210E, "u32", 0.001, "kW"),
                "soc": _reg(0x2112, "u16", 1, "%"),
                "temperature": _reg(0x2113, "u16", 1, "°C"),
            },
        },
        "control": {
            "power_absolute": {"addr": 0x4000, "cmd": "write_registers"},
        },
    },
}


def _copy_map(mapping: Dict[str, Any] | None) -> Dict[str, Any]:
    if not isinstance(mapping, dict):
        return {}
    return {key: value for key, value in mapping.items()}


def _register_like(mapping: Any) -> bool:
    return isinstance(mapping, dict) and any(key in mapping for key in ("addr", "address", "register"))


def _get_nested_registers(table: Dict[str, Any], key: str) -> Dict[str, Any]:
    registers = table.get("registers", {})
    section = registers.get(key, {})
    if isinstance(section, dict):
        return section
    return {}


def get_point_table(model: str, fallback_model: str | None = "generic_charger") -> dict:
    if model in POINT_TABLES:
        return POINT_TABLES[model]
    if fallback_model:
        return POINT_TABLES.get(fallback_model, {})
    return {}


def get_gun_registers(model: str, gun_id: int = 1) -> dict:
    table = get_point_table(model)
    registers = table.get("registers", {})
    gun_key = f"gun{gun_id}"
    gun_registers = registers.get(gun_key, {})
    if isinstance(gun_registers, dict) and gun_registers:
        return gun_registers
    return get_charger_connector_telemetry_map(model, gun_id)


def get_charger_connector_count(model: str | None) -> int | None:
    if not model:
        return None
    table = get_point_table(model, fallback_model=None)
    if not table:
        return None
    raw_count = table.get("connector_count", table.get("max_guns"))
    try:
        if raw_count is None:
            return None
        return max(1, int(raw_count))
    except (TypeError, ValueError):
        return None


def get_charger_connector_telemetry_map(model: str | None, connector_id: int) -> Dict[str, Any]:
    if not model:
        return {}

    table = get_point_table(model, fallback_model=None)
    if not table:
        return {}

    connector_telemetry = table.get("connector_telemetry")
    if isinstance(connector_telemetry, dict):
        return _copy_map(connector_telemetry)

    gun_registers = _get_nested_registers(table, f"gun{connector_id}")
    if not gun_registers:
        return {}

    telemetry = {key: value for key, value in gun_registers.items() if _register_like(value)}
    if "state" in telemetry and "status" not in telemetry:
        telemetry["status"] = telemetry["state"]
    return telemetry


def get_charger_connector_control_map(model: str | None, connector_id: int) -> Dict[str, Any]:
    if not model:
        return {}

    table = get_point_table(model, fallback_model=None)
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
    if "power_limit" in control and _register_like(control["power_limit"]):
        derived_controls["power_limit"] = control["power_limit"]
    if "power_absolute" in control and _register_like(control["power_absolute"]):
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


def get_charger_connector_status_map(model: str | None) -> Dict[Any, Any]:
    if not model:
        return {}
    table = get_point_table(model, fallback_model=None)
    mapping = table.get("connector_status_map")
    if isinstance(mapping, dict):
        return dict(mapping)
    return {}


def get_charger_connector_mode_map(model: str | None) -> Dict[Any, Any]:
    if not model:
        return {}
    table = get_point_table(model, fallback_model=None)
    mapping = table.get("connector_mode_map")
    if isinstance(mapping, dict):
        return dict(mapping)
    return {}


def get_device_default_maps(device_info: Dict[str, Any]) -> Dict[str, Any]:
    model = device_info.get("model")
    if not model:
        return {}

    table = get_point_table(str(model), fallback_model=None)
    if not table:
        return {}

    device_type = device_info.get("type")
    defaults: Dict[str, Any] = {}

    if device_type == "charging_station":
        pile_registers = _get_nested_registers(table, "pile")
        if pile_registers:
            defaults["telemetry_map"] = _copy_map(pile_registers)
        connector_count = get_charger_connector_count(str(model))
        if connector_count is not None:
            defaults["connector_count"] = connector_count
        return defaults

    telemetry = table.get("telemetry")
    if isinstance(telemetry, dict):
        defaults["telemetry_map"] = _copy_map(telemetry)

    control = table.get("control")
    if isinstance(control, dict):
        defaults["control_map"] = {
            key: value
            for key, value in control.items()
            if _register_like(value)
        }

    status_map = table.get("status_map")
    if isinstance(status_map, dict):
        defaults["status_map"] = dict(status_map)

    mode_map = table.get("mode_map")
    if isinstance(mode_map, dict):
        defaults["mode_map"] = dict(mode_map)

    return defaults
