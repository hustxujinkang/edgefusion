from edgefusion.protocol.modbus import ModbusProtocol


class _Response:
    def __init__(self, registers=None):
        self.registers = registers or []

    def isError(self):
        return False


class DummyTransport:
    def __init__(self):
        self.connected = False
        self.read_calls = []
        self.write_calls = []
        self.write_batch_calls = []

    def connect(self):
        self.connected = True
        return True

    def disconnect(self):
        self.connected = False
        return True

    def is_connected(self):
        return self.connected

    def read_holding_registers(self, addr, count, slave):
        self.read_calls.append((addr, count, slave))
        return _Response([0x0000, 0x1388])

    def write_register(self, addr, value, slave):
        self.write_calls.append((addr, value, slave))
        return _Response()

    def write_registers(self, addr, values, slave):
        self.write_batch_calls.append((addr, values, slave))
        return _Response()


def test_modbus_protocol_uses_transport_object_instead_of_tcp_client():
    transport = DummyTransport()
    protocol = ModbusProtocol({}, transport=transport)

    assert protocol.transport is transport
    assert protocol.connect() is True
    assert protocol.connected is True
    assert protocol.read_data("7", {"addr": 50001, "type": "u32"}) == 5000
    assert transport.read_calls == [(50001, 2, 7)]
