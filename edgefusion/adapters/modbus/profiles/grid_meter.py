from .vendors.generic import GENERIC_POINT_TABLES


GRID_METER_POINT_TABLES = {
    key: value
    for key, value in GENERIC_POINT_TABLES.items()
    if value.get("device_type") == "grid_meter"
}
