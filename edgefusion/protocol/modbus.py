# Modbus协议实现
from typing import Dict, Any, Optional
from pymodbus.client import ModbusTcpClient
from pymodbus.exceptions import ModbusException
from .base import ProtocolBase


class ModbusProtocol(ProtocolBase):
    """Modbus协议实现"""
    
    def __init__(self, config: Dict[str, Any]):
        """初始化Modbus协议实例
        
        Args:
            config: Modbus配置参数，包含host、port等
        """
        super().__init__(config)
        self.host = config.get('host', 'localhost')
        self.port = config.get('port', 502)
        self.timeout = config.get('timeout', 5)
        self.client = None
    
    def connect(self) -> bool:
        """连接Modbus设备
        
        Returns:
            bool: 连接是否成功
        """
        try:
            self.client = ModbusTcpClient(self.host, port=self.port, timeout=self.timeout)
            self.connected = self.client.connect()
            return self.connected
        except Exception as e:
            print(f"Modbus连接失败: {e}")
            self.connected = False
            return False
    
    def disconnect(self) -> bool:
        """断开Modbus连接
        
        Returns:
            bool: 断开是否成功
        """
        try:
            if self.client:
                self.client.close()
            self.connected = False
            return True
        except Exception as e:
            print(f"Modbus断开失败: {e}")
            return False
    
    def read_data(self, device_id: str, register: str) -> Optional[Any]:
        """读取Modbus设备数据
        
        Args:
            device_id: 设备ID（对应Modbus从站地址）
            register: 寄存器地址
            
        Returns:
            Optional[Any]: 读取的数据，失败返回None
        """
        if not self.connected:
            return None
        
        try:
            slave_id = int(device_id)
            reg_addr = int(register)
            
            # 根据寄存器类型读取数据
            # 这里简化处理，实际应根据设备手册确定寄存器类型
            response = self.client.read_holding_registers(reg_addr, 1, slave=slave_id)
            
            if response.isError():
                return None
            
            return response.registers[0]
        except Exception as e:
            print(f"Modbus读取失败: {e}")
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
        if not self.connected:
            return None
        
        try:
            response = self.client.read_holding_registers(addr, count, slave=slave_id)
            if response.isError():
                print(f"读取寄存器失败: addr={addr}, count={count}")
                return None
            return response.registers
        except Exception as e:
            print(f"读取寄存器异常: {e}")
            return None
    
    def write_data(self, device_id: str, register: str, value: Any) -> bool:
        """写入Modbus设备数据
        
        Args:
            device_id: 设备ID（对应Modbus从站地址）
            register: 寄存器地址
            value: 要写入的值
            
        Returns:
            bool: 写入是否成功
        """
        if not self.connected:
            return False
        
        try:
            slave_id = int(device_id)
            reg_addr = int(register)
            reg_value = int(value)
            
            response = self.client.write_register(reg_addr, reg_value, slave=slave_id)
            
            if response.isError():
                return False
            
            return True
        except Exception as e:
            print(f"Modbus写入失败: {e}")
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
                response = self.client.read_holding_registers(0, 1, slave=i)
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
