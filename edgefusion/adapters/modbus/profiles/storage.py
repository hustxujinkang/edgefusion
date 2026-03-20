from .common import reg


STORAGE_POINT_TABLES = {
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
    }
}
