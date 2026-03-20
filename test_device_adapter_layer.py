from edgefusion.adapters.device_profiles import (
    normalize_device_profile,
    resolve_protocol_read,
    resolve_protocol_write,
)
from edgefusion.charger_layout import build_connector_views
from edgefusion.point_tables import POINT_TABLES, get_device_default_maps
from edgefusion.register_map import (
    normalize_mapping_aliases,
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
    from edgefusion.adapters.modbus.profiles.vendors import get_vendor_point_tables_for_device_type

    assert grid_meter.GRID_METER_POINT_TABLES == get_vendor_point_tables_for_device_type("grid_meter")
    assert pv.PV_POINT_TABLES == get_vendor_point_tables_for_device_type("pv")
    assert storage.STORAGE_POINT_TABLES == get_vendor_point_tables_for_device_type("energy_storage")
    assert charger.CHARGER_POINT_TABLES == get_vendor_point_tables_for_device_type("charging_station")


def test_modbus_profile_package_exposes_vendor_submodules():
    from edgefusion.adapters.modbus.profiles.vendors import generic, xj

    assert "generic_grid_meter" in generic.GENERIC_POINT_TABLES
    assert "generic_charger" in generic.GENERIC_POINT_TABLES
    assert "xj_dc_120kw" in xj.XJ_POINT_TABLES


def test_vendor_registry_exposes_vendor_tables_and_device_family_views():
    from edgefusion.adapters.modbus.profiles.vendors import (
        VENDOR_POINT_TABLES,
        get_vendor_point_tables,
        get_vendor_point_tables_for_device_type,
    )

    assert "generic" in VENDOR_POINT_TABLES
    assert "xj" in VENDOR_POINT_TABLES
    assert get_vendor_point_tables("generic") is VENDOR_POINT_TABLES["generic"]
    assert "generic_grid_meter" in get_vendor_point_tables_for_device_type("grid_meter")
    assert "generic_pv" in get_vendor_point_tables_for_device_type("pv")
    assert "generic_storage" in get_vendor_point_tables_for_device_type("energy_storage")
    assert "generic_charger" in get_vendor_point_tables_for_device_type("charging_station")
    assert "xj_dc_120kw" in get_vendor_point_tables_for_device_type("charging_station")


def test_vendor_registry_resolves_vendor_aliases_and_model_aliases():
    from edgefusion.adapters.modbus.profiles.vendors import (
        get_vendor_default_model,
        resolve_vendor_key,
        resolve_vendor_model,
    )

    assert resolve_vendor_key("许继") == "xj"
    assert resolve_vendor_key("XUJi") == "xj"
    assert resolve_vendor_model("120 kW", vendor="许继", device_type="charging_station") == "xj_dc_120kw"
    assert resolve_vendor_model("xj dc 240kw", vendor="xj", device_type="charging_station") == "xj_dc_240kw"
    assert get_vendor_default_model("generic", "energy_storage") == "generic_storage"
    assert get_vendor_default_model("xj", "charging_station") is None


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


def test_modbus_defaults_can_resolve_vendor_model_aliases():
    from edgefusion.adapters.modbus.profiles import get_modbus_device_default_maps

    defaults = get_modbus_device_default_maps(
        {
            "device_id": "charger_1",
            "type": "charging_station",
            "manufacturer": "许继",
            "model": "120kw",
        }
    )

    assert defaults["connector_count"] == 2
    assert defaults["telemetry_map"]["gun_count"]["addr"] == 0x1000


def test_modbus_defaults_can_use_unambiguous_vendor_default_model():
    from edgefusion.adapters.modbus.profiles import get_modbus_device_default_maps

    defaults = get_modbus_device_default_maps(
        {
            "device_id": "storage_1",
            "type": "energy_storage",
            "manufacturer": "通用",
        }
    )

    assert defaults["telemetry_map"]["soc"]["addr"] == 52001
    assert defaults["control_map"]["mode"]["addr"] == 42001


def test_protocol_agnostic_connector_profile_defaults_resolve_from_device_info():
    from edgefusion.adapters.charger_profiles import (
        get_charger_connector_count,
        get_charger_connector_profile_defaults,
    )

    device_info = {
        "device_id": "charger_1",
        "type": "charging_station",
        "protocol": "modbus",
        "manufacturer": "许继",
        "model": "120kw",
    }

    assert get_charger_connector_count(device_info) == 2
    defaults = get_charger_connector_profile_defaults(device_info, 2)
    assert defaults["telemetry_map"]["power"]["addr"] == 0x210E
    assert defaults["status_map"][3] == "charging"
    assert defaults["control_map"]["power_limit"]["builder"] == "xj_power_absolute"


def test_charger_layout_builds_connector_views_through_adapter_seam():
    views = build_connector_views(
        {
            "device_id": "charger_1",
            "type": "charging_station",
            "protocol": "modbus",
            "manufacturer": "许继",
            "model": "120kw",
        }
    )

    assert [view["device_id"] for view in views] == ["charger_1:1", "charger_1:2"]
    assert views[1]["telemetry_map"]["power"]["addr"] == 0x210E
    assert views[1]["control_map"]["power_limit"]["connector_id"] == 2


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


def test_register_map_resolution_no_longer_reads_legacy_keys_directly():
    device_info = {
        "read_map": {"power": {"addr": 39991, "type": "u16"}},
        "write_map": {"power_limit": {"addr": 49991, "type": "u16"}},
    }

    assert resolve_read_register(device_info, "power") == "power"
    assert resolve_write_register(device_info, "power_limit") == "power_limit"


def test_normalize_mapping_aliases_absorbs_and_removes_legacy_keys():
    normalized = normalize_mapping_aliases(
        {
            "read_map": {"power": {"addr": 39991, "type": "u16"}},
            "write_map": {"power_limit": {"addr": 49991, "type": "u16"}},
            "register_map": {"mode": {"addr": 42001, "type": "u16"}},
        }
    )

    assert normalized["telemetry_map"]["power"] == {"addr": 39991, "type": "u16"}
    assert normalized["control_map"]["power_limit"] == {"addr": 49991, "type": "u16"}
    assert normalized["control_map"]["mode"] == {"addr": 42001, "type": "u16"}
    assert "read_map" not in normalized
    assert "write_map" not in normalized
    assert "register_map" not in normalized


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
    assert "read_map" not in device
    assert "write_map" not in device
    assert "register_map" not in device
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
