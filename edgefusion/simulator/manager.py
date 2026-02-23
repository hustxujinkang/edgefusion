# 设备模拟器管理器
from typing import Dict, List, Optional
from .pv_simulator import PVSimulator
from .storage_simulator import StorageSimulator
from .charger_simulator import ChargerSimulator


class SimulatorManager:
    """设备模拟器管理器"""
    
    def __init__(self):
        """初始化模拟器管理器"""
        self.simulators: Dict[str, Any] = {}
        self.device_counter = 0
    
    def create_pv_simulator(self, device_id: Optional[str] = None) -> PVSimulator:
        """创建光伏模拟器
        
        Args:
            device_id: 设备ID，None则自动生成
            
        Returns:
            PVSimulator: 光伏模拟器实例
        """
        if not device_id:
            device_id = f"pv_{self.device_counter}"
            self.device_counter += 1
        
        simulator = PVSimulator(device_id)
        self.simulators[device_id] = simulator
        return simulator
    
    def create_storage_simulator(self, device_id: Optional[str] = None) -> StorageSimulator:
        """创建储能模拟器
        
        Args:
            device_id: 设备ID，None则自动生成
            
        Returns:
            StorageSimulator: 储能模拟器实例
        """
        if not device_id:
            device_id = f"storage_{self.device_counter}"
            self.device_counter += 1
        
        simulator = StorageSimulator(device_id)
        self.simulators[device_id] = simulator
        return simulator
    
    def create_charger_simulator(self, device_id: Optional[str] = None) -> ChargerSimulator:
        """创建充电桩模拟器
        
        Args:
            device_id: 设备ID，None则自动生成
            
        Returns:
            ChargerSimulator: 充电桩模拟器实例
        """
        if not device_id:
            device_id = f"charger_{self.device_counter}"
            self.device_counter += 1
        
        simulator = ChargerSimulator(device_id)
        self.simulators[device_id] = simulator
        return simulator
    
    def get_simulator(self, device_id: str) -> Optional[Any]:
        """获取模拟器
        
        Args:
            device_id: 设备ID
            
        Returns:
            Optional[Any]: 模拟器实例
        """
        return self.simulators.get(device_id)
    
    def get_all_simulators(self) -> List[Any]:
        """获取所有模拟器
        
        Returns:
            List[Any]: 模拟器实例列表
        """
        return list(self.simulators.values())
    
    def get_simulators_by_type(self, device_type: str) -> List[Any]:
        """根据类型获取模拟器
        
        Args:
            device_type: 设备类型
            
        Returns:
            List[Any]: 模拟器实例列表
        """
        return [sim for sim in self.simulators.values() if sim.device_type == device_type]
    
    def remove_simulator(self, device_id: str) -> bool:
        """移除模拟器
        
        Args:
            device_id: 设备ID
            
        Returns:
            bool: 移除是否成功
        """
        if device_id in self.simulators:
            del self.simulators[device_id]
            return True
        return False
    
    def update_all(self):
        """更新所有模拟器状态"""
        for simulator in self.simulators.values():
            simulator.update()
    
    def get_simulator_info(self, device_id: str) -> Optional[Dict[str, Any]]:
        """获取模拟器信息
        
        Args:
            device_id: 设备ID
            
        Returns:
            Optional[Dict[str, Any]]: 模拟器信息
        """
        simulator = self.get_simulator(device_id)
        if simulator:
            info = simulator.get_info()
            info['data'] = simulator.data
            return info
        return None
    
    def get_all_simulator_info(self) -> Dict[str, Dict[str, Any]]:
        """获取所有模拟器信息
        
        Returns:
            Dict[str, Dict[str, Any]]: 所有模拟器信息
        """
        info_dict = {}
        for device_id, simulator in self.simulators.items():
            info_dict[device_id] = self.get_simulator_info(device_id)
        return info_dict


# 导入Any类型
from typing import Any
