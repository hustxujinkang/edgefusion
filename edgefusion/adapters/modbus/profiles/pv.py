from .common import reg


PV_POINT_TABLES = {
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
    }
}
