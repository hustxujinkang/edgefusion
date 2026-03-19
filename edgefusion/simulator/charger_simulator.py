# 充电桩模拟器
from .base import DeviceSimulator
import time


class ChargerSimulator(DeviceSimulator):
    """充电桩模拟器"""
    
    def __init__(
        self,
        device_id: str,
        auto_session_changes: bool = True,
        initial_status: str = "Available",
        charging_rate_w: float = 3000.0,
        max_power_w: float = 7000.0,
        min_power_w: float = 1000.0,
        power_limit_w: float | None = None,
    ):
        """初始化充电桩模拟器
        
        Args:
            device_id: 设备ID
        """
        super().__init__(device_id, "charging_station")
        self.auto_session_changes = auto_session_changes
        # 初始化充电桩数据
        self.data = {
            'status': initial_status,  # 状态
            'power': 0.0,  # 功率（W）
            'energy': 0.0,  # 能量（kWh）
            'voltage': 220.0,  # 电压（V）
            'current': 0.0,  # 电流（A）
            'temperature': 25.0,  # 温度（℃）
            'mode': 'auto',  # 模式
            'power_limit': float(power_limit_w if power_limit_w is not None else max_power_w),  # 功率限制（W）
            'max_power': float(max_power_w),
            'min_power': float(min_power_w),
            'connector_id': 1,  # 连接器ID
            'session_id': None  # 会话ID
        }
        self.last_update_time = time.time()
        self.charging_rate = float(charging_rate_w)  # 充电速率（W）
        self.session_start_time = None
        if initial_status == 'Charging':
            self.set_data('status', 'Charging')
    
    def get_data(self, register: str) -> float:
        """获取充电桩数据
        
        Args:
            register: 数据点
            
        Returns:
            float: 数据值
        """
        return self.data.get(register, 0.0)
    
    def set_data(self, register: str, value: float) -> bool:
        """设置充电桩数据
        
        Args:
            register: 数据点
            value: 数据值
            
        Returns:
            bool: 设置是否成功
        """
        if register in ['status', 'mode', 'power_limit']:
            self.data[register] = value
            self.last_updated = time.time()
            
            # 状态控制
            if register == 'status':
                if value == 'Charging':
                    self.data['power'] = min(self.charging_rate, self.data['power_limit'], self.data['max_power'])
                    self.session_start_time = time.time()
                    self.data['session_id'] = f"session_{int(time.time())}"
                elif value == 'Available':
                    self.data['power'] = 0.0
                    self.session_start_time = None
                    self.data['session_id'] = None
            return True
        return False
    
    def update(self):
        """更新充电桩状态
        
        根据状态更新功率和能量
        """
        current_time = time.time()
        elapsed = current_time - self.last_update_time
        
        # 更新时间
        self.last_update_time = current_time
        self.last_updated = current_time
        
        # 根据状态更新功率和能量
        if self.data['status'] == 'Charging':
            # 充电中
            power = min(self.charging_rate, self.data['power_limit'], self.data['max_power'])
            self.data['power'] = round(power, 2)
            self.data['current'] = round(power / self.data['voltage'], 2)
            
            # 更新能量
            energy_increase = power * elapsed / 3600 / 1000  # 转换为kWh
            self.data['energy'] = round(self.data['energy'] + energy_increase, 2)
            
            # 温度升高
            self.data['temperature'] = round(self.data['temperature'] + 0.1, 1)
            self.data['temperature'] = min(40, self.data['temperature'])
        elif self.data['status'] == 'Available':
            # 空闲
            self.data['power'] = 0.0
            self.data['current'] = 0.0
            
            # 温度降低
            self.data['temperature'] = round(self.data['temperature'] - 0.1, 1)
            self.data['temperature'] = max(20, self.data['temperature'])
        
        if self.auto_session_changes and self.data['status'] == 'Charging' and self.data['energy'] > 5.0:
            self.set_data('status', 'Available')
    
    def get_status(self) -> str:
        """获取充电桩状态
        
        Returns:
            str: 充电桩状态
        """
        return self.data['status']
    
    def get_power(self) -> float:
        """获取充电功率
        
        Returns:
            float: 充电功率
        """
        return self.data['power']
