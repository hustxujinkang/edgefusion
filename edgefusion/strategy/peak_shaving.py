# 削峰填谷策略
from typing import Dict, Any
from datetime import datetime
from .base import StrategyBase
from ..logger import get_logger


class PeakShavingStrategy(StrategyBase):
    """削峰填谷策略，用于平衡电网负载"""
    
    def __init__(self, config: Dict[str, Any], device_manager: Any):
        """初始化削峰填谷策略
        
        Args:
            config: 策略配置参数
            device_manager: 设备管理器实例
        """
        super().__init__(config, device_manager)
        self.logger = get_logger('PeakShavingStrategy')
        self.peak_hours = config.get('peak_hours', ['18:00-22:00'])
        self.valley_hours = config.get('valley_hours', ['00:00-06:00'])
        self.peak_power_limit = config.get('peak_power_limit', 10000)  # 峰值功率限制（W）
        self.valley_power_target = config.get('valley_power_target', 5000)  # 谷值功率目标（W）
    
    def start(self) -> bool:
        """启动削峰填谷策略
        
        Returns:
            bool: 启动是否成功
        """
        try:
            self.enabled = True
            self.logger.info(f"启动削峰填谷策略，峰值时段: {self.peak_hours}, 谷值时段: {self.valley_hours}")
            return True
        except Exception as e:
            self.logger.error(f"启动削峰填谷策略失败: {e}")
            return False
    
    def stop(self) -> bool:
        """停止削峰填谷策略
        
        Returns:
            bool: 停止是否成功
        """
        try:
            self.enabled = False
            self.logger.info("停止削峰填谷策略")
            return True
        except Exception as e:
            self.logger.error(f"停止削峰填谷策略失败: {e}")
            return False
    
    def execute(self) -> Dict[str, Any]:
        """执行削峰填谷策略
        
        Returns:
            Dict[str, Any]: 执行结果
        """
        if not self.enabled:
            return {'status': 'disabled', 'message': '策略未启用'}
        
        try:
            current_time = datetime.now().strftime('%H:%M')
            time_slot = self._get_current_time_slot(current_time)
            
            result = {
                'status': 'executed',
                'time_slot': time_slot,
                'timestamp': datetime.now().isoformat(),
                'actions': []
            }
            
            # 根据当前时段执行不同的控制策略
            if time_slot == 'peak':
                result['actions'].extend(self._execute_peak_control())
            elif time_slot == 'valley':
                result['actions'].extend(self._execute_valley_control())
            else:
                result['actions'].extend(self._execute_normal_control())
            
            self.logger.info(f"削峰填谷策略执行结果: {result}")
            return result
        except Exception as e:
            self.logger.error(f"执行削峰填谷策略失败: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def get_status(self) -> Dict[str, Any]:
        """获取策略状态
        
        Returns:
            Dict[str, Any]: 策略状态
        """
        current_time = datetime.now().strftime('%H:%M')
        time_slot = self._get_current_time_slot(current_time)
        
        return {
            'name': self.name,
            'enabled': self.enabled,
            'current_time_slot': time_slot,
            'peak_hours': self.peak_hours,
            'valley_hours': self.valley_hours,
            'peak_power_limit': self.peak_power_limit,
            'valley_power_target': self.valley_power_target
        }
    
    def _get_current_time_slot(self, current_time: str) -> str:
        """获取当前时间段类型
        
        Args:
            current_time: 当前时间，格式为'HH:MM'
            
        Returns:
            str: 时间段类型，'peak'（峰值）、'valley'（谷值）或'normal'（正常）
        """
        # 检查是否在峰值时段
        for peak_hour in self.peak_hours:
            start, end = peak_hour.split('-')
            if start <= current_time <= end:
                return 'peak'
        
        # 检查是否在谷值时段
        for valley_hour in self.valley_hours:
            start, end = valley_hour.split('-')
            if start <= current_time <= end:
                return 'valley'
        
        return 'normal'
    
    def _execute_peak_control(self) -> list:
        """执行峰值时段控制
        
        Returns:
            list: 执行的操作列表
        """
        actions = []
        
        # 1. 限制光伏输出（如果需要）
        # 2. 优先使用储能放电
        # 3. 限制或暂停充电桩充电
        
        # 模拟控制操作
        # 实际应根据设备状态和策略配置执行具体控制
        
        # 控制储能设备放电
        energy_storage_devices = self._get_devices_by_type('energy_storage')
        for device in energy_storage_devices:
            device_id = device['device_id']
            # 指令储能设备放电
            self._write_device_data(device_id, 'mode', 'discharge')
            actions.append({
                'device_id': device_id,
                'action': 'set_mode',
                'value': 'discharge',
                'reason': '峰值时段优先使用储能'
            })
        
        # 限制充电桩功率
        charging_stations = self._get_devices_by_type('charging_station')
        for device in charging_stations:
            device_id = device['device_id']
            # 指令充电桩降低功率
            self._write_device_data(device_id, 'power_limit', self.peak_power_limit // len(charging_stations))
            actions.append({
                'device_id': device_id,
                'action': 'set_power_limit',
                'value': self.peak_power_limit // len(charging_stations),
                'reason': '峰值时段限制充电功率'
            })
        
        return actions
    
    def _execute_valley_control(self) -> list:
        """执行谷值时段控制
        
        Returns:
            list: 执行的操作列表
        """
        actions = []
        
        # 1. 优先储能充电
        # 2. 允许充电桩满功率充电
        # 3. 光伏正常发电
        
        # 模拟控制操作
        
        # 控制储能设备充电
        energy_storage_devices = self._get_devices_by_type('energy_storage')
        for device in energy_storage_devices:
            device_id = device['device_id']
            # 指令储能设备充电
            self._write_device_data(device_id, 'mode', 'charge')
            actions.append({
                'device_id': device_id,
                'action': 'set_mode',
                'value': 'charge',
                'reason': '谷值时段储能充电'
            })
        
        # 解除充电桩功率限制
        charging_stations = self._get_devices_by_type('charging_station')
        for device in charging_stations:
            device_id = device['device_id']
            # 指令充电桩恢复满功率
            self._write_device_data(device_id, 'power_limit', 10000)  # 假设满功率为10kW
            actions.append({
                'device_id': device_id,
                'action': 'set_power_limit',
                'value': 10000,
                'reason': '谷值时段解除充电功率限制'
            })
        
        return actions
    
    def _execute_normal_control(self) -> list:
        """执行正常时段控制
        
        Returns:
            list: 执行的操作列表
        """
        actions = []
        
        # 1. 光伏正常发电
        # 2. 储能根据SOC自动调整
        # 3. 充电桩正常充电
        
        # 模拟控制操作
        
        # 控制储能设备根据SOC自动调整
        energy_storage_devices = self._get_devices_by_type('energy_storage')
        for device in energy_storage_devices:
            device_id = device['device_id']
            # 指令储能设备自动模式
            self._write_device_data(device_id, 'mode', 'auto')
            actions.append({
                'device_id': device_id,
                'action': 'set_mode',
                'value': 'auto',
                'reason': '正常时段储能自动模式'
            })
        
        return actions
