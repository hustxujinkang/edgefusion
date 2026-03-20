from .common import reg


GRID_METER_POINT_TABLES = {
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
            "power": reg(50001, "i32", 1, "W"),
            "status": reg(50002, "u16", 1, ""),
        },
    }
}
