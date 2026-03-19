from edgefusion.config import Config
from edgefusion.device_manager import DeviceManager
from edgefusion.monitor.collector import DataCollector


class FakeProtocol:
    def __init__(self, read_values=None):
        self.connected = True
        self.read_values = read_values or {}
        self.read_calls = []
        self.write_calls = []

    @property
    def is_connected(self):
        return self.connected

    def read_data(self, device_id, register):
        self.read_calls.append((device_id, register))
        return self.read_values.get((device_id, register))

    def write_data(self, device_id, register, value):
        self.write_calls.append((device_id, register, value))
        return True


def test_device_manager_maps_grid_pv_and_storage_semantic_reads_to_protocol_registers():
    protocol = FakeProtocol(
        {
            ("grid_real", "30001"): -4200,
            ("pv_real", "31001"): 5600,
            ("storage_real", "32001"): 47,
        }
    )
    device_manager = DeviceManager({})
    device_manager.protocols["modbus"] = protocol

    assert device_manager.register_device(
        {
            "device_id": "grid_real",
            "type": "grid_meter",
            "protocol": "modbus",
            "telemetry_map": {"power": "30001"},
        }
    ) is True
    assert device_manager.register_device(
        {
            "device_id": "pv_real",
            "type": "pv",
            "protocol": "modbus",
            "telemetry_map": {"power": "31001"},
        }
    ) is True
    assert device_manager.register_device(
        {
            "device_id": "storage_real",
            "type": "energy_storage",
            "protocol": "modbus",
            "telemetry_map": {"soc": "32001"},
        }
    ) is True

    assert device_manager.read_device_data("grid_real", "power") == -4200
    assert device_manager.read_device_data("pv_real", "power") == 5600
    assert device_manager.read_device_data("storage_real", "soc") == 47
    assert protocol.read_calls == [
        ("grid_real", "30001"),
        ("pv_real", "31001"),
        ("storage_real", "32001"),
    ]


def test_device_manager_maps_storage_and_pv_control_points_before_protocol_writes():
    protocol = FakeProtocol()
    device_manager = DeviceManager({})
    device_manager.protocols["modbus"] = protocol

    assert device_manager.register_device(
        {
            "device_id": "storage_real",
            "type": "energy_storage",
            "protocol": "modbus",
            "control_map": {
                "mode": "41001",
                "charge_power": "41002",
                "discharge_power": "41003",
            },
        }
    ) is True
    assert device_manager.register_device(
        {
            "device_id": "pv_real",
            "type": "pv",
            "protocol": "modbus",
            "control_map": {"power_limit": "42001"},
        }
    ) is True

    assert device_manager.write_device_data("storage_real", "mode", "charge") is True
    assert device_manager.write_device_data("storage_real", "charge_power", 2500) is True
    assert device_manager.write_device_data("pv_real", "power_limit", 3800) is True
    assert protocol.write_calls == [
        ("storage_real", "41001", "charge"),
        ("storage_real", "41002", 2500),
        ("pv_real", "42001", 3800),
    ]


def test_charger_connector_view_inherits_connector_specific_register_mapping():
    protocol = FakeProtocol()
    device_manager = DeviceManager({})
    device_manager.protocols["modbus"] = protocol

    assert device_manager.register_device(
        {
            "device_id": "charger_pile_real",
            "type": "charging_station",
            "protocol": "modbus",
            "connectors": [
                {
                    "device_id": "charger_pile_real:1",
                    "connector_id": 1,
                    "control_map": {"power_limit": "43001"},
                },
                {
                    "device_id": "charger_pile_real:2",
                    "connector_id": 2,
                    "control_map": {"power_limit": "43011"},
                },
            ],
        }
    ) is True

    assert device_manager.write_device_data("charger_pile_real:2", "power_limit", 3200) is True
    assert protocol.write_calls == [
        ("charger_pile_real", "43011", 3200),
    ]


def test_collector_reads_grid_pv_and_storage_snapshots_through_telemetry_mappings():
    protocol = FakeProtocol(
        {
            ("grid_real", "30001"): -500,
            ("grid_real", "30002"): "online",
            ("pv_real", "31001"): 6200,
            ("pv_real", "31002"): 12.5,
            ("pv_real", "31003"): 380,
            ("pv_real", "31004"): 16.3,
            ("pv_real", "31005"): "online",
            ("pv_real", "31006"): 6000,
            ("pv_real", "31007"): 0,
            ("storage_real", "32001"): 55,
            ("storage_real", "32002"): 0,
            ("storage_real", "32003"): 760,
            ("storage_real", "32004"): 0,
            ("storage_real", "32005"): "auto",
            ("storage_real", "32006"): 3000,
            ("storage_real", "32007"): 3000,
        }
    )
    device_manager = DeviceManager({})
    device_manager.protocols["modbus"] = protocol

    assert device_manager.register_device(
        {
            "device_id": "grid_real",
            "type": "grid_meter",
            "protocol": "modbus",
            "telemetry_map": {"power": "30001", "status": "30002"},
        }
    ) is True
    assert device_manager.register_device(
        {
            "device_id": "pv_real",
            "type": "pv",
            "protocol": "modbus",
            "telemetry_map": {
                "power": "31001",
                "energy": "31002",
                "voltage": "31003",
                "current": "31004",
                "status": "31005",
                "power_limit": "31006",
                "min_power_limit": "31007",
            },
        }
    ) is True
    assert device_manager.register_device(
        {
            "device_id": "storage_real",
            "type": "energy_storage",
            "protocol": "modbus",
            "telemetry_map": {
                "soc": "32001",
                "power": "32002",
                "voltage": "32003",
                "current": "32004",
                "mode": "32005",
                "max_charge_power": "32006",
                "max_discharge_power": "32007",
            },
        }
    ) is True

    collector = DataCollector(Config(), device_manager, None)
    collected = collector.collect_data()
    by_type = {item["device_type"]: item for item in collected}

    assert by_type["grid_meter"]["data"]["power"] == -500
    assert by_type["pv"]["data"]["power_limit"] == 6000
    assert by_type["energy_storage"]["data"]["max_discharge_power"] == 3000


