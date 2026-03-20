from pymodbus.client import ModbusTcpClient

from .modbus_transport import ModbusTransport


class ModbusTcpTransport(ModbusTransport):
    def __init__(self, host: str, port: int = 502, timeout: int = 5):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.client = ModbusTcpClient(self.host, port=self.port, timeout=self.timeout)
        self.connected = False

    def connect(self) -> bool:
        self.connected = self.client.connect()
        return self.connected

    def disconnect(self) -> bool:
        self.client.close()
        self.connected = False
        return True

    def read_holding_registers(self, addr: int, count: int, slave: int):
        return self.client.read_holding_registers(addr, count, slave=slave)

    def write_register(self, addr: int, value: int, slave: int):
        return self.client.write_register(addr, value, slave=slave)

    def write_registers(self, addr: int, values: list[int], slave: int):
        return self.client.write_registers(addr, values, slave=slave)

    @property
    def is_connected(self) -> bool:
        return self.connected
