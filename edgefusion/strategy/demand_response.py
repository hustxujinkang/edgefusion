# 需求响应策略
from typing import Dict, Any
from datetime import datetime
from .base import StrategyBase


class DemandResponseStrategy(StrategyBase):
    """需求响应策略，用于响应电网的需求侧管理信号"""
    
    def __init__(self, config: Dict[str, Any], device_manager: Any):
        """初始化需求响应策略
        
        Args:
            config: 策略配置参数
            device_manager: 设备管理器实例
        """
        super().__init__(config, device_manager)
        self.response_levels = config.get('response_levels', {
            'level1': {'power_reduction': 10, 'duration': 30},  # 10%功率 reduction, 30分钟
            'level2': {'power_reduction': 20, 'duration': 60},  # 20%功率 reduction, 60分钟
            'level3': {'power_reduction': 30, 'duration': 120}  # 30%功率 reduction, 120分钟
        })
        self.current_event = None
        self.event_start_time = None
    
    def start(self) -> bool:
        """启动需求响应策略
        
        Returns:
            bool: 启动是否成功
        """
        try:
            self.enabled = True
            print("启动需求响应策略")
            return True
        except Exception as e:
            print(f"启动需求响应策略失败: {e}")
            return False
    
    def stop(self) -> bool:
        """停止需求响应策略
        
        Returns:
            bool: 停止是否成功
        """
        try:
            self.enabled = False
            self.current_event = None
            self.event_start_time = None
            print("停止需求响应策略")
            return True
        except Exception as e:
            print(f"停止需求响应策略失败: {e}")
            return False
    
    def execute(self) -> Dict[str, Any]:
        """执行需求响应策略
        
        Returns:
            Dict[str, Any]: 执行结果
        """
        if not self.enabled:
            return {'status': 'disabled', 'message': '策略未启用'}
        
        try:
            result = {
                'status': 'executed',
                'timestamp': datetime.now().isoformat(),
                'actions': []
            }
            
            # 检查当前是否有需求响应事件
            if self.current_event:
                # 检查事件是否结束
                if self._is_event_ended():
                    result['actions'].extend(self._end_event())
                    result['message'] = '需求响应事件结束'
                else:
                    # 继续执行当前事件
                    result['actions'].extend(self._execute_event())
                    result['message'] = f'执行需求响应事件: {self.current_event}'
            else:
                # 检查是否有新的需求响应信号
                # 这里简化处理，实际应从电网或上级系统获取信号
                # 模拟检测到新的需求响应事件
                # new_event = self._detect_new_event()
                # if new_event:
                #     self.current_event = new_event
                #     self.event_start_time = datetime.now()
                #     result['actions'].extend(self._start_event())
                #     result['message'] = f'开始需求响应事件: {new_event}'
                # else:
                result['message'] = '无需求响应事件'
            
            print(f"需求响应策略执行结果: {result}")
            return result
        except Exception as e:
            print(f"执行需求响应策略失败: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def get_status(self) -> Dict[str, Any]:
        """获取策略状态
        
        Returns:
            Dict[str, Any]: 策略状态
        """
        event_status = None
        if self.current_event:
            event_status = {
                'event': self.current_event,
                'start_time': self.event_start_time.isoformat() if self.event_start_time else None,
                'remaining_duration': self._get_remaining_duration()
            }
        
        return {
            'name': self.name,
            'enabled': self.enabled,
            'current_event': event_status,
            'response_levels': self.response_levels
        }
    
    def trigger_event(self, event_level: str) -> bool:
        """手动触发需求响应事件
        
        Args:
            event_level: 事件级别
            
        Returns:
            bool: 触发是否成功
        """
        if event_level not in self.response_levels:
            return False
        
        self.current_event = event_level
        self.event_start_time = datetime.now()
        print(f"手动触发需求响应事件: {event_level}")
        return True
    
    def _is_event_ended(self) -> bool:
        """检查需求响应事件是否结束
        
        Returns:
            bool: 事件是否结束
        """
        if not self.current_event or not self.event_start_time:
            return True
        
        duration = self.response_levels[self.current_event]['duration']
        elapsed_time = (datetime.now() - self.event_start_time).total_seconds() / 60
        return elapsed_time >= duration
    
    def _get_remaining_duration(self) -> int:
        """获取剩余事件持续时间
        
        Returns:
            int: 剩余时间（分钟）
        """
        if not self.current_event or not self.event_start_time:
            return 0
        
        duration = self.response_levels[self.current_event]['duration']
        elapsed_time = (datetime.now() - self.event_start_time).total_seconds() / 60
        remaining = max(0, duration - elapsed_time)
        return int(remaining)
    
    def _start_event(self) -> list:
        """开始需求响应事件
        
        Returns:
            list: 执行的操作列表
        """
        actions = []
        
        if not self.current_event:
            return actions
        
        reduction_percentage = self.response_levels[self.current_event]['power_reduction']
        
        # 1. 限制充电桩功率
        charging_stations = self._get_devices_by_type('charging_station')
        for device in charging_stations:
            device_id = device['device_id']
            # 指令充电桩降低功率
            power_limit = int(10000 * (1 - reduction_percentage / 100))  # 假设满功率为10kW
            self._write_device_data(device_id, 'power_limit', power_limit)
            actions.append({
                'device_id': device_id,
                'action': 'set_power_limit',
                'value': power_limit,
                'reason': f'需求响应事件，降低{reduction_percentage}%功率'
            })
        
        # 2. 调整储能设备运行模式
        energy_storage_devices = self._get_devices_by_type('energy_storage')
        for device in energy_storage_devices:
            device_id = device['device_id']
            # 指令储能设备放电，减少电网负荷
            self._write_device_data(device_id, 'mode', 'discharge')
            actions.append({
                'device_id': device_id,
                'action': 'set_mode',
                'value': 'discharge',
                'reason': '需求响应事件，储能放电减少电网负荷'
            })
        
        return actions
    
    def _execute_event(self) -> list:
        """执行需求响应事件
        
        Returns:
            list: 执行的操作列表
        """
        actions = []
        
        # 监控设备状态，确保功率 reduction 目标达成
        # 这里简化处理，实际应根据设备反馈调整控制
        
        return actions
    
    def _end_event(self) -> list:
        """结束需求响应事件
        
        Returns:
            list: 执行的操作列表
        """
        actions = []
        
        # 1. 恢复充电桩功率
        charging_stations = self._get_devices_by_type('charging_station')
        for device in charging_stations:
            device_id = device['device_id']
            # 指令充电桩恢复满功率
            self._write_device_data(device_id, 'power_limit', 10000)  # 假设满功率为10kW
            actions.append({
                'device_id': device_id,
                'action': 'set_power_limit',
                'value': 10000,
                'reason': '需求响应事件结束，恢复满功率'
            })
        
        # 2. 恢复储能设备运行模式
        energy_storage_devices = self._get_devices_by_type('energy_storage')
        for device in energy_storage_devices:
            device_id = device['device_id']
            # 指令储能设备恢复自动模式
            self._write_device_data(device_id, 'mode', 'auto')
            actions.append({
                'device_id': device_id,
                'action': 'set_mode',
                'value': 'auto',
                'reason': '需求响应事件结束，恢复自动模式'
            })
        
        # 清除事件状态
        self.current_event = None
        self.event_start_time = None
        
        return actions
    
    def _detect_new_event(self) -> str:
        """检测新的需求响应事件
        
        Returns:
            str: 事件级别，None表示无新事件
        """
        # 模拟检测需求响应事件
        # 实际应从电网或上级系统获取信号
        return None
