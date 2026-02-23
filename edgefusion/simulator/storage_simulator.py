# 储能模拟器
from .base import DeviceSimulator
import time


class StorageSimulator(DeviceSimulator):
    """储能模拟器"""
    
    def __init__(self, device_id: str):
        """初始化储能模拟器
        
        Args:
            device_id: 设备ID
        """
        super().__init__(device_id, "energy_storage")
        # 初始化储能数据
        self.data = {
            'soc': 50.0,  # 荷电状态（%）
            'power': 0.0,  # 功率（W），正数为充电，负数为放电
            'voltage': 240.0,  # 电压（V）
            'current': 0.0,  # 电流（A）
            'temperature': 25.0,  # 温度（℃）
            'status': 'normal',  # 状态
            'mode': 'auto',  # 模式
            'charge_power': 2000.0,  # 充电功率（W）
            'discharge_power': 2000.0  # 放电功率（W）
        }
        self.last_update_time = time.time()
        self.capacity = 10000  # 容量（Wh）
        self.efficiency = 0.9  # 充放电效率
    
    def get_data(self, register: str) -> float:
        """获取储能数据
        
        Args:
            register: 数据点
            
        Returns:
            float: 数据值
        """
        return self.data.get(register, 0.0)
    
    def set_data(self, register: str, value: float) -> bool:
        """设置储能数据
        
        Args:
            register: 数据点
            value: 数据值
            
        Returns:
            bool: 设置是否成功
        """
        if register in ['mode', 'status', 'charge_power', 'discharge_power']:
            self.data[register] = value
            self.last_updated = time.time()
            return True
        elif register == 'mode':
            # 模式控制
            self.data['mode'] = value
            if value == 'charge':
                self.data['power'] = self.data['charge_power']
            elif value == 'discharge':
                self.data['power'] = -self.data['discharge_power']
            elif value == 'stop':
                self.data['power'] = 0.0
            self.last_updated = time.time()
            return True
        return False
    
    def update(self):
        """更新储能状态
        
        根据功率更新SOC
        """
        current_time = time.time()
        elapsed = current_time - self.last_update_time
        
        # 更新时间
        self.last_update_time = current_time
        self.last_updated = current_time
        
        # 根据功率更新SOC
        power = self.data['power']
        if power != 0:
            # 计算能量变化
            energy_change = power * elapsed / 3600  # 转换为Wh
            
            # 考虑效率
            if power > 0:
                # 充电
                energy_change *= self.efficiency
            else:
                # 放电
                energy_change /= self.efficiency
            
            # 更新SOC
            soc_change = (energy_change / self.capacity) * 100
            new_soc = self.data['soc'] + soc_change
            
            # 限制SOC范围
            new_soc = max(0, min(100, new_soc))
            self.data['soc'] = round(new_soc, 2)
            
            # 更新电流
            self.data['current'] = round(abs(power) / self.data['voltage'], 2)
        
        # 温度缓慢变化
        self.data['temperature'] = round(self.data['temperature'] + (0.1 if power != 0 else -0.1), 1)
        self.data['temperature'] = max(20, min(40, self.data['temperature']))
        
        # 根据SOC更新状态
        if self.data['soc'] <= 10:
            self.data['status'] = 'low_soc'
        elif self.data['soc'] >= 90:
            self.data['status'] = 'high_soc'
        else:
            self.data['status'] = 'normal'
    
    def get_soc(self) -> float:
        """获取SOC
        
        Returns:
            float: SOC值
        """
        return self.data['soc']
    
    def get_power(self) -> float:
        """获取功率
        
        Returns:
            float: 功率值
        """
        return self.data['power']
