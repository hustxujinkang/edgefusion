from edgefusion.adapters.device_profiles import (
    normalize_device_profile,
    resolve_protocol_read,
    resolve_protocol_write,
)


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
