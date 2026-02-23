# 协议基类
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class ProtocolBase(ABC):
    """协议基类，定义所有协议的通用接口"""
    
    def __init__(self, config: Dict[str, Any]):
        """初始化协议实例
        
        Args:
            config: 协议配置参数
        """
        self.config = config
        self.connected = False
    
    @abstractmethod
    def connect(self) -> bool:
        """连接设备
        
        Returns:
            bool: 连接是否成功
        """
        pass
    
    @abstractmethod
    def disconnect(self) -> bool:
        """断开连接
        
        Returns:
            bool: 断开是否成功
        """
        pass
    
    @abstractmethod
    def read_data(self, device_id: str, register: str) -> Optional[Any]:
        """读取设备数据
        
        Args:
            device_id: 设备ID
            register: 寄存器地址或数据点
            
        Returns:
            Optional[Any]: 读取的数据，失败返回None
        """
        pass
    
    @abstractmethod
    def write_data(self, device_id: str, register: str, value: Any) -> bool:
        """写入设备数据
        
        Args:
            device_id: 设备ID
            register: 寄存器地址或数据点
            value: 要写入的值
            
        Returns:
            bool: 写入是否成功
        """
        pass
    
    @abstractmethod
    def discover_devices(self) -> Dict[str, Dict[str, Any]]:
        """发现设备
        
        Returns:
            Dict[str, Dict[str, Any]]: 发现的设备列表，键为设备ID，值为设备信息
        """
        pass
    
    @property
    def is_connected(self) -> bool:
        """是否已连接
        
        Returns:
            bool: 连接状态
        """
        return self.connected
