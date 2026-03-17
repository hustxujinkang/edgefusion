# 自发自用策略
from typing import Dict, Any
from datetime import datetime
from .base import StrategyBase
from ..logger import get_logger


class SelfConsumptionStrategy(StrategyBase):
    """自发自用策略，用于最大化利用本地光伏发电"""
    
    def __init__(self, config: Dict[str, Any], device_manager: Any):
        """初始化自发自用策略
        
        Args:
            config: 策略配置参数
            device_manager: 设备管理器实例
        """
        super().__init__(config, device_manager)
        self.logger = get_logger('SelfConsumptionStrategy')
        self.soc_target = config.get('soc_target', 80)  # 储能SOC目标（%）
        self.min_soc = config.get('min_soc', 20)  # 储能最小SOC（%）
        self.pv_power_threshold = config.get('pv_power_threshold', 1000)  # 光伏功率阈值（W）
        self.grid_import_limit = config.get('grid_import_limit', 5000)  # 电网导入功率限制（W）
    
    def start(self) -> bool:
        """启动自发自用策略
        
        Returns:
            bool: 启动是否成功
        """
        try:
            self.enabled = True
            self.logger.info("启动自发自用策略")
            return True
        except Exception as e:
            self.logger.error("启动自发自用策略失败: %s", e)
            return False
    
    def stop(self) -> bool:
        """停止自发自用策略
        
        Returns:
            bool: 停止是否成功
        """
        try:
            self.enabled = False
            self.logger.info("停止自发自用策略")
            return True
        except Exception as e:
            self.logger.error("停止自发自用策略失败: %s", e)
            return False
    
    def execute(self) -> Dict[str, Any]:
        """执行自发自用策略
        
        Returns:
            Dict[str, Any]: 执行结果
        """
        if not self.enabled:
            return {'status': 'disabled', 'message': '策略未启用'}
        
        try:
            # 获取设备状态
            pv_power = self._get_pv_power()
            storage_soc = self._get_storage_soc()
            load_power = self._get_load_power()
            
            result = {
                'status': 'executed',
                'timestamp': datetime.now().isoformat(),
                'system_status': {
                    'pv_power': pv_power,
                    'storage_soc': storage_soc,
                    'load_power': load_power
                },
                'actions': []
            }
            
            # 根据系统状态执行控制策略
            if pv_power > self.pv_power_threshold:
                # 光伏功率充足
                excess_power = pv_power - load_power
                
                if excess_power > 0:
                    # 有多余光伏功率
                    if storage_soc < self.soc_target:
                        # 储能未充满，优先充电
                        result['actions'].extend(self._charge_storage(excess_power))
                    else:
                        # 储能已充满，可考虑其他用途
                        result['actions'].extend(self._optimize_excess_power(excess_power))
            else:
                # 光伏功率不足
                power_shortage = load_power - pv_power
                
                if power_shortage > 0:
                    # 需要补充功率
                    if storage_soc > self.min_soc:
                        # 储能有足够电量，优先放电
                        result['actions'].extend(self._discharge_storage(power_shortage))
                    else:
                        # 储能电量不足，从电网获取
                        result['actions'].extend(self._import_from_grid(power_shortage))
            
            self.logger.debug("自发自用策略执行结果: %s", result)
            return result
        except Exception as e:
            self.logger.error("执行自发自用策略失败: %s", e)
            return {'status': 'error', 'message': str(e)}
    
    def get_status(self) -> Dict[str, Any]:
        """获取策略状态
        
        Returns:
            Dict[str, Any]: 策略状态
        """
        # 获取设备状态
        pv_power = self._get_pv_power()
        storage_soc = self._get_storage_soc()
        load_power = self._get_load_power()
        
        return {
            'name': self.name,
            'enabled': self.enabled,
            'config': {
                'soc_target': self.soc_target,
                'min_soc': self.min_soc,
                'pv_power_threshold': self.pv_power_threshold,
                'grid_import_limit': self.grid_import_limit
            },
            'system_status': {
                'pv_power': pv_power,
                'storage_soc': storage_soc,
                'load_power': load_power
            }
        }
    
    def _get_pv_power(self) -> float:
        """获取光伏输出功率
        
        Returns:
            float: 光伏输出功率（W）
        """
        # 模拟获取光伏功率
        # 实际应从光伏设备读取数据
        return 5000.0  # 假设当前光伏功率为5kW
    
    def _get_storage_soc(self) -> float:
        """获取储能SOC
        
        Returns:
            float: 储能SOC（%）
        """
        # 模拟获取储能SOC
        # 实际应从储能设备读取数据
        return 50.0  # 假设当前储能SOC为50%
    
    def _get_load_power(self) -> float:
        """获取负载功率
        
        Returns:
            float: 负载功率（W）
        """
        # 模拟获取负载功率
        # 实际应计算或测量负载功率
        return 3000.0  # 假设当前负载功率为3kW
    
    def _charge_storage(self, power: float) -> list:
        """控制储能充电
        
        Args:
            power: 充电功率（W）
            
        Returns:
            list: 执行的操作列表
        """
        actions = []
        
        # 控制储能设备充电
        energy_storage_devices = self._get_devices_by_type('energy_storage')
        for device in energy_storage_devices:
            device_id = device['device_id']
            # 指令储能设备充电
            self._write_device_data(device_id, 'mode', 'charge')
            self._write_device_data(device_id, 'charge_power', power // len(energy_storage_devices))
            actions.append({
                'device_id': device_id,
                'action': 'set_mode',
                'value': 'charge',
                'reason': f'光伏功率充足，储能充电'
            })
            actions.append({
                'device_id': device_id,
                'action': 'set_charge_power',
                'value': power // len(energy_storage_devices),
                'reason': f'设置充电功率'
            })
        
        return actions
    
    def _discharge_storage(self, power: float) -> list:
        """控制储能放电
        
        Args:
            power: 放电功率（W）
            
        Returns:
            list: 执行的操作列表
        """
        actions = []
        
        # 控制储能设备放电
        energy_storage_devices = self._get_devices_by_type('energy_storage')
        for device in energy_storage_devices:
            device_id = device['device_id']
            # 指令储能设备放电
            self._write_device_data(device_id, 'mode', 'discharge')
            self._write_device_data(device_id, 'discharge_power', power // len(energy_storage_devices))
            actions.append({
                'device_id': device_id,
                'action': 'set_mode',
                'value': 'discharge',
                'reason': f'光伏功率不足，储能放电'
            })
            actions.append({
                'device_id': device_id,
                'action': 'set_discharge_power',
                'value': power // len(energy_storage_devices),
                'reason': f'设置放电功率'
            })
        
        return actions
    
    def _import_from_grid(self, power: float) -> list:
        """从电网导入功率
        
        Args:
            power: 导入功率（W）
            
        Returns:
            list: 执行的操作列表
        """
        actions = []
        
        # 限制电网导入功率
        import_power = min(power, self.grid_import_limit)
        
        # 这里简化处理，实际应通过能量管理系统控制电网导入
        actions.append({
            'device_id': 'grid',
            'action': 'set_import_power',
            'value': import_power,
            'reason': f'光伏功率不足且储能电量低，从电网导入功率'
        })
        
        return actions
    
    def _optimize_excess_power(self, power: float) -> list:
        """优化多余光伏功率
        
        Args:
            power: 多余功率（W）
            
        Returns:
            list: 执行的操作列表
        """
        actions = []
        
        # 优先给充电桩充电
        charging_stations = self._get_devices_by_type('charging_station')
        for device in charging_stations:
            device_id = device['device_id']
            # 指令充电桩使用多余光伏功率
            self._write_device_data(device_id, 'power_limit', power // len(charging_stations))
            actions.append({
                'device_id': device_id,
                'action': 'set_power_limit',
                'value': power // len(charging_stations),
                'reason': f'光伏功率过剩，用于充电桩充电'
            })
        
        return actions
