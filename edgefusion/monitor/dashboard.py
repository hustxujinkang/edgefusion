# 监控面板
from typing import Dict, Any, List
from flask import Flask, jsonify, request
import threading
import time
from ..device_manager import DeviceManager
from ..strategy import StrategyBase
from .collector import DataCollector
from .database import Database


class Dashboard:
    """监控面板，提供Web界面展示系统状态"""
    
    def __init__(self, config: Dict[str, Any], device_manager: DeviceManager, data_collector: DataCollector, database: Database):
        """初始化监控面板
        
        Args:
            config: 配置参数
            device_manager: 设备管理器实例
            data_collector: 数据采集器实例
            database: 数据库实例
        """
        self.config = config
        self.device_manager = device_manager
        self.data_collector = data_collector
        self.database = database
        self.strategies: Dict[str, StrategyBase] = {}
        self.app = Flask(__name__)
        self.running = False
        self.server_thread = None
        self.port = config.get('dashboard_port', 5000)
        self.host = config.get('dashboard_host', '0.0.0.0')
        
        # 注册路由
        self._register_routes()
    
    def _register_routes(self):
        """注册Flask路由"""
        # 系统状态
        @self.app.route('/api/status', methods=['GET'])
        def get_status():
            return jsonify(self.get_system_status())
        
        # 设备列表
        @self.app.route('/api/devices', methods=['GET'])
        def get_devices():
            return jsonify(self.device_manager.get_devices())
        
        # 设备详情
        @self.app.route('/api/devices/<device_id>', methods=['GET'])
        def get_device_detail(device_id):
            device = self.device_manager.get_device(device_id)
            if not device:
                return jsonify({'error': 'Device not found'}), 404
            return jsonify(device)
        
        # 设备数据
        @self.app.route('/api/devices/<device_id>/data', methods=['GET'])
        def get_device_data(device_id):
            limit = int(request.args.get('limit', 100))
            data = self.database.get_data_by_device(device_id, limit)
            return jsonify(data)
        
        # 策略列表
        @self.app.route('/api/strategies', methods=['GET'])
        def get_strategies():
            return jsonify(self.get_strategies_status())
        
        # 策略详情
        @self.app.route('/api/strategies/<strategy_name>', methods=['GET'])
        def get_strategy_detail(strategy_name):
            if strategy_name not in self.strategies:
                return jsonify({'error': 'Strategy not found'}), 404
            strategy = self.strategies[strategy_name]
            return jsonify(strategy.get_status())
        
        # 触发策略
        @self.app.route('/api/strategies/<strategy_name>/execute', methods=['POST'])
        def execute_strategy(strategy_name):
            if strategy_name not in self.strategies:
                return jsonify({'error': 'Strategy not found'}), 404
            strategy = self.strategies[strategy_name]
            result = strategy.execute()
            return jsonify(result)
        
        # 数据采集状态
        @self.app.route('/api/collector', methods=['GET'])
        def get_collector_status():
            return jsonify(self.data_collector.get_data_summary())
        
        # 数据库统计
        @self.app.route('/api/database', methods=['GET'])
        def get_database_stats():
            return jsonify(self.database.get_device_stats())
        
        # 主页
        @self.app.route('/')
        def index():
            return '''
            <!DOCTYPE html>
            <html lang="zh-CN">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>台区智能融合终端监控面板</title>
                <style>
                    body {
                        font-family: Arial, sans-serif;
                        margin: 20px;
                        background-color: #f0f0f0;
                    }
                    h1 {
                        color: #333;
                    }
                    .card {
                        background-color: white;
                        padding: 20px;
                        margin: 10px 0;
                        border-radius: 5px;
                        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    }
                    .endpoint {
                        background-color: #f9f9f9;
                        padding: 10px;
                        margin: 5px 0;
                        border-left: 3px solid #007bff;
                    }
                    a {
                        color: #007bff;
                        text-decoration: none;
                    }
                    a:hover {
                        text-decoration: underline;
                    }
                </style>
            </head>
            <body>
                <h1>台区智能融合终端监控面板</h1>
                <div class="card">
                    <h2>API 端点</h2>
                    <div class="endpoint">
                        <strong>系统状态:</strong> <a href="/api/status">/api/status</a>
                    </div>
                    <div class="endpoint">
                        <strong>设备列表:</strong> <a href="/api/devices">/api/devices</a>
                    </div>
                    <div class="endpoint">
                        <strong>设备详情:</strong> /api/devices/{device_id}
                    </div>
                    <div class="endpoint">
                        <strong>设备数据:</strong> /api/devices/{device_id}/data
                    </div>
                    <div class="endpoint">
                        <strong>策略列表:</strong> <a href="/api/strategies">/api/strategies</a>
                    </div>
                    <div class="endpoint">
                        <strong>策略详情:</strong> /api/strategies/{strategy_name}
                    </div>
                    <div class="endpoint">
                        <strong>数据采集状态:</strong> <a href="/api/collector">/api/collector</a>
                    </div>
                    <div class="endpoint">
                        <strong>数据库统计:</strong> <a href="/api/database">/api/database</a>
                    </div>
                </div>
            </body>
            </html>
            '''
    
    def start(self) -> bool:
        """启动监控面板
        
        Returns:
            bool: 启动是否成功
        """
        try:
            self.running = True
            self.server_thread = threading.Thread(target=self._run_server, daemon=True)
            self.server_thread.start()
            print(f"启动监控面板，访问地址: http://{self.host}:{self.port}")
            return True
        except Exception as e:
            print(f"启动监控面板失败: {e}")
            self.running = False
            return False
    
    def stop(self) -> bool:
        """停止监控面板
        
        Returns:
            bool: 停止是否成功
        """
        try:
            self.running = False
            # Flask开发服务器无法优雅停止，这里简化处理
            print("停止监控面板")
            return True
        except Exception as e:
            print(f"停止监控面板失败: {e}")
            return False
    
    def _run_server(self):
        """运行Flask服务器"""
        try:
            self.app.run(host=self.host, port=self.port, debug=False, use_reloader=False)
        except Exception as e:
            print(f"服务器运行失败: {e}")
            self.running = False
    
    def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态
        
        Returns:
            Dict[str, Any]: 系统状态
        """
        # 获取设备统计
        device_stats = self.database.get_device_stats()
        
        # 获取数据采集状态
        collector_status = self.data_collector.get_data_summary()
        
        # 获取策略状态
        strategy_status = self.get_strategies_status()
        
        return {
            'status': 'running' if self.running else 'stopped',
            'dashboard_url': f"http://{self.host}:{self.port}",
            'device_stats': device_stats,
            'collector_status': collector_status,
            'strategy_status': strategy_status
        }
    
    def get_strategies_status(self) -> List[Dict[str, Any]]:
        """获取策略状态
        
        Returns:
            List[Dict[str, Any]]: 策略状态列表
        """
        status_list = []
        for name, strategy in self.strategies.items():
            status = strategy.get_status()
            status['name'] = name
            status_list.append(status)
        return status_list
    
    def register_strategy(self, name: str, strategy: StrategyBase):
        """注册策略
        
        Args:
            name: 策略名称
            strategy: 策略实例
        """
        self.strategies[name] = strategy
    
    def unregister_strategy(self, name: str):
        """注销策略
        
        Args:
            name: 策略名称
        """
        if name in self.strategies:
            del self.strategies[name]
