# 设备管理模块
from typing import Dict, Any, List, Optional
from .charger_layout import build_connector_views, normalize_charger_pile
from .point_tables import get_device_default_maps
from .protocol import ProtocolBase, ModbusProtocol, MQTTProtocol, OCPPProtocol, SimulationProtocol
from .register_map import resolve_read_register, resolve_write_register
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
        self.device_candidates: Dict[str, Dict[str, Any]] = {}
        self.protocols: Dict[str, ProtocolBase] = {}
        self._init_protocols()

    def _normalize_device_info(self, device_info: Dict[str, Any]) -> Dict[str, Any]:
        normalized = dict(device_info)
        default_maps = get_device_default_maps(normalized)
        for key, value in default_maps.items():
            if key in {"telemetry_map", "control_map"} and isinstance(value, dict):
                merged = dict(value)
                if isinstance(normalized.get(key), dict):
                    merged.update(normalized[key])
                normalized[key] = merged
            else:
                normalized.setdefault(key, value)

        protocol_name = normalized.get('protocol')

        if normalized.get('source') not in {'real', 'simulated'}:
            normalized['source'] = 'simulated' if protocol_name == 'simulation' else 'real'

        raw_status = str(normalized.get('status', 'online')).lower()
        normalized['status'] = 'offline' if raw_status == 'offline' else 'online'
        return normalize_charger_pile(normalized)

    def _get_connector_view(self, device_id: str, *, include_candidates: bool = False) -> Optional[Dict[str, Any]]:
        collections = [self.devices.values()]
        if include_candidates:
            collections.append(self.device_candidates.values())

        for collection in collections:
            for device_info in collection:
                for connector in build_connector_views(device_info):
                    if connector.get("device_id") == device_id:
                        return connector
        return None
    
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

        # 初始化Simulation协议
        if 'simulation' in self.config:
            self.protocols['simulation'] = SimulationProtocol(self.config['simulation'])
    
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

        if not connected_protocols:
            self.logger.warning("无可用协议连接，设备发现功能将不可用")
            return

        if 'simulation' in connected_protocols:
            self.refresh_protocol_candidates('simulation')
    
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

        stale_candidate_ids = [
            device_id
            for device_id, device_info in self.device_candidates.items()
            if device_info.get('protocol') == protocol_name
        ]
        for device_id in stale_candidate_ids:
            del self.device_candidates[device_id]

        if clear_active:
            stale_device_ids = [
                device_id
                for device_id, device_info in self.devices.items()
                if device_info.get('protocol') == protocol_name
            ]
            for device_id in stale_device_ids:
                del self.devices[device_id]

        for device_id, device_info in discovered_candidates.items():
            self.device_candidates[device_id] = device_info

        candidates = {
            device_id: device_info
            for device_id, device_info in self.device_candidates.items()
            if device_info.get('protocol') == protocol_name
        }
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

        stale_device_ids = [
            device_id
            for device_id, device_info in self.devices.items()
            if device_info.get('protocol') == protocol_name
        ]
        for device_id in stale_device_ids:
            del self.devices[device_id]

        self.devices.update(discovered_devices)
        self.logger.info(f"{protocol_name}协议刷新后共有{len(discovered_devices)}个设备")
        return discovered_devices

    def register_device_candidate(self, device_info: Dict[str, Any]) -> bool:
        device_id = device_info.get('device_id')
        if not device_id:
            return False

        protocol_name = device_info.get('protocol')
        if protocol_name not in self.protocols:
            return False

        normalized = self._normalize_device_info(device_info)
        if device_id in self.devices:
            return False

        self.device_candidates[device_id] = normalized
        self.logger.info(f"注册候选设备: {device_id}")
        return True

    def unregister_device_candidate(self, device_id: str) -> bool:
        if device_id in self.devices:
            return False
        if device_id in self.device_candidates:
            del self.device_candidates[device_id]
            self.logger.info(f"删除候选设备: {device_id}")
            return True
        return False

    def activate_device(self, device_id: str) -> bool:
        device_info = self.device_candidates.get(device_id)
        if not device_info or device_id in self.devices:
            return False

        self.devices[device_id] = device_info
        self.logger.info(f"激活设备: {device_id}")
        return True
    
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
        self.devices[device_id] = self._normalize_device_info(device_info)
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
        device = self.devices.get(device_id)
        if device:
            return device
        return self._get_connector_view(device_id)

    def get_device_candidate(self, device_id: str) -> Optional[Dict[str, Any]]:
        device = self.device_candidates.get(device_id)
        if device:
            return device
        return self._get_connector_view(device_id, include_candidates=True)

    def is_device_connected(self, device_id: str) -> bool:
        return device_id in self.devices or self._get_connector_view(device_id) is not None
    
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

    def get_device_candidates(self, device_type: Optional[str] = None) -> List[Dict[str, Any]]:
        if device_type:
            return [device for device in self.device_candidates.values() if device.get('type') == device_type]
        return list(self.device_candidates.values())

    def get_device_connectors(self, device_id: str, include_candidates: bool = False) -> List[Dict[str, Any]]:
        device_info = self.devices.get(device_id)
        if device_info is None and include_candidates:
            device_info = self.device_candidates.get(device_id)
        if not device_info:
            return []
        return build_connector_views(device_info)
    
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
            
            io_device_id = device_info.get('io_device_id', device_id)
            protocol_register = resolve_read_register(device_info, register)
            return protocol.read_data(io_device_id, protocol_register)
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
            
            io_device_id = device_info.get('io_device_id', device_id)
            protocol_register = resolve_write_register(device_info, register)
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
            self.devices[device_id]['status'] = 'offline' if str(status).lower() == 'offline' else 'online'
            self.logger.info(f"更新设备状态: {device_id} -> {status}")
