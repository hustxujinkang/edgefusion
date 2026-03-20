from .profiles import (
    MODBUS_POINT_TABLES,
    get_modbus_charger_connector_control_map,
    get_modbus_charger_connector_count,
    get_modbus_charger_connector_mode_map,
    get_modbus_charger_connector_status_map,
    get_modbus_charger_connector_telemetry_map,
    get_modbus_device_default_maps,
    get_modbus_gun_registers,
    get_modbus_point_table,
)

get_point_table = get_modbus_point_table
get_gun_registers = get_modbus_gun_registers
get_charger_connector_count = get_modbus_charger_connector_count
get_charger_connector_telemetry_map = get_modbus_charger_connector_telemetry_map
get_charger_connector_control_map = get_modbus_charger_connector_control_map
get_charger_connector_status_map = get_modbus_charger_connector_status_map
get_charger_connector_mode_map = get_modbus_charger_connector_mode_map
get_device_default_maps = get_modbus_device_default_maps

__all__ = [
    "MODBUS_POINT_TABLES",
    "get_point_table",
    "get_gun_registers",
    "get_charger_connector_count",
    "get_charger_connector_telemetry_map",
    "get_charger_connector_control_map",
    "get_charger_connector_status_map",
    "get_charger_connector_mode_map",
    "get_device_default_maps",
    "get_modbus_charger_connector_control_map",
    "get_modbus_charger_connector_count",
    "get_modbus_charger_connector_mode_map",
    "get_modbus_charger_connector_status_map",
    "get_modbus_charger_connector_telemetry_map",
    "get_modbus_device_default_maps",
    "get_modbus_gun_registers",
    "get_modbus_point_table",
]
