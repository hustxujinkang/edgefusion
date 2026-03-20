from edgefusion.adapters.device_profiles import (
    normalize_device_profile,
    resolve_protocol_read,
    resolve_protocol_write,
)
from edgefusion.point_tables import POINT_TABLES, get_device_default_maps


def test_modbus_profile_module_exposes_builtin_model_tables():
    from edgefusion.adapters.modbus.profiles import (
        MODBUS_POINT_TABLES,
        get_modbus_device_default_maps,
    )

    defaults = get_modbus_device_default_maps(
        {
            "device_id": "pv_1",
            "type": "pv",
            "model": "generic_pv",
        }
    )

    assert MODBUS_POINT_TABLES["generic_pv"]["device_type"] == "pv"
    assert defaults["telemetry_map"]["power"]["addr"] == 51001
    assert defaults["control_map"]["power_limit"]["addr"] == 41001


def test_point_tables_compatibility_facade_reexports_modbus_profiles():
    from edgefusion.adapters.modbus.profiles import (
        MODBUS_POINT_TABLES,
        get_modbus_device_default_maps,
    )

    device_info = {
        "device_id": "storage_1",
        "type": "energy_storage",
        "model": "generic_storage",
    }

    assert POINT_TABLES is MODBUS_POINT_TABLES
    assert get_device_default_maps(device_info) == get_modbus_device_default_maps(device_info)


def test_normalize_device_profile_merges_point_table_defaults():
    device = normalize_device_profile(
        {
            "device_id": "storage_1",
            "type": "energy_storage",
            "model": "generic_storage",
            "protocol": "modbus",
        }
    )

    assert device["source"] == "real"
    assert device["status"] == "online"
    assert resolve_protocol_read(device, "soc") == {
        "addr": 52001,
        "type": "u16",
        "scale": 1,
        "unit": "%",
    }
    assert resolve_protocol_write(device, "charge_power") == {
        "addr": 42002,
        "type": "u16",
        "scale": 1,
        "unit": "W",
    }


def test_normalize_device_profile_keeps_explicit_mapping_over_defaults():
    device = normalize_device_profile(
        {
            "device_id": "grid_1",
            "type": "grid_meter",
            "model": "generic_grid_meter",
            "protocol": "modbus",
            "telemetry_map": {
                "power": "39991",
            },
        }
    )

    assert resolve_protocol_read(device, "power") == "39991"
    assert resolve_protocol_read(device, "status") == {
        "addr": 50002,
        "type": "u16",
        "scale": 1,
        "unit": "",
    }


def test_normalize_device_profile_derives_capabilities_from_default_maps():
    device = normalize_device_profile(
        {
            "device_id": "charger_1",
            "type": "charging_connector",
            "protocol": "modbus",
            "telemetry_map": {"status": {"addr": 5}, "power": {"addr": 2}},
            "control_map": {"power_limit": {"addr": 41001}, "stop_charging": {"addr": 5, "fixed_value": 0}},
        }
    )

    assert device["capabilities"]["readable_fields"] == ["power", "status"]
    assert device["capabilities"]["writable_fields"] == ["power_limit", "stop_charging"]
    assert device["capabilities"]["supports"]["power_limit_control"] is True
    assert device["capabilities"]["supports"]["stop_charging_control"] is True
