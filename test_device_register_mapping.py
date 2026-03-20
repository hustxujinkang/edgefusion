from edgefusion.config import Config
import edgefusion.device_manager as device_manager_module
from edgefusion.device_manager import DeviceManager
from edgefusion.monitor.collector import DataCollector


class FakeProtocol:
    def __init__(self, read_values=None):
        self.connected = True
        self.read_values = {
            (device_id, self._normalize_register(register)): value
            for (device_id, register), value in (read_values or {}).items()
        }
        self.read_calls = []
        self.write_calls = []

    @property
    def is_connected(self):
        return self.connected

    def read_data(self, device_id, register):
        self.read_calls.append((device_id, register))
        return self.read_values.get((device_id, self._normalize_register(register)))

    def write_data(self, device_id, register, value):
        self.write_calls.append((device_id, register, value))
        return True

    def _normalize_register(self, register):
        if isinstance(register, dict):
            return register.get("addr", register.get("address", register.get("register")))
        if isinstance(register, str) and register.isdigit():
            return int(register)
        return register


class EndpointProtocol(FakeProtocol):
    instances = []

    def __init__(self, config):
        super().__init__()
        self.config = dict(config)
        self.connected = False
        EndpointProtocol.instances.append(self)

    def connect(self):
        self.connected = True
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
        ("grid_real", {"addr": 50001, "type": "i32", "scale": 1, "unit": "W"}),
        ("grid_real", {"addr": 50002, "type": "u16", "scale": 1, "unit": ""}),
        ("pv_real", {"addr": 51001, "type": "i32", "scale": 1, "unit": "W"}),
        ("pv_real", {"addr": 51006, "type": "u16", "scale": 1, "unit": "W"}),
        ("storage_real", {"addr": 52001, "type": "u16", "scale": 1, "unit": "%"}),
        ("storage_real", {"addr": 52006, "type": "u16", "scale": 1, "unit": "W"}),
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
    assert device_manager.read_device_data("charger_real:2", "status") == "charging"
    assert protocol.read_calls == [
        ("charger_real", {"addr": 0x210E, "type": "u32", "scale": 0.001, "unit": "kW"}),
        ("charger_real", {"addr": 0x2100, "type": "u16", "scale": 1, "unit": ""}),
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


def test_device_manager_uses_dedicated_modbus_protocol_per_endpoint(monkeypatch):
    EndpointProtocol.instances = []
    monkeypatch.setattr(device_manager_module, "create_modbus_protocol", lambda config, defaults=None: EndpointProtocol(config))

    device_manager = DeviceManager({"modbus": {"host": "base-host", "port": 502, "timeout": 5}})
    base_protocol = device_manager.protocols["modbus"]
    base_protocol.connected = True

    assert device_manager.register_device(
        {
            "device_id": "grid_meter_a",
            "type": "grid_meter",
            "protocol": "modbus",
            "host": "10.0.0.10",
            "port": 502,
            "unit_id": 1,
            "telemetry_map": {"power": {"addr": 30001, "type": "i32"}},
        }
    ) is True
    assert device_manager.register_device(
        {
            "device_id": "grid_meter_b",
            "type": "grid_meter",
            "protocol": "modbus",
            "host": "10.0.0.11",
            "port": 1502,
            "unit_id": 2,
            "telemetry_map": {"power": {"addr": 30001, "type": "i32"}},
        }
    ) is True

    device_manager.read_device_data("grid_meter_a", "power")
    device_manager.read_device_data("grid_meter_b", "power")

    endpoint_protocols = [instance for instance in EndpointProtocol.instances if instance is not base_protocol]
    assert [(instance.config["host"], instance.config["port"]) for instance in endpoint_protocols] == [
        ("10.0.0.10", 502),
        ("10.0.0.11", 1502),
    ]
    assert endpoint_protocols[0].read_calls == [("1", {"addr": 30001, "type": "i32"})]
    assert endpoint_protocols[1].read_calls == [("2", {"addr": 30001, "type": "i32"})]


def test_device_manager_uses_dedicated_modbus_protocol_per_rtu_endpoint(monkeypatch):
    EndpointProtocol.instances = []
    monkeypatch.setattr(device_manager_module, "create_modbus_protocol", lambda config, defaults=None: EndpointProtocol(config))

    device_manager = DeviceManager({"modbus": {"host": "base-host", "port": 502, "timeout": 5}})
    base_protocol = device_manager.protocols["modbus"]
    base_protocol.connected = True

    assert device_manager.register_device(
        {
            "device_id": "storage_rtu_a",
            "type": "energy_storage",
            "protocol": "modbus",
            "transport": "rtu",
            "serial_port": "COM3",
            "baudrate": 9600,
            "bytesize": 8,
            "parity": "N",
            "stopbits": 1,
            "unit_id": 3,
            "telemetry_map": {"soc": {"addr": 32001, "type": "u16"}},
        }
    ) is True
    assert device_manager.register_device(
        {
            "device_id": "storage_rtu_b",
            "type": "energy_storage",
            "protocol": "modbus",
            "transport": "rtu",
            "serial_port": "COM4",
            "baudrate": 19200,
            "bytesize": 7,
            "parity": "E",
            "stopbits": 2,
            "unit_id": 4,
            "telemetry_map": {"soc": {"addr": 32001, "type": "u16"}},
        }
    ) is True

    device_manager.read_device_data("storage_rtu_a", "soc")
    device_manager.read_device_data("storage_rtu_b", "soc")

    endpoint_protocols = [instance for instance in EndpointProtocol.instances if instance is not base_protocol]
    assert [
        (
            instance.config["transport"],
            instance.config["serial_port"],
            instance.config["baudrate"],
            instance.config["bytesize"],
            instance.config["parity"],
            instance.config["stopbits"],
        )
        for instance in endpoint_protocols
    ] == [
        ("rtu", "COM3", 9600, 8, "N", 1),
        ("rtu", "COM4", 19200, 7, "E", 2),
    ]
    assert endpoint_protocols[0].read_calls == [("3", {"addr": 32001, "type": "u16"})]
    assert endpoint_protocols[1].read_calls == [("4", {"addr": 32001, "type": "u16"})]


def test_device_manager_reuses_base_modbus_protocol_for_default_endpoint(monkeypatch):
    EndpointProtocol.instances = []
    monkeypatch.setattr(device_manager_module, "create_modbus_protocol", lambda config, defaults=None: EndpointProtocol(config))

    device_manager = DeviceManager({"modbus": {"host": "base-host", "port": 502, "timeout": 5}})
    base_protocol = device_manager.protocols["modbus"]
    base_protocol.connected = True

    assert device_manager.register_device(
        {
            "device_id": "grid_meter_default",
            "type": "grid_meter",
            "protocol": "modbus",
            "unit_id": 1,
            "telemetry_map": {"power": {"addr": 30001, "type": "i32"}},
        }
    ) is True

    device_manager.read_device_data("grid_meter_default", "power")

    assert EndpointProtocol.instances == [base_protocol]
    assert base_protocol.read_calls == [("1", {"addr": 30001, "type": "i32"})]


def test_collector_keeps_missing_grid_power_as_none_for_trust_checks():
    protocol = FakeProtocol({("grid_real", "30002"): "online"})
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

    collector = DataCollector(Config(), device_manager, None)
    collected = collector.collect_data()

    assert collected[0]["data"]["power"] is None
    assert collected[0]["data"]["status"] == "online"


def test_device_manager_normalizes_status_and_mode_fields_from_profile_maps():
    protocol = FakeProtocol(
        {
            ("pv_real", 51005): 2,
            ("storage_real", 52005): 3,
            ("charger_real", 0x2100): 3,
        }
    )
    device_manager = DeviceManager({})
    device_manager.protocols["modbus"] = protocol

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
    assert device_manager.register_device(
        {
            "device_id": "charger_real",
            "type": "charging_station",
            "model": "xj_dc_120kw",
            "protocol": "modbus",
        }
    ) is True

    assert device_manager.read_device_data("pv_real", "status") == "fault"
    assert device_manager.read_device_data("storage_real", "mode") == "auto"
    assert device_manager.read_device_data("charger_real:2", "status") == "charging"
