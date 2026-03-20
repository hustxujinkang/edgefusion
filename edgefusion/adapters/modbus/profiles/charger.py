from .vendors.generic import GENERIC_POINT_TABLES
from .vendors.xj import XJ_POINT_TABLES


CHARGER_POINT_TABLES = {
    key: value
    for key, value in {
        **GENERIC_POINT_TABLES,
        **XJ_POINT_TABLES,
    }.items()
    if value.get("device_type") == "charging_station"
}
