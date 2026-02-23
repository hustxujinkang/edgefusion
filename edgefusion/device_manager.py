# 设备管理模块
from typing import Dict, Any, List, Optional
from .protocol import ProtocolBase, ModbusProtocol, MQTTProtocol, OCPPProtocol
from .logger import get_logger


class DeviceManager:
    """设备管理模块，负责设备的注册、发现和管理"""
    
    def __init__(self, config: Dict[str, Any]):
        """初始化设备管理器
        
        Args:
            config: 设备管理配置
        """
        self.logger = get_logger('DeviceManager')
        self.config = config
        self.devices: Dict[str, Dict[str, Any]] = {}
        self.protocols: Dict[str, ProtocolBase] = {}
        self._init_protocols()
    
    def _init_protocols(self):
        """初始化协议实例"""
        # 初始化Modbus协议
        if 'modbus' in self.config:
            self.protocols['modbus'] = ModbusProtocol(self.config['modbus'])
        
        # 初始化MQTT协议
        if 'mqtt' in self.config:
            self.protocols['mqtt'] = MQTTProtocol(self.config['mqtt'])
        
        # 初始化OCPP协议
        if 'ocpp' in self.config:
            self.protocols['ocpp'] = OCPPProtocol(self.config['ocpp'])
    
    def start(self):
        """启动设备管理器"""
        # 连接所有协议
        connected_protocols = []
        for protocol_name, protocol in self.protocols.items():
            self.logger.info(f"连接{protocol_name}协议...")
            try:
                success = protocol.connect()
                if success:
                    self.logger.info(f"{protocol_name}协议连接成功")
                    connected_protocols.append(protocol_name)
                else:
                    self.logger.warning(f"{protocol_name}协议连接失败，将在无此协议模式下运行")
            except Exception as e:
                self.logger.error(f"{protocol_name}协议连接异常: {e}，将在无此协议模式下运行")
        
        # 发现设备
        if connected_protocols:
            self.logger.info(f"通过以下协议发现设备: {connected_protocols}")
            self.discover_devices()
        else:
            self.logger.warning("无可用协议连接，设备发现功能将不可用")
    
    def stop(self):
        """停止设备管理器"""
        # 断开所有协议
        for protocol_name, protocol in self.protocols.items():
            self.logger.info(f"断开{protocol_name}协议...")
            protocol.disconnect()
    
    def discover_devices(self) -> Dict[str, Dict[str, Any]]:
        """发现所有设备
        
        Returns:
            Dict[str, Dict[str, Any]]: 发现的设备列表
        """
        discovered_devices = {}
        
        # 通过各协议发现设备
        for protocol_name, protocol in self.protocols.items():
            if protocol.is_connected:
                self.logger.info(f"通过{protocol_name}协议发现设备...")
                try:
                    protocol_devices = protocol.discover_devices()
                    
                    # 为每个设备添加协议信息
                    for device_id, device_info in protocol_devices.items():
                        device_info['protocol'] = protocol_name
                        discovered_devices[device_id] = device_info
                except Exception as e:
                    self.logger.error(f"{protocol_name}协议设备发现失败: {e}")
        
        # 更新设备列表
        self.devices.update(discovered_devices)
        self.logger.info(f"共发现{len(discovered_devices)}个设备")
        return discovered_devices
    
    def register_device(self, device_info: Dict[str, Any]) -> bool:
        """手动注册设备
        
        Args:
            device_info: 设备信息
            
        Returns:
            bool: 注册是否成功
        """
        device_id = device_info.get('device_id')
        if not device_id:
            return False
        
        # 检查协议是否存在
        protocol_name = device_info.get('protocol')
        if protocol_name not in self.protocols:
            return False
        
        # 注册设备
        self.devices[device_id] = device_info
        self.logger.info(f"手动注册设备: {device_id}")
        return True
    
    def unregister_device(self, device_id: str) -> bool:
        """注销设备
        
        Args:
            device_id: 设备ID
            
        Returns:
            bool: 注销是否成功
        """
        if device_id in self.devices:
            del self.devices[device_id]
            self.logger.info(f"注销设备: {device_id}")
            return True
        return False
    
    def get_device(self, device_id: str) -> Optional[Dict[str, Any]]:
        """获取设备信息
        
        Args:
            device_id: 设备ID
            
        Returns:
            Optional[Dict[str, Any]]: 设备信息，不存在返回None
        """
        return self.devices.get(device_id)
    
    def get_devices(self, device_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取设备列表
        
        Args:
            device_type: 设备类型，None表示获取所有设备
            
        Returns:
            List[Dict[str, Any]]: 设备列表
        """
        if device_type:
            return [device for device in self.devices.values() if device.get('type') == device_type]
        return list(self.devices.values())
    
    def read_device_data(self, device_id: str, register: str) -> Optional[Any]:
        """读取设备数据
        
        Args:
            device_id: 设备ID
            register: 数据点
            
        Returns:
            Optional[Any]: 读取的数据，失败返回None
        """
        try:
            device_info = self.get_device(device_id)
            if not device_info:
                self.logger.warning(f"设备不存在: {device_id}")
                return None
            
            protocol_name = device_info.get('protocol')
            if protocol_name not in self.protocols:
                self.logger.warning(f"协议不存在: {protocol_name}")
                return None
            
            protocol = self.protocols[protocol_name]
            if not protocol.is_connected:
                self.logger.warning(f"协议未连接: {protocol_name}")
                return None
            
            return protocol.read_data(device_id, register)
        except Exception as e:
            self.logger.error(f"读取设备数据失败: {e}")
            return None
    
    def write_device_data(self, device_id: str, register: str, value: Any) -> bool:
        """写入设备数据
        
        Args:
            device_id: 设备ID
            register: 数据点
            value: 要写入的值
            
        Returns:
            bool: 写入是否成功
        """
        try:
            device_info = self.get_device(device_id)
            if not device_info:
                self.logger.warning(f"设备不存在: {device_id}")
                return False
            
            protocol_name = device_info.get('protocol')
            if protocol_name not in self.protocols:
                self.logger.warning(f"协议不存在: {protocol_name}")
                return False
            
            protocol = self.protocols[protocol_name]
            if not protocol.is_connected:
                self.logger.warning(f"协议未连接: {protocol_name}")
                return False
            
            return protocol.write_data(device_id, register, value)
        except Exception as e:
            self.logger.error(f"写入设备数据失败: {e}")
            return False
    
    def get_device_status(self, device_id: str) -> str:
        """获取设备状态
        
        Args:
            device_id: 设备ID
            
        Returns:
            str: 设备状态
        """
        device_info = self.get_device(device_id)
        if not device_info:
            return 'Unknown'
        
        return device_info.get('status', 'Unknown')
    
    def update_device_status(self, device_id: str, status: str):
        """更新设备状态
        
        Args:
            device_id: 设备ID
            status: 新状态
        """
        if device_id in self.devices:
            self.devices[device_id]['status'] = status
            self.logger.info(f"更新设备状态: {device_id} -> {status}")
