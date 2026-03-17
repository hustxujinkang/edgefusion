# 配置管理模块
import yaml
import os
from typing import Dict, Any
from .runtime_paths import get_config_file


class Config:
    """配置管理类"""
    
    def __init__(self, config_file: str | None = None):
        """初始化配置
        
        Args:
            config_file: 配置文件路径
        """
        self.config_file = config_file or get_config_file()
        self.config: Dict[str, Any] = {}
        self._load_config()
    
    def _load_config(self):
        """加载配置文件"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.config = yaml.safe_load(f)
            else:
                # 使用默认配置
                self._load_default_config()
                # 保存默认配置到文件
                self.save_config()
        except Exception as e:
            print(f"加载配置文件失败: {e}")
            self._load_default_config()
    
    def _load_default_config(self):
        """加载默认配置"""
        self.config = {
            'device_manager': {
                'modbus': {
                    'host': 'localhost',
                    'port': 502,
                    'timeout': 5
                },
                'mqtt': {
                    'broker': 'localhost',
                    'port': 1883,
                    'username': None,
                    'password': None
                },
                'ocpp': {
                    'host': 'localhost',
                    'port': 8080,
                    'endpoint': '/ocpp'
                }
            },
            'strategy': {
                'peak_shaving': {
                    'peak_hours': ['18:00-22:00'],
                    'valley_hours': ['00:00-06:00'],
                    'peak_power_limit': 10000,
                    'valley_power_target': 5000
                },
                'demand_response': {
                    'response_levels': {
                        'level1': {'power_reduction': 10, 'duration': 30},
                        'level2': {'power_reduction': 20, 'duration': 60},
                        'level3': {'power_reduction': 30, 'duration': 120}
                    }
                },
                'self_consumption': {
                    'soc_target': 80,
                    'min_soc': 20,
                    'pv_power_threshold': 1000,
                    'grid_import_limit': 5000
                }
            },
            'monitor': {
                'collect_interval': 10,
                'database_url': 'sqlite:///edgefusion.db',
                'dashboard_port': 5000,
                'dashboard_host': '0.0.0.0'
            }
        }
    
    def save_config(self):
        """保存配置到文件"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                yaml.dump(self.config, f, default_flow_style=False, allow_unicode=True)
        except Exception as e:
            print(f"保存配置文件失败: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值
        
        Args:
            key: 配置键，支持点号分隔的路径
            default: 默认值
            
        Returns:
            Any: 配置值
        """
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set(self, key: str, value: Any):
        """设置配置值
        
        Args:
            key: 配置键，支持点号分隔的路径
            value: 配置值
        """
        keys = key.split('.')
        config = self.config
        
        for i, k in enumerate(keys[:-1]):
            if k not in config:
                config[k] = {}
            config = config[k]
        
        config[keys[-1]] = value
        self.save_config()
    
    def get_all(self) -> Dict[str, Any]:
        """获取所有配置
        
        Returns:
            Dict[str, Any]: 所有配置
        """
        return self.config
