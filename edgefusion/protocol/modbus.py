# Modbus协议实现
from typing import Dict, Any, Optional
from ..logger import get_logger
from ..transport import ModbusRtuTransport, ModbusTcpTransport
from .base import ProtocolBase


class ModbusProtocol(ProtocolBase):
    """Modbus协议实现"""
    
    def __init__(self, config: Dict[str, Any], transport: Any = None):
        """初始化Modbus协议实例
        
        Args:
            config: Modbus配置参数，包含host、port等
        """
        super().__init__(config)
        self.host = config.get('host', 'localhost')
        self.port = config.get('port', 502)
        self.timeout = config.get('timeout', 5)
        self.transport = transport or self._create_transport(config)
        self.logger = get_logger('ModbusProtocol')

    def _get_transport_mode(self, config: Dict[str, Any]) -> str:
        transport_mode = str(config.get("transport", config.get("mode", "tcp"))).lower()
        if transport_mode in {"rtu", "serial"}:
            return "rtu"
        return "tcp"

    def _get_serial_port(self, config: Dict[str, Any]) -> str:
        serial_port = config.get("serial_port")
        if serial_port:
            return str(serial_port)

        port = config.get("port")
        if isinstance(port, str) and port:
            return port

        return "COM1"

    def _create_transport(self, config: Dict[str, Any]) -> Any:
        transport_mode = self._get_transport_mode(config)
        if transport_mode == "rtu":
            return ModbusRtuTransport(
                serial_port=self._get_serial_port(config),
                baudrate=int(config.get("baudrate", 9600)),
                bytesize=int(config.get("bytesize", 8)),
                parity=str(config.get("parity", "N")),
                stopbits=int(config.get("stopbits", 1)),
                timeout=self.timeout,
            )

        return ModbusTcpTransport(self.host, port=self.port, timeout=self.timeout)

    @property
    def client(self) -> Any:
        return self.transport

    @client.setter
    def client(self, value: Any):
        self.transport = value

    def _transport_connected(self) -> bool:
        connection_state = getattr(self.transport, "is_connected", None)
        if callable(connection_state):
            return bool(connection_state())
        if connection_state is not None:
            return bool(connection_state)
        return bool(self.connected)
    
    def connect(self) -> bool:
        """连接Modbus设备
        
        Returns:
            bool: 连接是否成功
        """
        try:
            self.connected = bool(self.transport.connect())
            return self.connected
        except Exception as e:
            self.logger.error("Modbus连接失败: %s", e)
            self.connected = False
            return False
    
    def disconnect(self) -> bool:
        """断开Modbus连接
        
        Returns:
            bool: 断开是否成功
        """
        try:
            if self.transport:
                self.transport.disconnect()
            self.connected = False
            return True
        except Exception as e:
            self.logger.error("Modbus断开失败: %s", e)
            return False
    
    def _normalize_register_definition(self, register: Any) -> Dict[str, Any]:
        if isinstance(register, dict):
            return dict(register)
        return {"addr": int(register)}

    def _resolve_register_address(self, register: Any) -> int:
        if isinstance(register, dict):
            for key in ("register", "address", "addr"):
                if key in register:
                    return int(register[key])
            raise ValueError(f"无效寄存器定义: {register}")
        return int(register)

    def _get_register_type(self, register: Dict[str, Any]) -> str:
        return str(register.get("type", "u16")).lower()

    def _get_read_count(self, register: Dict[str, Any]) -> int:
        if "count" in register:
            return max(1, int(register["count"]))

        register_type = self._get_register_type(register)
        if register_type in {"u32", "i32"}:
            return 2
        return 1

    def _decode_value(self, registers: list[int], register: Dict[str, Any]) -> Any:
        register_type = self._get_register_type(register)
        scale = float(register.get("scale", 1) or 1)

        if register_type == "u16":
            value = int(registers[0])
        elif register_type == "i16":
            value = int(registers[0])
            if value >= 0x8000:
                value -= 0x10000
        elif register_type in {"u32", "i32"}:
            value = (int(registers[0]) << 16) | int(registers[1])
            if register_type == "i32" and value >= 0x80000000:
                value -= 0x100000000
        else:
            value = int(registers[0])

        decoded = value * scale
        if float(decoded).is_integer():
            return int(decoded)
        return decoded

    def _encode_single_value(self, register: Dict[str, Any], value: Any) -> int:
        register_type = self._get_register_type(register)
        scale = float(register.get("scale", 1) or 1)
        raw_value = int(round(float(value) / scale))

        if register_type == "i16" and raw_value < 0:
            raw_value += 0x10000
        return raw_value & 0xFFFF

    def read_data(self, device_id: str, register: Any) -> Optional[Any]:
        """读取Modbus设备数据
        
        Args:
            device_id: 设备ID（对应Modbus从站地址）
            register: 寄存器地址
            
        Returns:
            Optional[Any]: 读取的数据，失败返回None
        """
        if not self._transport_connected():
            return None
        
        try:
            slave_id = int(device_id)
            register_def = self._normalize_register_definition(register)
            reg_addr = self._resolve_register_address(register_def)
            count = self._get_read_count(register_def)

            response = self.transport.read_holding_registers(reg_addr, count, slave=slave_id)
            
            if response.isError():
                return None

            return self._decode_value(response.registers, register_def)
        except Exception as e:
            self.logger.error("Modbus读取失败: %s", e)
            return None
    
    def _read_registers(self, addr: int, count: int, slave_id: int = 1) -> Optional[list]:
        """读取多个保持寄存器（内部方法）
        
        Args:
            addr: 寄存器起始地址
            count: 读取数量
            slave_id: 从站ID
            
        Returns:
            Optional[list]: 寄存器值列表，失败返回None
        """
        if not self._transport_connected():
            return None
        
        try:
            response = self.transport.read_holding_registers(addr, count, slave=slave_id)
            if response.isError():
                self.logger.warning("读取寄存器失败: addr=%s, count=%s", addr, count)
                return None
            return response.registers
        except Exception as e:
            self.logger.error("读取寄存器异常: %s", e)
            return None
    
    def _write_registers(self, addr: int, values: list, slave_id: int = 1) -> bool:
        """写多个保持寄存器（内部方法）
        
        Args:
            addr: 寄存器起始地址
            values: 要写入的寄存器值列表
            slave_id: 从站ID
            
        Returns:
            bool: 是否成功
        """
        if not self._transport_connected():
            return False
        
        try:
            from pymodbus.payload import BinaryPayloadBuilder
            from pymodbus.constants import Endian
            
            response = self.transport.write_registers(addr, values, slave=slave_id)
            if response.isError():
                self.logger.warning("写寄存器失败: addr=%s, values=%s", addr, values)
                return False
            return True
        except Exception as e:
            self.logger.error("写寄存器异常: %s", e)
            return False

    def _build_command_values(self, register: Dict[str, Any], value: Any) -> list[int]:
        builder = register.get("builder")
        if builder == "xj_power_absolute":
            connector_id = int(register.get("connector_id", 1))
            control_type = int(register.get("control_type", 0x02))
            param = int(register.get("fixed_value", value))
            register_count = max(4, int(register.get("register_count", 12)))
            values = [
                connector_id,
                control_type,
                param & 0xFFFF,
                (param >> 16) & 0xFFFF,
            ]
            return values + [0] * max(0, register_count - len(values))

        raw_values = register.get("values")
        if isinstance(raw_values, list):
            return [int(item) for item in raw_values]

        return [int(value)]
    
    def write_data(self, device_id: str, register: Any, value: Any) -> bool:
        """写入Modbus设备数据
        
        Args:
            device_id: 设备ID（对应Modbus从站地址）
            register: 寄存器地址
            value: 要写入的值
            
        Returns:
            bool: 写入是否成功
        """
        if not self._transport_connected():
            return False
        
        try:
            slave_id = int(device_id)
            if isinstance(register, dict) and register.get("cmd") == "write_registers":
                reg_addr = self._resolve_register_address(register)
                values = self._build_command_values(register, value)
                return self._write_registers(reg_addr, values, slave_id)

            register_def = self._normalize_register_definition(register)
            reg_addr = self._resolve_register_address(register_def)
            reg_value = register_def.get("fixed_value", value)
            reg_value = self._encode_single_value(register_def, reg_value)

            response = self.transport.write_register(reg_addr, reg_value, slave=slave_id)

            if response.isError():
                return False

            return True
        except Exception as e:
            self.logger.error("Modbus写入失败: %s", e)
            return False
    
    def discover_devices(self) -> Dict[str, Dict[str, Any]]:
        """发现Modbus设备
        
        Returns:
            Dict[str, Dict[str, Any]]: 发现的设备列表
        """
        devices = {}
        
        # 简单的设备发现实现，实际应根据网络扫描或配置文件
        # 这里返回模拟数据
        for i in range(1, 10):
            try:
                # 尝试读取设备ID
                response = self.transport.read_holding_registers(0, 1, slave=i)
                if not response.isError():
                    devices[str(i)] = {
                        'device_id': str(i),
                        'type': 'modbus_device',
                        'address': f"{self.host}:{self.port}",
                        'slave_id': i,
                        'status': 'online'
                    }
            except:
                pass
        
        return devices
