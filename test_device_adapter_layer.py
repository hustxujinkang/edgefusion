from edgefusion.adapters.device_profiles import (
    normalize_device_profile,
    resolve_protocol_read,
    resolve_protocol_write,
)
from edgefusion.point_tables import POINT_TABLES, get_device_default_maps
from edgefusion.register_map import (
    resolve_read_definition,
    resolve_read_register,
    resolve_write_definition,
    resolve_write_register,
)


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


def test_modbus_profile_package_exposes_device_family_submodules():
    from edgefusion.adapters.modbus.profiles import charger, grid_meter, pv, storage

    assert "generic_grid_meter" in grid_meter.GRID_METER_POINT_TABLES
    assert "generic_pv" in pv.PV_POINT_TABLES
    assert "generic_storage" in storage.STORAGE_POINT_TABLES
    assert "xj_dc_120kw" in charger.CHARGER_POINT_TABLES


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


def test_register_map_primary_api_reads_from_explicit_semantic_maps_only():
    device_info = {
        "telemetry_map": {"power": {"addr": 30001, "type": "i32"}},
        "read_map": {"power": {"addr": 39991, "type": "u16"}},
        "control_map": {"power_limit": {"addr": 41001, "type": "u16"}},
        "write_map": {"power_limit": {"addr": 49991, "type": "u16"}},
        "register_map": {
            "power": {"addr": 39992, "type": "u16"},
            "power_limit": {"addr": 49992, "type": "u16"},
        },
    }

    assert resolve_read_definition(device_info, "power") == {"addr": 30001, "type": "i32"}
    assert resolve_write_definition(device_info, "power_limit") == {"addr": 41001, "type": "u16"}


def test_register_map_compatibility_wrappers_keep_legacy_fallbacks():
    device_info = {
        "read_map": {"power": {"addr": 39991, "type": "u16"}},
        "write_map": {"power_limit": {"addr": 49991, "type": "u16"}},
    }

    assert resolve_read_register(device_info, "power") == {"addr": 39991, "type": "u16"}
    assert resolve_write_register(device_info, "power_limit") == {"addr": 49991, "type": "u16"}


def test_normalize_device_profile_promotes_legacy_register_maps_into_primary_maps():
    device = normalize_device_profile(
        {
            "device_id": "legacy_storage",
            "type": "energy_storage",
            "protocol": "modbus",
            "read_map": {"soc": {"addr": 32001, "type": "u16"}},
            "write_map": {"charge_power": {"addr": 42002, "type": "u16"}},
            "register_map": {"mode": {"addr": 42001, "type": "u16"}},
        }
    )

    assert device["telemetry_map"]["soc"] == {"addr": 32001, "type": "u16"}
    assert device["control_map"]["charge_power"] == {"addr": 42002, "type": "u16"}
    assert device["control_map"]["mode"] == {"addr": 42001, "type": "u16"}
    assert resolve_protocol_read(device, "soc") == {"addr": 32001, "type": "u16"}
    assert resolve_protocol_write(device, "charge_power") == {"addr": 42002, "type": "u16"}


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
