from edgefusion.adapters.device_profiles import normalize_device_profile
from edgefusion.device_inventory import DeviceInventory


def test_device_inventory_tracks_candidates_active_devices_and_connector_views():
    inventory = DeviceInventory(normalize_device_profile)

    assert inventory.register_candidate(
        {
            "device_id": "charger_candidate",
            "type": "charging_station",
            "protocol": "modbus",
            "model": "generic_charger",
        }
    ) is True

    candidate = inventory.get_candidate("charger_candidate")
    connector = inventory.get_candidate("charger_candidate:1")

    assert candidate is not None
    assert connector is not None
    assert connector["type"] == "charging_connector"
    assert connector["pile_id"] == "charger_candidate"

    assert inventory.activate_device("charger_candidate") is True
    assert inventory.get_device("charger_candidate") is not None
    assert inventory.get_candidate("charger_candidate") is not None

    inventory.update_device_status("charger_candidate", "offline")
    assert inventory.get_device_status("charger_candidate") == "offline"


def test_device_inventory_replaces_protocol_scoped_candidates_and_devices():
    inventory = DeviceInventory(normalize_device_profile)

    assert inventory.register_candidate(
        {
            "device_id": "sim_candidate_old",
            "type": "grid_meter",
            "protocol": "simulation",
        }
    ) is True
    assert inventory.register_candidate(
        {
            "device_id": "modbus_candidate_keep",
            "type": "grid_meter",
            "protocol": "modbus",
        }
    ) is True
    assert inventory.register_device(
        {
            "device_id": "sim_active_old",
            "type": "grid_meter",
            "protocol": "simulation",
        }
    ) is True
    assert inventory.register_device(
        {
            "device_id": "modbus_active_keep",
            "type": "grid_meter",
            "protocol": "modbus",
        }
    ) is True

    inventory.replace_protocol_candidates(
        "simulation",
        {
            "sim_candidate_new": normalize_device_profile(
                {
                    "device_id": "sim_candidate_new",
                    "type": "grid_meter",
                    "protocol": "simulation",
                }
            )
        },
        clear_active=True,
    )

    assert inventory.get_candidate("sim_candidate_old") is None
    assert inventory.get_candidate("sim_candidate_new") is not None
    assert inventory.get_candidate("modbus_candidate_keep") is not None
    assert inventory.get_device("sim_active_old") is None
    assert inventory.get_device("modbus_active_keep") is not None


def test_device_inventory_replaces_protocol_scoped_devices_only():
    inventory = DeviceInventory(normalize_device_profile)

    assert inventory.register_device(
        {
            "device_id": "modbus_old",
            "type": "grid_meter",
            "protocol": "modbus",
        }
    ) is True
    assert inventory.register_device(
        {
            "device_id": "simulation_keep",
            "type": "grid_meter",
            "protocol": "simulation",
        }
    ) is True

    inventory.replace_protocol_devices(
        "modbus",
        {
            "modbus_new": normalize_device_profile(
                {
                    "device_id": "modbus_new",
                    "type": "grid_meter",
                    "protocol": "modbus",
                }
            )
        },
    )

    assert inventory.get_device("modbus_old") is None
    assert inventory.get_device("modbus_new") is not None
    assert inventory.get_device("simulation_keep") is not None
