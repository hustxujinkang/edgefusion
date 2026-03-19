from edgefusion.protocol.modbus import ModbusProtocol


class _Response:
    def isError(self):
        return False


class FakeClient:
    def __init__(self):
        self.write_register_calls = []
        self.write_registers_calls = []

    def write_register(self, addr, value, slave):
        self.write_register_calls.append((addr, value, slave))
        return _Response()

    def write_registers(self, addr, values, slave):
        self.write_registers_calls.append((addr, values, slave))
        return _Response()


def test_modbus_protocol_expands_xj_power_limit_command_into_register_batch():
    client = FakeClient()
    protocol = ModbusProtocol({})
    protocol.client = client
    protocol.connected = True

    result = protocol.write_data(
        "7",
        {
            "addr": 0x4000,
            "cmd": "write_registers",
            "builder": "xj_power_absolute",
            "connector_id": 2,
            "control_type": 0x02,
            "register_count": 12,
        },
        70000,
    )

    assert result is True
    assert client.write_register_calls == []
    assert client.write_registers_calls == [
        (
            0x4000,
            [2, 0x02, 4464, 1, 0, 0, 0, 0, 0, 0, 0, 0],
            7,
        )
    ]


def test_modbus_protocol_uses_fixed_value_for_single_register_commands():
    client = FakeClient()
    protocol = ModbusProtocol({})
    protocol.client = client
    protocol.connected = True

    result = protocol.write_data(
        "3",
        {
            "addr": 5,
            "fixed_value": 2,
        },
        999,
    )

    assert result is True
    assert client.write_registers_calls == []
    assert client.write_register_calls == [
        (5, 2, 3),
    ]
