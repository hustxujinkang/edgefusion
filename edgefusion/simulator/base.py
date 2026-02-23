# 设备模拟器基类
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import time
import random


class DeviceSimulator(ABC):
    """设备模拟器基类"""
    
    def __init__(self, device_id: str, device_type: str):
        """初始化设备模拟器
        
        Args:
            device_id: 设备ID
            device_type: 设备类型
        """
        self.device_id = device_id
        self.device_type = device_type
        self.status = "online"
        self.created_at = time.time()
        self.last_updated = time.time()
        self.data: Dict[str, Any] = {}
    
    @abstractmethod
    def get_data(self, register: str) -> Optional[Any]:
        """获取设备数据
        
        Args:
            register: 数据点
            
        Returns:
            Optional[Any]: 数据值
        """
        pass
    
    @abstractmethod
    def set_data(self, register: str, value: Any) -> bool:
        """设置设备数据
        
        Args:
            register: 数据点
            value: 数据值
            
        Returns:
            bool: 设置是否成功
        """
        pass
    
    @abstractmethod
    def update(self):
        """更新设备状态"""
        pass
    
    def get_status(self) -> str:
        """获取设备状态
        
        Returns:
            str: 设备状态
        """
        return self.status
    
    def set_status(self, status: str):
        """设置设备状态
        
        Args:
            status: 设备状态
        """
        self.status = status
        self.last_updated = time.time()
    
    def get_info(self) -> Dict[str, Any]:
        """获取设备信息
        
        Returns:
            Dict[str, Any]: 设备信息
        """
        return {
            'device_id': self.device_id,
            'device_type': self.device_type,
            'status': self.status,
            'created_at': self.created_at,
            'last_updated': self.last_updated
        }
    
    def generate_random_value(self, min_val: float, max_val: float) -> float:
        """生成随机值
        
        Args:
            min_val: 最小值
            max_val: 最大值
            
        Returns:
            float: 随机值
        """
        return random.uniform(min_val, max_val)
