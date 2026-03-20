from .vendors.generic import GENERIC_POINT_TABLES


STORAGE_POINT_TABLES = {
    key: value
    for key, value in GENERIC_POINT_TABLES.items()
    if value.get("device_type") == "energy_storage"
}
