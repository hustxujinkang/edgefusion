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
    <title>台区智能融合终端监控面板 - EdgeFusion</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.1/font/bootstrap-icons.css" rel="stylesheet">
    <style>
        :root {
            --primary-color: #0d6efd;
            --success-color: #198754;
            --warning-color: #ffc107;
            --danger-color: #dc3545;
            --dark-color: #212529;
        }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }
        .main-container {
            background: #f8f9fa;
            min-height: 100vh;
        }
        .header {
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            color: white;
            padding: 2rem 0;
            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
        }
        .header h1 {
            font-weight: 700;
            margin-bottom: 0.5rem;
        }
        .header .subtitle {
            opacity: 0.9;
            font-size: 1.1rem;
        }
        .nav-pills .nav-link {
            color: #495057;
            font-weight: 500;
            padding: 0.75rem 1.25rem;
            border-radius: 0.5rem;
            margin: 0.25rem;
            transition: all 0.3s ease;
        }
        .nav-pills .nav-link:hover {
            background: #e9ecef;
        }
        .nav-pills .nav-link.active {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
        }
        .card {
            border: none;
            border-radius: 1rem;
            box-shadow: 0 4px 20px rgba(0,0,0,0.08);
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }
        .card:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 30px rgba(0,0,0,0.12);
        }
        .card-header {
            background: white;
            border-bottom: 2px solid #f0f0f0;
            font-weight: 600;
            padding: 1rem 1.5rem;
            border-radius: 1rem 1rem 0 0 !important;
        }
        .stat-card {
            background: white;
            border-radius: 1rem;
            padding: 1.5rem;
            text-align: center;
            box-shadow: 0 4px 20px rgba(0,0,0,0.08);
            transition: all 0.3s ease;
        }
        .stat-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 8px 30px rgba(0,0,0,0.15);
        }
        .stat-icon {
            font-size: 2.5rem;
            margin-bottom: 0.5rem;
        }
        .stat-value {
            font-size: 2rem;
            font-weight: 700;
            color: var(--dark-color);
        }
        .stat-label {
            color: #6c757d;
            font-weight: 500;
        }
        .api-card {
            border-left: 4px solid var(--primary-color);
            margin-bottom: 1rem;
        }
        .api-method {
            display: inline-block;
            padding: 0.25rem 0.75rem;
            border-radius: 0.375rem;
            font-size: 0.75rem;
            font-weight: 700;
            text-transform: uppercase;
            margin-right: 0.5rem;
        }
        .method-get { background: #d1e7dd; color: #0f5132; }
        .method-post { background: #fff3cd; color: #664d03; }
        .method-put { background: #cff4fc; color: #055160; }
        .method-delete { background: #f8d7da; color: #842029; }
        .api-path {
            font-family: 'Courier New', monospace;
            background: #f8f9fa;
            padding: 0.5rem 1rem;
            border-radius: 0.5rem;
            color: var(--primary-color);
            font-weight: 600;
        }
        .api-description {
            color: #6c757d;
            margin-top: 0.5rem;
        }
        .badge-custom {
            padding: 0.5rem 1rem;
            font-weight: 500;
        }
        .status-dot {
            display: inline-block;
            width: 10px;
            height: 10px;
            border-radius: 50%;
            margin-right: 8px;
            animation: pulse 2s infinite;
        }
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        .status-online { background: #198754; }
        .status-offline { background: #dc3545; }
        .tab-content {
            animation: fadeIn 0.3s ease;
        }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .footer {
            background: #212529;
            color: white;
            padding: 2rem 0;
            margin-top: 3rem;
        }
        .refresh-btn {
            position: fixed;
            bottom: 2rem;
            right: 2rem;
            width: 60px;
            height: 60px;
            border-radius: 50%;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.5);
            font-size: 1.5rem;
            cursor: pointer;
            transition: all 0.3s ease;
            z-index: 1000;
        }
        .refresh-btn:hover {
            transform: scale(1.1) rotate(180deg);
            box-shadow: 0 6px 20px rgba(102, 126, 234, 0.7);
        }
        .table-responsive {
            border-radius: 0.75rem;
        }
        .table thead {
            background: #f8f9fa;
        }
        .table th {
            font-weight: 600;
            color: #495057;
            border-bottom: 2px solid #dee2e6;
        }
        .parameter-badge {
            font-size: 0.75rem;
            background: #e7f3ff;
            color: #0066cc;
            padding: 0.25rem 0.5rem;
            border-radius: 0.25rem;
            margin-right: 0.25rem;
        }
    </style>
</head>
<body>
    <div class="main-container">
        <div class="header">
            <div class="container">
                <div class="row align-items-center">
                    <div class="col-md-8">
                        <h1><i class="bi bi-lightning-charge-fill me-3"></i>EdgeFusion</h1>
                        <p class="subtitle mb-0"><i class="bi bi-gear-fill me-2"></i>台区智能融合终端后台监控系统</p>
                    </div>
                    <div class="col-md-4 text-end">
                        <span class="badge bg-success badge-custom">
                            <span class="status-dot status-online"></span>系统运行中
                        </span>
                    </div>
                </div>
            </div>
        </div>
        <div class="container py-4">
            <ul class="nav nav-pills nav-fill mb-4" id="mainTabs" role="tablist">
                <li class="nav-item">
                    <button class="nav-link active" id="dashboard-tab" data-bs-toggle="pill" data-bs-target="#dashboard" type="button" role="tab">
                        <i class="bi bi-speedometer2 me-2"></i>仪表板
                    </button>
                </li>
                <li class="nav-item">
                    <button class="nav-link" id="devices-tab" data-bs-toggle="pill" data-bs-target="#devices" type="button" role="tab">
                        <i class="bi bi-hdd-stack me-2"></i>设备管理
                    </button>
                </li>
                <li class="nav-item">
                    <button class="nav-link" id="strategies-tab" data-bs-toggle="pill" data-bs-target="#strategies" type="button" role="tab">
                        <i class="bi bi-diagram-3 me-2"></i>控制策略
                    </button>
                </li>
                <li class="nav-item">
                    <button class="nav-link" id="api-tab" data-bs-toggle="pill" data-bs-target="#api" type="button" role="tab">
                        <i class="bi bi-code-slash me-2"></i>API文档
                    </button>
                </li>
            </ul>
            <div class="tab-content" id="mainTabsContent">
                <div class="tab-pane fade show active" id="dashboard" role="tabpanel">
                    <div class="row g-4 mb-4">
                        <div class="col-md-3">
                            <div class="stat-card">
                                <div class="stat-icon text-primary"><i class="bi bi-hdd"></i></div>
                                <div class="stat-value" id="deviceCount">-</div>
                                <div class="stat-label">设备总数</div>
                            </div>
                        </div>
                        <div class="col-md-3">
                            <div class="stat-card">
                                <div class="stat-icon text-success"><i class="bi bi-check-circle"></i></div>
                                <div class="stat-value" id="onlineDevices">-</div>
                                <div class="stat-label">在线设备</div>
                            </div>
                        </div>
                        <div class="col-md-3">
                            <div class="stat-card">
                                <div class="stat-icon text-warning"><i class="bi bi-database"></i></div>
                                <div class="stat-value" id="dataPoints">-</div>
                                <div class="stat-label">数据点数</div>
                            </div>
                        </div>
                        <div class="col-md-3">
                            <div class="stat-card">
                                <div class="stat-icon text-info"><i class="bi bi-gear"></i></div>
                                <div class="stat-value" id="strategyCount">-</div>
                                <div class="stat-label">策略数量</div>
                            </div>
                        </div>
                    </div>
                    <div class="row g-4">
                        <div class="col-md-6">
                            <div class="card">
                                <div class="card-header d-flex justify-content-between align-items-center">
                                    <span><i class="bi bi-info-circle me-2"></i>系统状态</span>
                                    <a href="/api/status" class="btn btn-sm btn-outline-primary"><i class="bi bi-arrow-up-right me-1"></i>查看JSON</a>
                                </div>
                                <div class="card-body">
                                    <div id="systemStatus">
                                        <div class="text-center py-4 text-muted">
                                            <div class="spinner-border" role="status"></div>
                                            <p class="mt-2">加载中...</p>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                        <div class="col-md-6">
                            <div class="card">
                                <div class="card-header d-flex justify-content-between align-items-center">
                                    <span><i class="bi bi-database me-2"></i>数据采集状态</span>
                                    <a href="/api/collector" class="btn btn-sm btn-outline-primary"><i class="bi bi-arrow-up-right me-1"></i>查看JSON</a>
                                </div>
                                <div class="card-body">
                                    <div id="collectorStatus">
                                        <div class="text-center py-4 text-muted">
                                            <div class="spinner-border" role="status"></div>
                                            <p class="mt-2">加载中...</p>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="row g-4 mt-4">
                        <div class="col-12">
                            <div class="card">
                                <div class="card-header d-flex justify-content-between align-items-center">
                                    <span><i class="bi bi-table me-2"></i>数据库统计</span>
                                    <a href="/api/database" class="btn btn-sm btn-outline-primary"><i class="bi bi-arrow-up-right me-1"></i>查看JSON</a>
                                </div>
                                <div class="card-body">
                                    <div id="databaseStats">
                                        <div class="text-center py-4 text-muted">
                                            <div class="spinner-border" role="status"></div>
                                            <p class="mt-2">加载中...</p>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="tab-pane fade" id="devices" role="tabpanel">
                    <div class="card">
                        <div class="card-header d-flex justify-content-between align-items-center">
                            <span><i class="bi bi-list-ul me-2"></i>设备列表</span>
                            <a href="/api/devices" class="btn btn-sm btn-outline-primary"><i class="bi bi-arrow-up-right me-1"></i>查看JSON</a>
                        </div>
                        <div class="card-body">
                            <div id="deviceList">
                                <div class="text-center py-4 text-muted">
                                    <div class="spinner-border" role="status"></div>
                                    <p class="mt-2">加载中...</p>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="tab-pane fade" id="strategies" role="tabpanel">
                    <div class="card">
                        <div class="card-header d-flex justify-content-between align-items-center">
                            <span><i class="bi bi-list-ul me-2"></i>策略列表</span>
                            <a href="/api/strategies" class="btn btn-sm btn-outline-primary"><i class="bi bi-arrow-up-right me-1"></i>查看JSON</a>
                        </div>
                        <div class="card-body">
                            <div id="strategyList">
                                <div class="text-center py-4 text-muted">
                                    <div class="spinner-border" role="status"></div>
                                    <p class="mt-2">加载中...</p>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="tab-pane fade" id="api" role="tabpanel">
                    <div class="card mb-4">
                        <div class="card-header">
                            <i class="bi bi-book me-2"></i>API接口文档
                        </div>
                        <div class="card-body">
                            <p class="text-muted">
                                以下是EdgeFusion系统提供的所有RESTful API接口。所有接口返回JSON格式数据。
                            </p>
                        </div>
                    </div>
                    <div class="card api-card mb-3">
                        <div class="card-body">
                            <div class="d-flex align-items-center mb-2">
                                <span class="api-method method-get">GET</span>
                                <span class="api-path">/api/status</span>
                            </div>
                            <h5 class="fw-bold">系统状态</h5>
                            <p class="api-description">获取整个系统的运行状态，包括设备统计、数据采集状态和策略状态。</p>
                            <div class="mt-2">
                                <span class="parameter-badge">无参数</span>
                            </div>
                            <div class="mt-3">
                                <a href="/api/status" class="btn btn-sm btn-outline-primary" target="_blank">
                                    <i class="bi bi-play me-1"></i>测试接口
                                </a>
                            </div>
                        </div>
                    </div>
                    <div class="card api-card mb-3">
                        <div class="card-body">
                            <div class="d-flex align-items-center mb-2">
                                <span class="api-method method-get">GET</span>
                                <span class="api-path">/api/devices</span>
                            </div>
                            <h5 class="fw-bold">设备列表</h5>
                            <p class="api-description">获取当前系统中注册的所有设备信息，包括设备ID、类型、状态等。</p>
                            <div class="mt-2">
                                <span class="parameter-badge">无参数</span>
                            </div>
                            <div class="mt-3">
                                <a href="/api/devices" class="btn btn-sm btn-outline-primary" target="_blank">
                                    <i class="bi bi-play me-1"></i>测试接口
                                </a>
                            </div>
                        </div>
                    </div>
                    <div class="card api-card mb-3">
                        <div class="card-body">
                            <div class="d-flex align-items-center mb-2">
                                <span class="api-method method-get">GET</span>
                                <span class="api-path">/api/devices/{device_id}</span>
                            </div>
                            <h5 class="fw-bold">设备详情</h5>
                            <p class="api-description">获取指定设备的详细信息，包括设备配置、连接状态、协议信息等。</p>
                            <div class="mt-2">
                                <span class="parameter-badge">device_id (路径参数): 设备唯一标识符</span>
                            </div>
                            <div class="alert alert-info mt-2 small">
                                <i class="bi bi-info-circle me-1"></i>返回404如果设备不存在
                            </div>
                        </div>
                    </div>
                    <div class="card api-card mb-3">
                        <div class="card-body">
                            <div class="d-flex align-items-center mb-2">
                                <span class="api-method method-get">GET</span>
                                <span class="api-path">/api/devices/{device_id}/data</span>
                            </div>
                            <h5 class="fw-bold">设备数据</h5>
                            <p class="api-description">获取指定设备的历史采集数据，支持限制返回条数。</p>
                            <div class="mt-2">
                                <span class="parameter-badge">device_id (路径参数): 设备唯一标识符</span>
                                <span class="parameter-badge">limit (查询参数): 返回数据条数，默认100</span>
                            </div>
                            <div class="alert alert-info mt-2 small">
                                <i class="bi bi-lightbulb me-1"></i>示例: /api/devices/device_001/data?limit=50
                            </div>
                        </div>
                    </div>
                    <div class="card api-card mb-3">
                        <div class="card-body">
                            <div class="d-flex align-items-center mb-2">
                                <span class="api-method method-get">GET</span>
                                <span class="api-path">/api/strategies</span>
                            </div>
                            <h5 class="fw-bold">策略列表</h5>
                            <p class="api-description">获取系统中所有可用的控制策略及其当前状态。</p>
                            <div class="mt-2">
                                <span class="parameter-badge">无参数</span>
                            </div>
                            <div class="mt-3">
                                <a href="/api/strategies" class="btn btn-sm btn-outline-primary" target="_blank">
                                    <i class="bi bi-play me-1"></i>测试接口
                                </a>
                            </div>
                        </div>
                    </div>
                    <div class="card api-card mb-3">
                        <div class="card-body">
                            <div class="d-flex align-items-center mb-2">
                                <span class="api-method method-get">GET</span>
                                <span class="api-path">/api/strategies/{strategy_name}</span>
                            </div>
                            <h5 class="fw-bold">策略详情</h5>
                            <p class="api-description">获取指定策略的详细配置和当前运行状态。</p>
                            <div class="mt-2">
                                <span class="parameter-badge">strategy_name (路径参数): 策略名称</span>
                            </div>
                            <div class="alert alert-info mt-2 small">
                                <i class="bi bi-info-circle me-1"></i>返回404如果策略不存在
                            </div>
                        </div>
                    </div>
                    <div class="card api-card mb-3">
                        <div class="card-body">
                            <div class="d-flex align-items-center mb-2">
                                <span class="api-method method-post">POST</span>
                                <span class="api-path">/api/strategies/{strategy_name}/execute</span>
                            </div>
                            <h5 class="fw-bold">触发策略执行</h5>
                            <p class="api-description">手动触发指定的控制策略立即执行一次。</p>
                            <div class="mt-2">
                                <span class="parameter-badge">strategy_name (路径参数): 策略名称</span>
                            </div>
                            <div class="alert alert-warning mt-2 small">
                                <i class="bi bi-exclamation-triangle me-1"></i>这会立即执行策略，可能影响设备运行状态
                            </div>
                        </div>
                    </div>
                    <div class="card api-card mb-3">
                        <div class="card-body">
                            <div class="d-flex align-items-center mb-2">
                                <span class="api-method method-get">GET</span>
                                <span class="api-path">/api/collector</span>
                            </div>
                            <h5 class="fw-bold">数据采集状态</h5>
                            <p class="api-description">获取数据采集器的运行状态，包括采集间隔、最后采集时间、数据统计等。</p>
                            <div class="mt-2">
                                <span class="parameter-badge">无参数</span>
                            </div>
                            <div class="mt-3">
                                <a href="/api/collector" class="btn btn-sm btn-outline-primary" target="_blank">
                                    <i class="bi bi-play me-1"></i>测试接口
                                </a>
                            </div>
                        </div>
                    </div>
                    <div class="card api-card mb-3">
                        <div class="card-body">
                            <div class="d-flex align-items-center mb-2">
                                <span class="api-method method-get">GET</span>
                                <span class="api-path">/api/database</span>
                            </div>
                            <h5 class="fw-bold">数据库统计</h5>
                            <p class="api-description">获取数据库的统计信息，包括各设备的数据点数、总数据量等。</p>
                            <div class="mt-2">
                                <span class="parameter-badge">无参数</span>
                            </div>
                            <div class="mt-3">
                                <a href="/api/database" class="btn btn-sm btn-outline-primary" target="_blank">
                                    <i class="bi bi-play me-1"></i>测试接口
                                </a>
                            </div>
                        </div>
                    </div>
                    <div class="card mt-4">
                        <div class="card-header">
                            <i class="bi bi-info-circle me-2"></i>使用说明
                        </div>
                        <div class="card-body">
                            <h6 class="fw-bold mb-3"><i class="bi bi-check-circle text-success me-2"></i>通用说明</h6>
                            <ul class="mb-4">
                                <li>所有接口返回 <code>Content-Type: application/json</code></li>
                                <li>成功响应返回HTTP 200状态码</li>
                                <li>错误响应包含 <code>error</code> 字段说明错误原因</li>
                                <li>时间戳格式为Unix时间戳（秒）</li>
                            </ul>
                            <h6 class="fw-bold mb-3"><i class="bi bi-arrow-left-right text-primary me-2"></i>HTTP状态码</h6>
                            <div class="table-responsive">
                                <table class="table table-sm">
                                    <thead>
                                        <tr><th>状态码</th><th>说明</th></tr>
                                    </thead>
                                    <tbody>
                                        <tr><td><span class="badge bg-success">200</span></td><td>请求成功</td></tr>
                                        <tr><td><span class="badge bg-danger">404</span></td><td>资源不存在</td></tr>
                                        <tr><td><span class="badge bg-warning">500</span></td><td>服务器内部错误</td></tr>
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        <div class="footer">
            <div class="container text-center">
                <p class="mb-1">
                    <i class="bi bi-lightning-charge-fill me-2"></i><strong>EdgeFusion</strong> - 台区智能融合终端后台系统
                </p>
                <p class="mb-0 small text-muted">
                    版本 0.1.0 | <i class="bi bi-github me-1"></i>开源项目
                </p>
            </div>
        </div>
    </div>
    <button class="refresh-btn" onclick="refreshAllData()" title="刷新数据">
        <i class="bi bi-arrow-repeat"></i>
    </button>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        async function fetchJSON(url) {
            try {
                const response = await fetch(url);
                return await response.json();
            } catch (e) {
                console.error('请求失败:', e);
                return null;
            }
        }
        async function loadSystemStatus() {
            const data = await fetchJSON('/api/status');
            const container = document.getElementById('systemStatus');
            if (!data) {
                container.innerHTML = '<div class="alert alert-danger">加载失败</div>';
                return;
            }
            let html = '<div class="table-responsive"><table class="table table-sm">';
            html += '<tr><th width="40%">状态</th><td><span class="badge bg-success">' + (data.status || 'running') + '</span></td></tr>';
            html += '<tr><th>面板地址</th><td><code>' + (data.dashboard_url || '-') + '</code></td></tr>';
            html += '</table></div>';
            container.innerHTML = html;
        }
        async function loadCollectorStatus() {
            const data = await fetchJSON('/api/collector');
            const container = document.getElementById('collectorStatus');
            if (!data) {
                container.innerHTML = '<div class="alert alert-danger">加载失败</div>';
                return;
            }
            let html = '<div class="table-responsive"><table class="table table-sm">';
            for (const [key, value] of Object.entries(data)) {
                html += '<tr><th width="40%">' + key + '</th><td><code>' + JSON.stringify(value) + '</code></td></tr>';
            }
            html += '</table></div>';
            container.innerHTML = html;
        }
        async function loadDatabaseStats() {
            const data = await fetchJSON('/api/database');
            const container = document.getElementById('databaseStats');
            if (!data) {
                container.innerHTML = '<div class="alert alert-danger">加载失败</div>';
                document.getElementById('dataPoints').textContent = '0';
                return;
            }
            let html = '<div class="table-responsive"><table class="table table-sm table-striped">';
            html += '<thead><tr><th>设备</th><th>数据点数</th></tr></thead><tbody>';
            let total = 0;
            let hasData = false;
            for (const [device, count] of Object.entries(data)) {
                const safeCount = typeof count === 'number' ? count : 0;
                html += '<tr><td><i class="bi bi-hdd me-2"></i>' + device + '</td><td>' + safeCount + '</td></tr>';
                total += safeCount;
                hasData = true;
            }
            if (!hasData) {
                html += '<tr><td colspan="2" class="text-center text-muted">暂无数据</td></tr>';
            }
            html += '</tbody><tfoot><tr class="fw-bold"><td>总计</td><td>' + total + '</td></tr></tfoot></table></div>';
            container.innerHTML = html;
            document.getElementById('dataPoints').textContent = total;
        }
        async function loadDevices() {
            const data = await fetchJSON('/api/devices');
            const container = document.getElementById('deviceList');
            if (!data) {
                container.innerHTML = '<div class="alert alert-danger">加载失败</div>';
                return;
            }
            const devices = Object.values(data);
            document.getElementById('deviceCount').textContent = devices.length;
            const onlineCount = devices.filter(d => d.status === 'online').length;
            document.getElementById('onlineDevices').textContent = onlineCount;
            if (devices.length === 0) {
                container.innerHTML = '<div class="alert alert-info text-center">暂无设备</div>';
                return;
            }
            let html = '<div class="table-responsive"><table class="table table-hover">';
            html += '<thead><tr><th>设备ID</th><th>类型</th><th>状态</th><th>操作</th></tr></thead><tbody>';
            for (const device of devices) {
                const statusBadge = device.status === 'online' 
                    ? '<span class="badge bg-success"><i class="bi bi-check-circle me-1"></i>在线</span>'
                    : '<span class="badge bg-danger"><i class="bi bi-x-circle me-1"></i>离线</span>';
                html += '<tr>';
                html += '<td><code>' + device.device_id + '</code></td>';
                html += '<td><span class="badge bg-secondary">' + (device.type || '-') + '</span></td>';
                html += '<td>' + statusBadge + '</td>';
                html += '<td>';
                html += '<a href="/api/devices/' + device.device_id + '" class="btn btn-sm btn-outline-primary me-1" target="_blank"><i class="bi bi-eye"></i></a>';
                html += '<a href="/api/devices/' + device.device_id + '/data" class="btn btn-sm btn-outline-info" target="_blank"><i class="bi bi-database"></i></a>';
                html += '</td></tr>';
            }
            html += '</tbody></table></div>';
            container.innerHTML = html;
        }
        async function loadStrategies() {
            const data = await fetchJSON('/api/strategies');
            const container = document.getElementById('strategyList');
            if (!data) {
                container.innerHTML = '<div class="alert alert-danger">加载失败</div>';
                return;
            }
            document.getElementById('strategyCount').textContent = data.length;
            if (data.length === 0) {
                container.innerHTML = '<div class="alert alert-info text-center">暂无策略</div>';
                return;
            }
            let html = '<div class="table-responsive"><table class="table table-hover">';
            html += '<thead><tr><th>策略名称</th><th>状态</th><th>操作</th></tr></thead><tbody>';
            for (const strategy of data) {
                html += '<tr>';
                html += '<td><i class="bi bi-gear me-2"></i><strong>' + (strategy.name || '-') + '</strong></td>';
                html += '<td><span class="badge bg-primary">已加载</span></td>';
                html += '<td>';
                html += '<a href="/api/strategies/' + strategy.name + '" class="btn btn-sm btn-outline-primary me-1" target="_blank"><i class="bi bi-eye"></i></a>';
                html += '</td></tr>';
            }
            html += '</tbody></table></div>';
            container.innerHTML = html;
        }
        async function refreshAllData() {
            await Promise.all([
                loadSystemStatus(),
                loadCollectorStatus(),
                loadDatabaseStats(),
                loadDevices(),
                loadStrategies()
            ]);
        }
        document.addEventListener('DOMContentLoaded', function() {
            refreshAllData();
        });
    </script>
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
