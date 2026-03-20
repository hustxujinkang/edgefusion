from pymodbus.client import ModbusSerialClient

from .modbus_transport import ModbusTransport


class ModbusRtuTransport(ModbusTransport):
    def __init__(
        self,
        serial_port: str,
        baudrate: int = 9600,
        bytesize: int = 8,
        parity: str = "N",
        stopbits: int = 1,
        timeout: int = 5,
    ):
        self.serial_port = serial_port
        self.baudrate = baudrate
        self.bytesize = bytesize
        self.parity = parity
        self.stopbits = stopbits
        self.timeout = timeout
        self.client = ModbusSerialClient(
            port=self.serial_port,
            baudrate=self.baudrate,
            bytesize=self.bytesize,
            parity=self.parity,
            stopbits=self.stopbits,
            timeout=self.timeout,
        )
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
