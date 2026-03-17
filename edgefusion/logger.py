# 日志管理模块
import logging
import logging.handlers
import os
from datetime import datetime
from .runtime_paths import get_log_dir


class Logger:
    """日志管理器"""
    
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, log_dir=None, max_bytes=10485760, backup_count=5):
        """初始化日志管理器
        
        Args:
            log_dir: 日志目录
            max_bytes: 单个日志文件最大字节数
            backup_count: 日志文件备份数量
        """
        if not hasattr(self, 'initialized'):
            self.initialized = True
            self.log_dir = log_dir or get_log_dir()
            self.max_bytes = max_bytes
            self.backup_count = backup_count
            
            # 创建日志目录
            if not os.path.exists(self.log_dir):
                os.makedirs(self.log_dir)
            
            # 配置根日志器
            self._configure_root_logger()
    
    def _configure_root_logger(self):
        """配置根日志器"""
        # 创建根日志器
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)
        
        # 清除现有处理器
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
            handler.close()
        
        # 创建格式器
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # 创建控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
        
        # 创建文件处理器
        log_file = os.path.join(self.log_dir, f'edgefusion_{datetime.now().strftime("%Y%m%d")}.log')
        file_handler = logging.handlers.RotatingFileHandler(
            log_file, maxBytes=self.max_bytes, backupCount=self.backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    def get_logger(self, name):
        """获取指定名称的日志器
        
        Args:
            name: 日志器名称
            
        Returns:
            logging.Logger: 日志器实例
        """
        return logging.getLogger(name)


# 全局日志器实例
logger = Logger()

# 便捷函数
def get_logger(name):
    """获取指定名称的日志器
    
    Args:
        name: 日志器名称
        
    Returns:
        logging.Logger: 日志器实例
    """
    return logger.get_logger(name)
