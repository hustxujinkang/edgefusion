# 数据采集器
from typing import Dict, Any, List
from datetime import datetime
import threading
import time
from ..device_manager import DeviceManager
from ..config import Config
from ..logger import get_logger


class DataCollector:
    """数据采集器，用于实时采集设备运行数据"""
    
    def __init__(self, config: Config, device_manager: DeviceManager, database: Any):
        """初始化数据采集器
        
        Args:
            config: 配置实例
            device_manager: 设备管理器实例
            database: 数据库实例
        """
        self.config = config
        self.device_manager = device_manager
        self.database = database
        self.collecting = False
        self.collect_thread = None
        self.collect_interval = config.get('collect_interval', 10)  # 采集间隔（秒）
        self.data_buffer: List[Dict[str, Any]] = []
        self.buffer_lock = threading.Lock()
        self.logger = get_logger('DataCollector')
    
    def start(self) -> bool:
        """启动数据采集
        
        Returns:
            bool: 启动是否成功
        """
        try:
            self.collecting = True
            self.collect_thread = threading.Thread(target=self._collect_loop, daemon=True)
            self.collect_thread.start()
            self.logger.info("启动数据采集器")
            return True
        except Exception as e:
            self.logger.error("启动数据采集器失败: %s", e)
            self.collecting = False
            return False
    
    def stop(self) -> bool:
        """停止数据采集
        
        Returns:
            bool: 停止是否成功
        """
        try:
            self.collecting = False
            if self.collect_thread:
                self.collect_thread.join(timeout=5)
            self.logger.info("停止数据采集器")
            return True
        except Exception as e:
            self.logger.error("停止数据采集器失败: %s", e)
            return False
    
    def _collect_loop(self):
        """数据采集循环"""
        while self.collecting:
            try:
                self.collect_data()
                time.sleep(self.collect_interval)
            except Exception as e:
                self.logger.error("数据采集失败: %s", e)
                time.sleep(self.collect_interval)
    
    def collect_data(self) -> List[Dict[str, Any]]:
        """采集设备数据
        
        Returns:
            List[Dict[str, Any]]: 采集的数据列表
        """
        collected_data = []
        timestamp = datetime.now()
        
        # 采集所有设备数据
        devices = self.device_manager.get_devices()
        for device in devices:
            device_id = device['device_id']
            device_type = device.get('type', 'unknown')
            
            # 根据设备类型采集不同的数据
            if device_type == 'pv':
                data = self._collect_pv_data(device_id, timestamp)
            elif device_type == 'energy_storage':
                data = self._collect_storage_data(device_id, timestamp)
            elif device_type == 'charging_station':
                data = self._collect_charger_data(device_id, timestamp)
            else:
                data = self._collect_generic_data(device_id, timestamp)
            
            if data:
                collected_data.append(data)
        
        # 保存数据到缓冲区
        with self.buffer_lock:
            self.data_buffer.extend(collected_data)
            # 限制缓冲区大小
            if len(self.data_buffer) > 1000:
                self.data_buffer = self.data_buffer[-1000:]
        
        # 保存数据到数据库
        if self.database:
            for data in collected_data:
                self.database.insert_data(data)
        
        return collected_data
    
    def _collect_pv_data(self, device_id: str, timestamp: datetime) -> Dict[str, Any]:
        """采集光伏设备数据
        
        Args:
            device_id: 设备ID
            timestamp: 采集时间
            
        Returns:
            Dict[str, Any]: 采集的数据
        """
        try:
            # 读取光伏设备数据
            power = self.device_manager.read_device_data(device_id, 'power') or 0
            energy = self.device_manager.read_device_data(device_id, 'energy') or 0
            voltage = self.device_manager.read_device_data(device_id, 'voltage') or 0
            current = self.device_manager.read_device_data(device_id, 'current') or 0
            status = self.device_manager.read_device_data(device_id, 'status') or 'unknown'
            
            return {
                'device_id': device_id,
                'device_type': 'pv',
                'timestamp': timestamp.isoformat(),
                'data': {
                    'power': power,
                    'energy': energy,
                    'voltage': voltage,
                    'current': current,
                    'status': status
                }
            }
        except Exception as e:
            self.logger.warning("采集光伏数据失败: %s", e)
            return {
                'device_id': device_id,
                'device_type': 'pv',
                'timestamp': timestamp.isoformat(),
                'data': {
                    'power': 0,
                    'energy': 0,
                    'voltage': 0,
                    'current': 0,
                    'status': 'error'
                }
            }
    
    def _collect_storage_data(self, device_id: str, timestamp: datetime) -> Dict[str, Any]:
        """采集储能设备数据
        
        Args:
            device_id: 设备ID
            timestamp: 采集时间
            
        Returns:
            Dict[str, Any]: 采集的数据
        """
        try:
            # 读取储能设备数据
            soc = self.device_manager.read_device_data(device_id, 'soc') or 0
            power = self.device_manager.read_device_data(device_id, 'power') or 0
            voltage = self.device_manager.read_device_data(device_id, 'voltage') or 0
            current = self.device_manager.read_device_data(device_id, 'current') or 0
            mode = self.device_manager.read_device_data(device_id, 'mode') or 'unknown'
            
            return {
                'device_id': device_id,
                'device_type': 'energy_storage',
                'timestamp': timestamp.isoformat(),
                'data': {
                    'soc': soc,
                    'power': power,
                    'voltage': voltage,
                    'current': current,
                    'mode': mode
                }
            }
        except Exception as e:
            self.logger.warning("采集储能数据失败: %s", e)
            return {
                'device_id': device_id,
                'device_type': 'energy_storage',
                'timestamp': timestamp.isoformat(),
                'data': {
                    'soc': 0,
                    'power': 0,
                    'voltage': 0,
                    'current': 0,
                    'mode': 'error'
                }
            }
    
    def _collect_charger_data(self, device_id: str, timestamp: datetime) -> Dict[str, Any]:
        """采集充电桩数据
        
        Args:
            device_id: 设备ID
            timestamp: 采集时间
            
        Returns:
            Dict[str, Any]: 采集的数据
        """
        try:
            # 读取充电桩数据
            status = self.device_manager.read_device_data(device_id, 'status') or 'Available'
            power = self.device_manager.read_device_data(device_id, 'power') or 0
            energy = self.device_manager.read_device_data(device_id, 'energy') or 0
            voltage = self.device_manager.read_device_data(device_id, 'voltage') or 0
            current = self.device_manager.read_device_data(device_id, 'current') or 0
            
            return {
                'device_id': device_id,
                'device_type': 'charging_station',
                'timestamp': timestamp.isoformat(),
                'data': {
                    'status': status,
                    'power': power,
                    'energy': energy,
                    'voltage': voltage,
                    'current': current
                }
            }
        except Exception as e:
            self.logger.warning("采集充电桩数据失败: %s", e)
            return {
                'device_id': device_id,
                'device_type': 'charging_station',
                'timestamp': timestamp.isoformat(),
                'data': {
                    'status': 'Error',
                    'power': 0,
                    'energy': 0,
                    'voltage': 0,
                    'current': 0
                }
            }
    
    def _collect_generic_data(self, device_id: str, timestamp: datetime) -> Dict[str, Any]:
        """采集通用设备数据
        
        Args:
            device_id: 设备ID
            timestamp: 采集时间
            
        Returns:
            Dict[str, Any]: 采集的数据
        """
        try:
            # 读取通用设备数据
            status = self.device_manager.get_device_status(device_id)
            
            return {
                'device_id': device_id,
                'device_type': 'generic',
                'timestamp': timestamp.isoformat(),
                'data': {
                    'status': status
                }
            }
        except Exception as e:
            self.logger.warning("采集通用设备数据失败: %s", e)
            return {
                'device_id': device_id,
                'device_type': 'generic',
                'timestamp': timestamp.isoformat(),
                'data': {
                    'status': 'error'
                }
            }
    
    def get_latest_data(self, device_id: str = None) -> List[Dict[str, Any]]:
        """获取最新采集的数据
        
        Args:
            device_id: 设备ID，None表示获取所有设备数据
            
        Returns:
            List[Dict[str, Any]]: 最新数据列表
        """
        with self.buffer_lock:
            if device_id:
                return [data for data in self.data_buffer if data['device_id'] == device_id]
            return self.data_buffer.copy()
    
    def get_data_summary(self) -> Dict[str, Any]:
        """获取数据采集摘要
        
        Returns:
            Dict[str, Any]: 数据采集摘要
        """
        with self.buffer_lock:
            device_count = len(set(data['device_id'] for data in self.data_buffer))
            total_data_points = len(self.data_buffer)
            
            # 计算各类型设备数量
            device_types = {}
            for data in self.data_buffer:
                device_type = data.get('device_type', 'unknown')
                device_types[device_type] = device_types.get(device_type, 0) + 1
            
            return {
                'collecting': self.collecting,
                'collect_interval': self.collect_interval,
                'buffer_size': len(self.data_buffer),
                'device_count': device_count,
                'total_data_points': total_data_points,
                'device_types': device_types
            }
