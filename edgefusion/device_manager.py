# 设备管理模块
from typing import Dict, Any, List, Optional
from .adapters import normalize_device_profile, normalize_field_value, resolve_protocol_read, resolve_protocol_write
from .device_semantics import field_is_readable, field_is_writable
from .device_inventory import DeviceInventory
from .protocol import (
    ProtocolBase,
    MQTTProtocol,
    OCPPProtocol,
    ProtocolRegistry,
    SimulationProtocol,
    build_modbus_endpoint_key,
    create_modbus_protocol,
)
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
        self.inventory = DeviceInventory(normalize_device_profile)
        self.devices = self.inventory.devices
        self.device_candidates = self.inventory.device_candidates
        self.protocol_registry = ProtocolRegistry(
            config,
            protocol_builders={
                'mqtt': MQTTProtocol,
                'ocpp': OCPPProtocol,
                'simulation': SimulationProtocol,
            },
            modbus_protocol_factory=create_modbus_protocol,
            modbus_endpoint_builder=build_modbus_endpoint_key,
        )
        self.protocols: Dict[str, ProtocolBase] = self.protocol_registry.protocols
        self.endpoint_protocols: Dict[str, ProtocolBase] = self.protocol_registry.endpoint_protocols

    def _normalize_device_info(self, device_info: Dict[str, Any]) -> Dict[str, Any]:
        return self.inventory.normalize(device_info)

    def _get_connector_view(self, device_id: str, *, include_candidates: bool = False) -> Optional[Dict[str, Any]]:
        if include_candidates:
            return self.inventory.get_candidate(device_id)
        return self.inventory.get_device(device_id)

    def _get_io_device_id(self, device_info: Dict[str, Any], fallback_device_id: str) -> str:
        if device_info.get('io_device_id') is not None:
            return str(device_info['io_device_id'])
        if device_info.get('protocol') == 'modbus':
            unit_id = device_info.get('unit_id', device_info.get('slave_id'))
            if unit_id is not None:
                return str(unit_id)
        return fallback_device_id
    
    def start(self):
        """启动设备管理器"""
        connected_protocols = self.protocol_registry.connect_all()

        if not connected_protocols:
            self.logger.warning("无可用协议连接，设备发现功能将不可用")
            return

        if 'simulation' in connected_protocols:
            self.refresh_protocol_candidates('simulation')
    
    def stop(self):
        """停止设备管理器"""
        self.protocol_registry.disconnect_all()
    
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
                        discovered_devices[device_id] = self._normalize_device_info(device_info)
                except Exception as e:
                    self.logger.error(f"{protocol_name}协议设备发现失败: {e}")
        
        # 更新设备列表
        self.devices.update(discovered_devices)
        self.logger.info(f"共发现{len(discovered_devices)}个设备")
        return discovered_devices

    def refresh_protocol_candidates(self, protocol_name: str, clear_active: bool = False) -> Dict[str, Dict[str, Any]]:
        protocol = self.protocols.get(protocol_name)
        if not protocol or not protocol.is_connected:
            return {}

        discovered_candidates: Dict[str, Dict[str, Any]] = {}
        try:
            protocol_devices = protocol.discover_devices()
            for device_id, device_info in protocol_devices.items():
                device_info['protocol'] = protocol_name
                normalized = self._normalize_device_info(device_info)
                discovered_candidates[device_id] = normalized
        except Exception as e:
            self.logger.error(f"{protocol_name}协议候选设备刷新失败: {e}")
            return {}

        candidates = self.inventory.replace_protocol_candidates(
            protocol_name,
            discovered_candidates,
            clear_active=clear_active,
        )
        self.logger.info(f"{protocol_name}协议刷新后共有{len(candidates)}个候选设备")
        return candidates

    def refresh_protocol_devices(self, protocol_name: str) -> Dict[str, Dict[str, Any]]:
        """刷新指定协议的设备清单，并移除该协议下已失效的旧设备。"""
        protocol = self.protocols.get(protocol_name)
        if not protocol or not protocol.is_connected:
            return {}

        discovered_devices: Dict[str, Dict[str, Any]] = {}
        try:
            protocol_devices = protocol.discover_devices()
            for device_id, device_info in protocol_devices.items():
                device_info['protocol'] = protocol_name
                discovered_devices[device_id] = self._normalize_device_info(device_info)
        except Exception as e:
            self.logger.error(f"{protocol_name}协议设备刷新失败: {e}")
            return {}

        self.inventory.replace_protocol_devices(protocol_name, discovered_devices)
        self.logger.info(f"{protocol_name}协议刷新后共有{len(discovered_devices)}个设备")
        return discovered_devices

    def register_device_candidate(self, device_info: Dict[str, Any]) -> bool:
        device_id = device_info.get('device_id')
        if not device_id:
            return False

        protocol_name = device_info.get('protocol')
        if protocol_name not in self.protocols:
            return False

        if self.inventory.register_candidate(device_info):
            self.logger.info(f"注册候选设备: {device_id}")
            return True
        return False

    def unregister_device_candidate(self, device_id: str) -> bool:
        if self.inventory.unregister_candidate(device_id):
            self.logger.info(f"删除候选设备: {device_id}")
            return True
        return False

    def activate_device(self, device_id: str) -> bool:
        if self.inventory.activate_device(device_id):
            self.logger.info(f"激活设备: {device_id}")
            return True
        return False
    
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
        if self.inventory.register_device(device_info):
            self.logger.info(f"手动注册设备: {device_id}")
            return True
        return False
    
    def unregister_device(self, device_id: str) -> bool:
        """注销设备
        
        Args:
            device_id: 设备ID
            
        Returns:
            bool: 注销是否成功
        """
        if self.inventory.unregister_device(device_id):
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
        return self.inventory.get_device(device_id)

    def get_device_candidate(self, device_id: str) -> Optional[Dict[str, Any]]:
        return self.inventory.get_candidate(device_id)

    def is_device_connected(self, device_id: str) -> bool:
        return self.inventory.is_connected(device_id)
    
    def get_devices(self, device_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取设备列表
        
        Args:
            device_type: 设备类型，None表示获取所有设备
            
        Returns:
            List[Dict[str, Any]]: 设备列表
        """
        return self.inventory.get_devices(device_type)

    def get_device_candidates(self, device_type: Optional[str] = None) -> List[Dict[str, Any]]:
        return self.inventory.get_candidates(device_type)

    def get_device_connectors(self, device_id: str, include_candidates: bool = False) -> List[Dict[str, Any]]:
        return self.inventory.get_connectors(device_id, include_candidates=include_candidates)
    
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
            protocol = self.protocol_registry.get_protocol_for_device(device_info)
            if protocol is None:
                self.logger.warning(f"协议不存在: {protocol_name}")
                return None

            if not protocol.is_connected:
                self.logger.warning(f"协议未连接: {protocol_name}")
                return None

            if not field_is_readable(device_info, register):
                self.logger.warning(f"设备字段不可读: {device_id}.{register}")
                return None
            
            io_device_id = self._get_io_device_id(device_info, device_id)
            protocol_register = resolve_protocol_read(device_info, register)
            raw_value = protocol.read_data(io_device_id, protocol_register)
            return normalize_field_value(device_info, register, raw_value)
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
            protocol = self.protocol_registry.get_protocol_for_device(device_info)
            if protocol is None:
                self.logger.warning(f"协议不存在: {protocol_name}")
                return False

            if not protocol.is_connected:
                self.logger.warning(f"协议未连接: {protocol_name}")
                return False

            if not field_is_writable(device_info, register):
                self.logger.warning(f"设备字段不可写: {device_id}.{register}")
                return False
            
            io_device_id = self._get_io_device_id(device_info, device_id)
            protocol_register = resolve_protocol_write(device_info, register)
            return protocol.write_data(io_device_id, protocol_register, value)
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
        return self.inventory.get_device_status(device_id)
    
    def update_device_status(self, device_id: str, status: str):
        """更新设备状态
        
        Args:
            device_id: 设备ID
            status: 新状态
        """
        if device_id in self.devices:
            self.inventory.update_device_status(device_id, status)
            self.logger.info(f"更新设备状态: {device_id} -> {status}")
