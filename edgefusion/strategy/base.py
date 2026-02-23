# 策略基类
from abc import ABC, abstractmethod
from typing import Dict, Any, List
from ..device_manager import DeviceManager


class StrategyBase(ABC):
    """策略基类，定义所有策略的通用接口"""
    
    def __init__(self, config: Dict[str, Any], device_manager: DeviceManager):
        """初始化策略实例
        
        Args:
            config: 策略配置参数
            device_manager: 设备管理器实例
        """
        self.config = config
        self.device_manager = device_manager
        self.enabled = False
        self.name = self.__class__.__name__
    
    @abstractmethod
    def start(self) -> bool:
        """启动策略
        
        Returns:
            bool: 启动是否成功
        """
        pass
    
    @abstractmethod
    def stop(self) -> bool:
        """停止策略
        
        Returns:
            bool: 停止是否成功
        """
        pass
    
    @abstractmethod
    def execute(self) -> Dict[str, Any]:
        """执行策略
        
        Returns:
            Dict[str, Any]: 执行结果
        """
        pass
    
    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """获取策略状态
        
        Returns:
            Dict[str, Any]: 策略状态
        """
        pass
    
    def is_enabled(self) -> bool:
        """策略是否启用
        
        Returns:
            bool: 策略启用状态
        """
        return self.enabled
    
    def set_enabled(self, enabled: bool):
        """设置策略启用状态
        
        Args:
            enabled: 是否启用
        """
        self.enabled = enabled
    
    def get_config(self) -> Dict[str, Any]:
        """获取策略配置
        
        Returns:
            Dict[str, Any]: 策略配置
        """
        return self.config
    
    def update_config(self, config: Dict[str, Any]):
        """更新策略配置
        
        Args:
            config: 新的策略配置
        """
        self.config.update(config)
    
    def _get_devices_by_type(self, device_type: str) -> List[Dict[str, Any]]:
        """根据设备类型获取设备列表
        
        Args:
            device_type: 设备类型
            
        Returns:
            List[Dict[str, Any]]: 设备列表
        """
        return self.device_manager.get_devices(device_type)
    
    def _read_device_data(self, device_id: str, register: str) -> Any:
        """读取设备数据
        
        Args:
            device_id: 设备ID
            register: 数据点
            
        Returns:
            Any: 读取的数据
        """
        return self.device_manager.read_device_data(device_id, register)
    
    def _write_device_data(self, device_id: str, register: str, value: Any) -> bool:
        """写入设备数据
        
        Args:
            device_id: 设备ID
            register: 数据点
            value: 要写入的值
            
        Returns:
            bool: 写入是否成功
        """
        return self.device_manager.write_device_data(device_id, register, value)
