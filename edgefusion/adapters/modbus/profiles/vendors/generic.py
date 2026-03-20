from ..common import reg


GENERIC_POINT_TABLES = {
    "generic_grid_meter": {
        "name": "通用总表",
        "manufacturer": "Generic",
        "model_aliases": ["generic grid meter", "通用总表"],
        "device_type": "grid_meter",
        "status_map": {
            0: "offline",
            1: "online",
            2: "fault",
        },
        "telemetry": {
            "power": reg(50001, "i32", 1, "W"),
            "status": reg(50002, "u16", 1, ""),
        },
    },
    "generic_pv": {
        "name": "通用光伏逆变器",
        "manufacturer": "Generic",
        "model_aliases": ["generic pv", "generic inverter", "通用光伏", "通用光伏逆变器"],
        "device_type": "pv",
        "status_map": {
            0: "offline",
            1: "online",
            2: "fault",
        },
        "telemetry": {
            "power": reg(51001, "i32", 1, "W"),
            "energy": reg(51002, "u32", 0.1, "kWh"),
            "voltage": reg(51003, "u16", 0.1, "V"),
            "current": reg(51004, "u16", 0.1, "A"),
            "status": reg(51005, "u16", 1, ""),
            "power_limit": reg(51006, "u16", 1, "W"),
            "min_power_limit": reg(51007, "u16", 1, "W"),
        },
        "control": {
            "power_limit": reg(41001, "u16", 1, "W"),
        },
    },
    "generic_storage": {
        "name": "通用储能",
        "manufacturer": "Generic",
        "model_aliases": ["generic storage", "generic ess", "通用储能"],
        "device_type": "energy_storage",
        "mode_map": {
            0: "idle",
            1: "charge",
            2: "discharge",
            3: "auto",
        },
        "telemetry": {
            "soc": reg(52001, "u16", 1, "%"),
            "power": reg(52002, "i32", 1, "W"),
            "voltage": reg(52003, "u16", 0.1, "V"),
            "current": reg(52004, "i16", 0.1, "A"),
            "mode": reg(52005, "u16", 1, ""),
            "max_charge_power": reg(52006, "u16", 1, "W"),
            "max_discharge_power": reg(52007, "u16", 1, "W"),
        },
        "control": {
            "mode": reg(42001, "u16", 1, ""),
            "charge_power": reg(42002, "u16", 1, "W"),
            "discharge_power": reg(42003, "u16", 1, "W"),
        },
    },
    "generic_charger": {
        "name": "通用充电桩",
        "manufacturer": "Generic",
        "model_aliases": ["generic charger", "通用充电桩"],
        "device_type": "charging_station",
        "connector_count": 1,
        "connector_status_map": {
            0: "idle",
            1: "charging",
            2: "fault",
        },
        "connector_telemetry": {
            "voltage": reg(0, "u16", 0.1, "V"),
            "current": reg(1, "u16", 0.01, "A"),
            "power": reg(2, "u16", 1, "W"),
            "energy": reg(3, "u16", 0.01, "kWh"),
            "temperature": reg(4, "u16", 0.1, "°C"),
            "status": reg(5, "u16", 1, ""),
        },
        "connector_control": {
            "start_charging": {"addr": 5, "fixed_value": 1},
            "stop_charging": {"addr": 5, "fixed_value": 0},
            "clear_fault": {"addr": 5, "fixed_value": 0},
            "emergency_stop": {"addr": 5, "fixed_value": 2},
        },
    },
}


GENERIC_VENDOR_PROFILE = {
    "vendor": "generic",
    "aliases": ["generic", "通用"],
    "default_models": {
        "grid_meter": "generic_grid_meter",
        "pv": "generic_pv",
        "energy_storage": "generic_storage",
        "charging_station": "generic_charger",
    },
    "tables": GENERIC_POINT_TABLES,
}
