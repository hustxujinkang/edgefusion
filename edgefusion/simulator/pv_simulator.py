# 光伏模拟器
from .base import DeviceSimulator
import time
import random


class PVSimulator(DeviceSimulator):
    """光伏模拟器"""
    
    def __init__(self, device_id: str):
        """初始化光伏模拟器
        
        Args:
            device_id: 设备ID
        """
        super().__init__(device_id, "pv")
        # 初始化光伏数据
        self.data = {
            'power': 0.0,  # 功率（W）
            'energy': 0.0,  # 能量（kWh）
            'voltage': 220.0,  # 电压（V）
            'current': 0.0,  # 电流（A）
            'temperature': 25.0,  # 温度（℃）
            'status': 'normal',  # 状态
            'mode': 'auto'  # 模式
        }
        self.last_update_time = time.time()
        self.max_power = 5000.0  # 最大功率（W）
    
    def get_data(self, register: str) -> float:
        """获取光伏数据
        
        Args:
            register: 数据点
            
        Returns:
            float: 数据值
        """
        return self.data.get(register, 0.0)
    
    def set_data(self, register: str, value: float) -> bool:
        """设置光伏数据
        
        Args:
            register: 数据点
            value: 数据值
            
        Returns:
            bool: 设置是否成功
        """
        if register in ['mode', 'status']:
            self.data[register] = value
            self.last_updated = time.time()
            return True
        # 其他数据点为只读
        return False
    
    def update(self):
        """更新光伏状态
        
        根据时间模拟光伏功率变化
        """
        current_time = time.time()
        elapsed = current_time - self.last_update_time
        
        # 更新时间
        self.last_update_time = current_time
        self.last_updated = current_time
        
        # 获取当前小时
        hour = time.localtime(current_time).tm_hour
        
        # 根据时间模拟光伏功率
        if 6 <= hour < 18:
            # 白天，有阳光
            # 功率随时间变化，中午最高
            noon = 12
            power_factor = 1 - abs(hour - noon) / 6
            base_power = self.max_power * power_factor
            # 添加随机波动
            power = base_power * (0.8 + 0.2 * random.random())
            
            # 更新功率和电流
            self.data['power'] = round(power, 2)
            self.data['current'] = round(power / self.data['voltage'], 2)
            
            # 更新能量
            energy_increase = power * elapsed / 3600 / 1000  # 转换为kWh
            self.data['energy'] = round(self.data['energy'] + energy_increase, 2)
            
            # 更新状态
            self.data['status'] = 'normal'
        else:
            # 夜晚，无阳光
            self.data['power'] = 0.0
            self.data['current'] = 0.0
            self.data['status'] = 'sleep'
        
        # 随机波动温度
        self.data['temperature'] = round(20 + 10 * random.random(), 1)
    
    def get_power(self) -> float:
        """获取当前功率
        
        Returns:
            float: 功率值
        """
        return self.data['power']
    
    def get_energy(self) -> float:
        """获取累计能量
        
        Returns:
            float: 能量值
        """
        return self.data['energy']
