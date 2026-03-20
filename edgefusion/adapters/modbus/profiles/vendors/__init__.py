from . import generic, xj
from .generic import GENERIC_POINT_TABLES
from .xj import XJ_POINT_TABLES

VENDOR_POINT_TABLES = {
    "generic": GENERIC_POINT_TABLES,
    "xj": XJ_POINT_TABLES,
}


def get_vendor_point_tables(vendor: str) -> dict:
    return VENDOR_POINT_TABLES.get(vendor, {})


def get_vendor_point_tables_for_device_type(device_type: str) -> dict:
    return {
        key: value
        for tables in VENDOR_POINT_TABLES.values()
        for key, value in tables.items()
        if value.get("device_type") == device_type
    }


__all__ = [
    "generic",
    "xj",
    "GENERIC_POINT_TABLES",
    "XJ_POINT_TABLES",
    "VENDOR_POINT_TABLES",
    "get_vendor_point_tables",
    "get_vendor_point_tables_for_device_type",
]
