# 主程序入口
import sys
import signal
import time
from .config import Config
from .device_manager import DeviceManager
from .strategy import ModeControllerStrategy
from .logger import get_logger

# 尝试导入监控模块（兼容模式）
try:
    from .monitor import DataCollector, Database, Dashboard
    MONITOR_AVAILABLE = True
except Exception as e:
    logger = get_logger('main')
    logger.warning(f"监控模块导入失败（兼容模式）: {e}")
    # 定义占位符类
    class Database:
        def __init__(self, *args, **kwargs):
            pass
        
        def insert_data(self, data):
            """兼容模式：不保存数据"""
            return True
    
    class Dashboard:
        def __init__(self, *args, **kwargs):
            pass
        
        def start(self):
            pass
        
        def stop(self):
            pass
        
        def register_strategy(self, *args, **kwargs):
            pass
    
    # 导入DataCollector
    from .monitor.collector import DataCollector
    MONITOR_AVAILABLE = False


class EdgeFusion:
    """台区智能融合终端后台程序"""
    
    def __init__(self):
        """初始化EdgeFusion应用"""
        self.logger = get_logger('EdgeFusion')
        # 初始化配置
        self.config = Config()
        self.logger.info("加载配置完成")
        
        # 初始化设备管理器
        device_config = dict(self.config.get('device_manager', {}))
        if self.config.get('simulation.enabled', False):
            simulation_config = dict(self.config.get('simulation', {}))
            simulation_config.pop('enabled', None)
            device_config['simulation'] = simulation_config
        self.device_manager = DeviceManager(device_config)
        self.logger.info("初始化设备管理器完成")
        
        # 初始化数据库（兼容模式）
        try:
            db_url = self.config.get('monitor.database_url', 'sqlite:///edgefusion.db')
            self.database = Database(db_url)
            self.logger.info("初始化数据库完成")
            # 初始化数据采集器
            self.data_collector = DataCollector(self.config, self.device_manager, self.database)
            self.logger.info("初始化数据采集器完成")
        except Exception as e:
            self.logger.warning(f"数据库初始化失败（兼容模式）: {e}")
            self.logger.warning("系统将在无数据库模式下运行")
            self.database = None
            # 初始化数据采集器（无数据库模式）
            self.data_collector = DataCollector(self.config, self.device_manager, None)
            self.logger.info("初始化数据采集器（无数据库模式）完成")
        
        # 初始化策略
        self.strategies = {}
        self._init_strategies()
        self.logger.info("初始化策略完成")
        
        # 初始化监控面板
        try:
            monitor_config = self.config.get('monitor', {})
            self.dashboard = Dashboard(monitor_config, self.device_manager, self.data_collector, self.database)
            
            # 注册策略到监控面板
            for name, strategy in self.strategies.items():
                self.dashboard.register_strategy(name, strategy)
            self.logger.info("初始化监控面板完成")
        except Exception as e:
            self.logger.warning(f"监控面板初始化失败（兼容模式）: {e}")
            self.logger.warning("系统将在无监控面板模式下运行")
            self.dashboard = None
        
        # 运行状态
        self.running = False
    
    def _init_strategies(self):
        """初始化策略"""
        controller_config = dict(self.config.get('control.mode_controller', {}))
        controller_config['use_simulated_devices'] = self.config.get('control.use_simulated_devices', True)
        self.strategies['mode_controller'] = ModeControllerStrategy(
            controller_config,
            self.device_manager,
            self.data_collector,
        )
    
    def start(self):
        """启动EdgeFusion应用"""
        try:
            self.logger.info("启动EdgeFusion应用...")
            self.running = True
            
            # 启动设备管理器
            self.device_manager.start()
            
            # 启动数据采集器
            self.data_collector.start()
            
            # 启动策略
            for name, strategy in self.strategies.items():
                strategy.start()
            
            # 启动监控面板（如果初始化成功）
            if self.dashboard:
                self.dashboard.start()
            
            self.logger.info("EdgeFusion应用启动完成")
            self.logger.info("系统运行中，按Ctrl+C停止")
            
            # 主循环
            while self.running:
                # 定期执行策略
                for name, strategy in self.strategies.items():
                    if strategy.is_enabled():
                        strategy.execute()
                time.sleep(10)  # 10秒执行一次策略
                
        except KeyboardInterrupt:
            self.logger.info("收到停止信号，正在停止应用...")
            self.stop()
        except Exception as e:
            self.logger.error(f"应用运行失败: {e}")
            self.stop()
    
    def stop(self):
        """停止EdgeFusion应用"""
        try:
            self.running = False
            
            # 停止监控面板（如果初始化成功）
            if self.dashboard:
                self.dashboard.stop()
            
            # 停止策略
            for name, strategy in self.strategies.items():
                strategy.stop()
            
            # 停止数据采集器
            self.data_collector.stop()
            
            # 停止设备管理器
            self.device_manager.stop()
            
            self.logger.info("EdgeFusion应用停止完成")
        except Exception as e:
            self.logger.error(f"停止应用失败: {e}")
    
    def get_status(self):
        """获取应用状态"""
        return {
            'running': self.running,
            'device_count': len(self.device_manager.get_devices()),
            'strategies': [name for name in self.strategies.keys()],
            'dashboard_url': f"http://{self.config.get('monitor.dashboard_host', '0.0.0.0')}:{self.config.get('monitor.dashboard_port', 5000)}"
        }


def main():
    """主函数"""
    app = EdgeFusion()
    app.start()


if __name__ == '__main__':
    main()
