from edgefusion.protocol.modbus import ModbusProtocol
from edgefusion.transport.modbus_rtu import ModbusRtuTransport


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


class DummySerialClient:
    def __init__(self, port, baudrate, bytesize, parity, stopbits, timeout):
        self.port = port
        self.baudrate = baudrate
        self.bytesize = bytesize
        self.parity = parity
        self.stopbits = stopbits
        self.timeout = timeout
        self.connected = False
        self.read_calls = []
        self.write_calls = []
        self.write_batch_calls = []

    def connect(self):
        self.connected = True
        return True

    def close(self):
        self.connected = False

    def read_holding_registers(self, addr, count, slave):
        self.read_calls.append((addr, count, slave))
        return _Response([11, 22])

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


def test_modbus_rtu_transport_wraps_serial_client(monkeypatch):
    monkeypatch.setattr(
        "edgefusion.transport.modbus_rtu.ModbusSerialClient",
        DummySerialClient,
    )

    transport = ModbusRtuTransport(
        serial_port="COM3",
        baudrate=9600,
        bytesize=8,
        parity="E",
        stopbits=1,
        timeout=3,
    )

    assert transport.connect() is True
    assert transport.is_connected is True
    assert transport.read_holding_registers(12, 2, slave=7).registers == [11, 22]
    assert transport.write_register(13, 99, slave=7).isError() is False
    assert transport.write_registers(14, [1, 2], slave=7).isError() is False
    assert transport.client.port == "COM3"
    assert transport.client.baudrate == 9600
    assert transport.client.bytesize == 8
    assert transport.client.parity == "E"
    assert transport.client.stopbits == 1
    assert transport.client.timeout == 3
    assert transport.client.read_calls == [(12, 2, 7)]
    assert transport.client.write_calls == [(13, 99, 7)]
    assert transport.client.write_batch_calls == [(14, [1, 2], 7)]
    assert transport.disconnect() is True
    assert transport.is_connected is False


def test_modbus_protocol_uses_rtu_transport_for_serial_configs(monkeypatch):
    created = {}

    class SpyRtuTransport:
        def __init__(self, serial_port, baudrate, bytesize, parity, stopbits, timeout):
            created.update(
                {
                    "serial_port": serial_port,
                    "baudrate": baudrate,
                    "bytesize": bytesize,
                    "parity": parity,
                    "stopbits": stopbits,
                    "timeout": timeout,
                }
            )
            self.connected = False

        def connect(self):
            self.connected = True
            return True

        def disconnect(self):
            self.connected = False
            return True

        def read_holding_registers(self, addr, count, slave):
            return _Response([0, 0])

        def write_register(self, addr, value, slave):
            return _Response()

        def write_registers(self, addr, values, slave):
            return _Response()

        @property
        def is_connected(self):
            return self.connected

    monkeypatch.setattr("edgefusion.protocol.modbus.ModbusRtuTransport", SpyRtuTransport)

    protocol = ModbusProtocol(
        {
            "transport": "rtu",
            "serial_port": "COM7",
            "baudrate": 19200,
            "bytesize": 7,
            "parity": "O",
            "stopbits": 2,
            "timeout": 4,
        }
    )

    assert created == {
        "serial_port": "COM7",
        "baudrate": 19200,
        "bytesize": 7,
        "parity": "O",
        "stopbits": 2,
        "timeout": 4,
    }
    assert protocol.connect() is True
    assert protocol.transport.is_connected is True
