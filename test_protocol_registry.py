from edgefusion.protocol.registry import ProtocolRegistry


class StubProtocol:
    def __init__(self, config=None):
        self.config = dict(config or {})
        self.connected = False

    @property
    def is_connected(self):
        return self.connected

    def connect(self):
        self.connected = True
        return True

    def disconnect(self):
        self.connected = False
        return True


def test_protocol_registry_initializes_configured_protocols_and_base_modbus_endpoint():
    created_modbus = []

    def modbus_factory(config, defaults=None):
        protocol = StubProtocol(config)
        created_modbus.append(protocol)
        return protocol

    def endpoint_builder(config, defaults=None):
        effective = dict(defaults or {})
        effective.update(config or {})
        return f"{effective.get('host', 'localhost')}:{effective.get('port', 502)}"

    registry = ProtocolRegistry(
        {
            "modbus": {"host": "base-host", "port": 502},
            "mqtt": {"broker": "broker"},
            "simulation": {"enabled": True},
        },
        protocol_builders={
            "mqtt": StubProtocol,
            "simulation": StubProtocol,
        },
        modbus_protocol_factory=modbus_factory,
        modbus_endpoint_builder=endpoint_builder,
    )

    assert registry.protocols["modbus"] is created_modbus[0]
    assert registry.endpoint_protocols["base-host:502"] is created_modbus[0]
    assert isinstance(registry.protocols["mqtt"], StubProtocol)
    assert isinstance(registry.protocols["simulation"], StubProtocol)


def test_protocol_registry_creates_and_reuses_dedicated_modbus_endpoint_protocols():
    created_modbus = []

    def modbus_factory(config, defaults=None):
        effective = dict(defaults or {})
        effective.update(config or {})
        protocol = StubProtocol(effective)
        created_modbus.append(protocol)
        return protocol

    def endpoint_builder(config, defaults=None):
        effective = dict(defaults or {})
        effective.update(config or {})
        return f"{effective.get('host', 'localhost')}:{effective.get('port', 502)}"

    registry = ProtocolRegistry(
        {
            "modbus": {"host": "base-host", "port": 502},
        },
        protocol_builders={},
        modbus_protocol_factory=modbus_factory,
        modbus_endpoint_builder=endpoint_builder,
    )
    base_protocol = registry.protocols["modbus"]
    base_protocol.connected = True

    device_info = {
        "protocol": "modbus",
        "host": "10.0.0.8",
        "port": 1502,
    }

    resolved_first = registry.get_protocol_for_device(device_info)
    resolved_second = registry.get_protocol_for_device(device_info)

    assert resolved_first is resolved_second
    assert resolved_first is not base_protocol
    assert resolved_first.is_connected is True
    assert len(created_modbus) == 2