def test_device_manager_derives_semantic_maps_from_point_table_models():
    protocol = FakeProtocol(
        {
            ("grid_real", "50001"): -1800,
            ("grid_real", "50002"): "online",
            ("pv_real", "51001"): 4200,
            ("pv_real", "51006"): 3800,
            ("storage_real", "52001"): 61,
            ("storage_real", "52006"): 3200,
        }
    )
    device_manager = DeviceManager({})
    device_manager.protocols["modbus"] = protocol

    assert device_manager.register_device(
        {
            "device_id": "grid_real",
            "type": "grid_meter",
            "model": "generic_grid_meter",
            "protocol": "modbus",
        }
    ) is True
    assert device_manager.register_device(
        {
            "device_id": "pv_real",
            "type": "pv",
            "model": "generic_pv",
            "protocol": "modbus",
        }
    ) is True
    assert device_manager.register_device(
        {
            "device_id": "storage_real",
            "type": "energy_storage",
            "model": "generic_storage",
            "protocol": "modbus",
        }
    ) is True

    assert device_manager.read_device_data("grid_real", "power") == -1800
    assert device_manager.read_device_data("grid_real", "status") == "online"
    assert device_manager.read_device_data("pv_real", "power") == 4200
    assert device_manager.read_device_data("pv_real", "power_limit") == 3800
    assert device_manager.read_device_data("storage_real", "soc") == 61
    assert device_manager.read_device_data("storage_real", "max_charge_power") == 3200
    assert protocol.read_calls == [
        ("grid_real", "50001"),
        ("grid_real", "50002"),
        ("pv_real", "51001"),
        ("pv_real", "51006"),
        ("storage_real", "52001"),
        ("storage_real", "52006"),
    ]


def test_explicit_semantic_maps_override_point_table_defaults():
    protocol = FakeProtocol(
        {
            ("grid_real", "59991"): -900,
        }
    )
    device_manager = DeviceManager({})
    device_manager.protocols["modbus"] = protocol

    assert device_manager.register_device(
        {
            "device_id": "grid_real",
            "type": "grid_meter",
            "model": "generic_grid_meter",
            "protocol": "modbus",
            "telemetry_map": {"power": "59991"},
        }
    ) is True

    assert device_manager.read_device_data("grid_real", "power") == -900
    assert protocol.read_calls == [("grid_real", "59991")]


def test_charger_model_point_table_expands_connectors_and_maps_gun_registers():
    protocol = FakeProtocol(
        {
            ("charger_real", "8462"): 7200,
            ("charger_real", "8448"): 3,
        }
    )
    device_manager = DeviceManager({})
    device_manager.protocols["modbus"] = protocol

    assert device_manager.register_device(
        {
            "device_id": "charger_real",
            "type": "charging_station",
            "model": "xj_dc_120kw",
            "protocol": "modbus",
        }
    ) is True

    connectors = device_manager.get_device_connectors("charger_real")
    assert [connector["device_id"] for connector in connectors] == ["charger_real:1", "charger_real:2"]
    assert device_manager.read_device_data("charger_real:2", "power") == 7200
    assert device_manager.read_device_data("charger_real:2", "status") == 3
    assert protocol.read_calls == [
        ("charger_real", "8462"),
        ("charger_real", "8448"),
    ]


def test_charger_model_point_table_maps_power_limit_to_complex_control_command():
    protocol = FakeProtocol()
    device_manager = DeviceManager({})
    device_manager.protocols["modbus"] = protocol

    assert device_manager.register_device(
        {
            "device_id": "charger_real",
            "type": "charging_station",
            "model": "xj_dc_120kw",
            "protocol": "modbus",
        }
    ) is True

    assert device_manager.write_device_data("charger_real:2", "power_limit", 3200) is True
    assert protocol.write_calls == [
        (
            "charger_real",
            {
                "addr": 0x4000,
                "cmd": "write_registers",
                "builder": "xj_power_absolute",
                "connector_id": 2,
                "control_type": 0x02,
                "register_count": 12,
            },
            3200,
        )
    ]
