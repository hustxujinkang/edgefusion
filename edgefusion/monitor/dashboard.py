# 监控面板（增强版）
from typing import Dict, Any, List, Optional
from flask import Flask, jsonify, request, render_template
import threading
import time
import os
from ..device_manager import DeviceManager
from ..charger_layout import build_connector_device_id
from ..adapters.model_catalog import get_modbus_device_model_catalog, get_modbus_model_probe_register
from ..strategy import StrategyBase
from ..logger import get_logger
from .collector import DataCollector
from .database import Database
from ..protocol import ModbusProtocol, SimulationProtocol, create_modbus_protocol


class Dashboard:
    """监控面板，提供Web界面展示系统状态（增强版 - 支持设备管理）"""
    
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
        self.logger = get_logger('Dashboard')
        
        # 显式配置模板和静态资源目录，避免前端依赖外网 CDN
        app_root = os.path.dirname(os.path.dirname(__file__))
        template_dir = os.path.join(app_root, 'templates')
        static_dir = os.path.join(app_root, 'static')
        self.app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
        
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

        # 模式摘要
        @self.app.route('/api/modes/summary', methods=['GET'])
        def get_modes_summary():
            return jsonify(self._get_mode_summary())

        # 模式配置
        @self.app.route('/api/modes/config', methods=['GET'])
        def get_modes_config():
            return jsonify(self._get_mode_config())

        @self.app.route('/api/modes/config', methods=['POST'])
        def update_modes_config():
            data = request.get_json() or {}
            updated = self._set_mode_config(data)
            return jsonify({'success': True, **updated})

        # 控制设置
        @self.app.route('/api/control/settings', methods=['GET'])
        def get_control_settings():
            return jsonify(self._get_control_settings())

        @self.app.route('/api/control/settings', methods=['POST'])
        def update_control_settings():
            data = request.get_json() or {}
            use_simulated_devices = bool(data.get('use_simulated_devices', True))
            settings = self._set_control_settings(use_simulated_devices)
            return jsonify({'success': True, **settings})
        
        # 设备列表
        @self.app.route('/api/devices', methods=['GET'])
        def get_devices():
            return jsonify(self.device_manager.get_devices())

        # 候选设备列表
        @self.app.route('/api/devices/candidates', methods=['GET'])
        def get_device_candidates():
            return jsonify(self._get_candidate_device_inventory())

        @self.app.route('/api/device-models', methods=['GET'])
        def get_device_models():
            protocol = (request.args.get('protocol') or 'modbus').lower()
            if protocol != 'modbus':
                return jsonify({'protocol': protocol, 'device_types': []})
            return jsonify(get_modbus_device_model_catalog())
        
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

        # 最新采集快照
        @self.app.route('/api/collector/latest', methods=['GET'])
        def get_collector_latest():
            device_id = request.args.get('device_id')
            return jsonify(self.data_collector.get_latest_data(device_id))
        
        # 数据库统计
        @self.app.route('/api/database', methods=['GET'])
        def get_database_stats():
            return jsonify(self.database.get_device_stats())

        # 仿真场景列表
        @self.app.route('/api/simulation/scenarios', methods=['GET'])
        def get_simulation_scenarios():
            protocol = self._get_simulation_protocol()
            if not protocol:
                return jsonify({
                    'enabled': False,
                    'current': None,
                    'scenarios': []
                })

            return jsonify({
                'enabled': True,
                'current': protocol.get_current_scenario(),
                'scenarios': protocol.list_scenarios()
            })

        # 切换仿真场景
        @self.app.route('/api/simulation/scenario', methods=['POST'])
        def switch_simulation_scenario():
            protocol = self._get_simulation_protocol()
            if not protocol:
                return jsonify({'success': False, 'message': '仿真未启用'}), 400

            data = request.get_json() or {}
            scenario = data.get('scenario')
            if not scenario:
                return jsonify({'success': False, 'message': '场景不能为空'}), 400

            if not protocol.switch_scenario(scenario):
                return jsonify({'success': False, 'message': f'场景切换失败: {scenario}'}), 400

            self.device_manager.refresh_protocol_candidates('simulation', clear_active=True)
            simulation_candidates = [
                device for device in self.device_manager.get_device_candidates()
                if device.get('protocol') == 'simulation'
            ]

            return jsonify({
                'success': True,
                'current': protocol.get_current_scenario(),
                'candidate_count': len(simulation_candidates),
                'devices': simulation_candidates
            })
        
        # ============ 新增：设备管理API ============
        
        # 测试Modbus连接
        @self.app.route('/api/devices/test-modbus', methods=['POST'])
        def test_modbus_connection():
            try:
                data = request.get_json() or {}
                unit_id = data.get('unit_id', 1)
                device_type = data.get('device_type')
                vendor = data.get('vendor')
                model = data.get('model')
                config = self._build_modbus_endpoint_config(data)
                protocol = create_modbus_protocol(config)

                if not protocol.connect():
                    return jsonify({'success': False, 'message': '连接失败'})

                try:
                    probe_register = get_modbus_model_probe_register(
                        device_type=str(device_type) if device_type is not None else None,
                        model=str(model) if model is not None else None,
                        vendor=str(vendor) if vendor is not None else None,
                    ) or {'addr': 0, 'type': 'u16'}
                    test_value = protocol.read_data(str(unit_id), probe_register)
                finally:
                    protocol.disconnect()

                return jsonify({
                    'success': True,
                    'message': '连接成功',
                    'test_value': test_value
                })
            except Exception as e:
                return jsonify({'success': False, 'message': str(e)})
        
        # 添加Modbus设备
        @self.app.route('/api/devices/add-modbus', methods=['POST'])
        def add_modbus_device():
            try:
                data = request.get_json() or {}
                device_id = data.get('device_id')
                device_type = data.get('device_type', 'modbus_device')
                model = data.get('model')  # 【新增】型号标识
                
                if not device_id:
                    return jsonify({'success': False, 'message': '设备ID不能为空'})
                
                # 测试连接
                config = self._build_modbus_endpoint_config(data)
                protocol = create_modbus_protocol(config)
                
                if not protocol.connect():
                    return jsonify({'success': False, 'message': '设备连接失败'})
                
                protocol.disconnect()
                
                # 保存设备信息
                device_info = {
                    'device_id': device_id,
                    'type': device_type,
                    'vendor': data.get('vendor'),
                    'model': model,  # 【新增】型号标识
                    'protocol': 'modbus',
                    'unit_id': data.get('unit_id', 1),
                    'status': 'online'
                }
                device_info.update(config)

                self._ensure_modbus_protocol(config)
                if not self.device_manager.register_device_candidate(device_info):
                    return jsonify({'success': False, 'message': '候选设备注册失败'})
                
                return jsonify({
                    'success': True, 
                    'message': '候选设备添加成功',
                    'device': device_info
                })
            except Exception as e:
                return jsonify({'success': False, 'message': str(e)})
        
        # 读取Modbus寄存器
        @self.app.route('/api/devices/<device_id>/read-register', methods=['POST'])
        def read_modbus_register(device_id):
            try:
                data = request.get_json()
                register = data.get('register', '0')
                
                device_info = self._get_modbus_device_info(device_id)
                if not device_info:
                    return jsonify({'success': False, 'message': '设备不存在或不支持该接口'})
                
                config = self._build_modbus_endpoint_config(device_info)
                
                protocol = create_modbus_protocol(config)
                if not protocol.connect():
                    return jsonify({'success': False, 'message': '设备连接失败'})
                
                value = protocol.read_data(str(device_info['unit_id']), register)
                protocol.disconnect()
                
                return jsonify({
                    'success': True,
                    'register': register,
                    'value': value
                })
            except Exception as e:
                return jsonify({'success': False, 'message': str(e)})
        
        # 写入Modbus寄存器
        @self.app.route('/api/devices/<device_id>/write-register', methods=['POST'])
        def write_modbus_register(device_id):
            try:
                data = request.get_json()
                register = data.get('register', '0')
                value = data.get('value', 0)
                
                device_info = self._get_modbus_device_info(device_id)
                if not device_info:
                    return jsonify({'success': False, 'message': '设备不存在或不支持该接口'})
                
                config = self._build_modbus_endpoint_config(device_info)
                
                protocol = create_modbus_protocol(config)
                if not protocol.connect():
                    return jsonify({'success': False, 'message': '设备连接失败'})
                
                success = protocol.write_data(str(device_info['unit_id']), register, value)
                protocol.disconnect()
                
                if success:
                    return jsonify({'success': True, 'message': '写入成功'})
                else:
                    return jsonify({'success': False, 'message': '写入失败'})
            except Exception as e:
                return jsonify({'success': False, 'message': str(e)})
        
        # 【新增】按型号点表读取枪数据
        @self.app.route('/api/devices/<device_id>/gun-data', methods=['GET'])
        def read_gun_data(device_id):
            try:
                gun_id = int(request.args.get('gun_id', 1))
                
                device_info = self._get_modbus_device_info(device_id)
                if not device_info:
                    return jsonify({'success': False, 'message': '设备不存在或不支持该接口'})
                model = device_info.get('model', 'generic_charger')
                connector_device_id = build_connector_device_id(device_info['device_id'], gun_id)
                connector_info = self.device_manager.get_device(connector_device_id)
                if not connector_info:
                    return jsonify({'success': False, 'message': f'型号 {model} 不支持枪{gun_id}'})

                telemetry_map = connector_info.get('telemetry_map', {})
                if not isinstance(telemetry_map, dict) or not telemetry_map:
                    return jsonify({'success': False, 'message': f'型号 {model} 未配置枪{gun_id}采集点表'})

                result = {'gun_id': gun_id, 'model': model}
                for name, cfg in telemetry_map.items():
                    try:
                        value = self.device_manager.read_device_data(connector_device_id, name)
                        unit = cfg.get('unit', '') if isinstance(cfg, dict) else ''
                        result[name] = {
                            'value': value,
                            'unit': unit,
                        }
                    except Exception as e:
                        result[name] = {'value': None, 'error': str(e)}

                return jsonify({'success': True, 'data': result})
                
            except Exception as e:
                return jsonify({'success': False, 'message': str(e)})
        
        # 获取已连接设备列表
        @self.app.route('/api/devices/connected', methods=['GET'])
        def get_connected_devices():
            return jsonify(self.device_manager.get_devices())

        @self.app.route('/api/devices/candidates/<device_id>/activate', methods=['POST'])
        def activate_candidate_device(device_id):
            if self.device_manager.activate_device(device_id):
                return jsonify({'success': True, 'message': '设备已接入'})
            return jsonify({'success': False, 'message': '候选设备不存在或接入失败'}), 404

        @self.app.route('/api/devices/candidates/<device_id>', methods=['DELETE'])
        def delete_candidate_device(device_id):
            if self.device_manager.is_device_connected(device_id):
                return jsonify({'success': False, 'message': '设备已接入，请先断开'}), 409
            if self.device_manager.unregister_device_candidate(device_id):
                return jsonify({'success': True, 'message': '候选设备已删除'})
            return jsonify({'success': False, 'message': '候选设备不存在'}), 404
        
        # 【新增】设备控制API
        @self.app.route('/api/devices/<device_id>/control', methods=['POST'])
        def control_device(device_id):
            """设备控制API"""
            try:
                data = request.get_json()
                action = data.get('action')  # start_charging/stop_charging/set_power/emergency_stop/clear_fault
                gun_id = data.get('gun_id', 1)
                params = data.get('params', {})
                
                device_info = self._get_modbus_device_info(device_id)
                if not device_info:
                    return jsonify({'success': False, 'message': '设备不存在或不支持该接口'})

                target_device_id = device_info.get('device_id', device_id)
                if device_info.get('type') == 'charging_station':
                    target_device_id = build_connector_device_id(target_device_id, int(gun_id))

                target_device = self.device_manager.get_device(target_device_id)
                if not target_device:
                    return jsonify({'success': False, 'message': '充电枪不存在或未接入'})

                control_map = target_device.get('control_map', {}) if isinstance(target_device, dict) else {}
                register = None
                value: Any = 1
                if action == 'start_charging':
                    power_w = int(float(params.get('power_kw', 120)) * 1000)
                    if isinstance(control_map, dict) and 'power_limit' in control_map:
                        register = 'power_limit'
                        value = power_w
                    else:
                        register = 'start_charging'
                elif action == 'stop_charging':
                    register = 'stop_charging'
                elif action == 'set_power':
                    register = 'power_limit'
                    value = int(float(params.get('power_kw', 120)) * 1000)
                elif action == 'set_soc':
                    return jsonify({'success': False, 'message': '当前不支持目标SOC控制'}), 400
                elif action == 'emergency_stop':
                    register = 'emergency_stop'
                elif action == 'clear_fault':
                    register = 'clear_fault'
                else:
                    return jsonify({'success': False, 'message': f'未知操作: {action}'})

                result = self.device_manager.write_device_data(target_device_id, register, value)
                
                return jsonify({
                    'success': result,
                    'message': '操作成功' if result else '操作失败'
                })
                
            except Exception as e:
                return jsonify({'success': False, 'message': str(e)})
        
        # 删除设备
        @self.app.route('/api/devices/<device_id>', methods=['DELETE'])
        def delete_device(device_id):
            if self.device_manager.unregister_device(device_id):
                return jsonify({'success': True, 'message': '设备已断开'})
            return jsonify({'success': False, 'message': '设备不存在'})
        
        # 主页 - 使用外部模板文件
        @self.app.route('/')
        def index():
            return render_template('index.html')
    
    def start(self) -> bool:
        """启动监控面板
        
        Returns:
            bool: 启动是否成功
        """
        try:
            self.running = True
            self.server_thread = threading.Thread(target=self._run_server, daemon=True)
            self.server_thread.start()
            self.logger.info("启动监控面板（增强版），访问地址: http://%s:%s", self.host, self.port)
            return True
        except Exception as e:
            self.logger.error("启动监控面板失败: %s", e)
            self.running = False
            return False
    
    def stop(self) -> bool:
        """停止监控面板
        
        Returns:
            bool: 停止是否成功
        """
        try:
            self.running = False
            self.logger.info("停止监控面板")
            return True
        except Exception as e:
            self.logger.error("停止监控面板失败: %s", e)
            return False
    
    def _run_server(self):
        """运行Flask服务器"""
        try:
            self.app.run(host=self.host, port=self.port, debug=False, use_reloader=False)
        except Exception as e:
            self.logger.error("服务器运行失败: %s", e)
            self.running = False
    
    def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态
        
        Returns:
            Dict[str, Any]: 系统状态
        """
        device_stats = self.database.get_device_stats()
        collector_status = self.data_collector.get_data_summary()
        strategy_status = self.get_strategies_status()
        
        # 获取设备总数和在线设备数
        all_devices = self.device_manager.get_devices()
        device_count = len(all_devices)
        online_devices = sum(1 for d in all_devices if d.get('status') == 'online')
        
        return {
            'status': 'running' if self.running else 'stopped',
            'dashboard_url': f"http://{self.host}:{self.port}",
            'device_stats': device_stats,
            'collector_status': collector_status,
            'strategy_status': strategy_status,
            'device_count': device_count,
            'online_devices': online_devices
        }

    def _build_modbus_endpoint_config(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        transport = str(payload.get('transport', payload.get('mode', 'tcp'))).lower()
        timeout = int(payload.get('timeout', 5))
        if transport in {'rtu', 'serial'}:
            return {
                'transport': 'rtu',
                'serial_port': str(payload.get('serial_port', payload.get('port', ''))),
                'baudrate': int(payload.get('baudrate', 9600)),
                'bytesize': int(payload.get('bytesize', 8)),
                'parity': str(payload.get('parity', 'N')),
                'stopbits': int(payload.get('stopbits', 1)),
                'timeout': timeout,
            }

        return {
            'transport': 'tcp',
            'host': str(payload.get('host', 'localhost')),
            'port': int(payload.get('port', 502)),
            'timeout': timeout,
        }

    def _ensure_modbus_protocol(self, endpoint_config: Dict[str, Any]):
        """确保设备管理器中存在Modbus协议占位实例。"""
        if 'modbus' in self.device_manager.protocols:
            protocol = self.device_manager.protocols['modbus']
            is_connected = bool(getattr(protocol, 'is_connected', getattr(protocol, 'connected', False)))
            if not is_connected:
                protocol.connect()
            return

        protocol = create_modbus_protocol(endpoint_config)
        protocol.connect()
        self.device_manager.protocols['modbus'] = protocol

    def _get_modbus_device_info(self, device_id: str) -> Optional[Dict[str, Any]]:
        """获取支持Dashboard直连接口的Modbus设备信息。"""
        device_info = self.device_manager.get_device(device_id)
        if not device_info:
            return None

        if device_info.get('protocol') != 'modbus':
            return None
        transport = str(device_info.get('transport', 'tcp')).lower()
        if transport in {'rtu', 'serial'}:
            required_fields = ('serial_port', 'unit_id')
        else:
            required_fields = ('host', 'port', 'unit_id')
        if any(field not in device_info for field in required_fields):
            return None

        return device_info

    def _get_candidate_device_inventory(self) -> List[Dict[str, Any]]:
        inventory: List[Dict[str, Any]] = []
        for device in self.device_manager.get_device_candidates():
            item = dict(device)
            item['connected'] = self.device_manager.is_device_connected(item.get('device_id', ''))
            inventory.append(item)
        return inventory

    def _get_simulation_protocol(self) -> Optional[SimulationProtocol]:
        protocol = self.device_manager.protocols.get('simulation')
        if isinstance(protocol, SimulationProtocol) and protocol.is_connected:
            return protocol
        return None

    def _get_mode_controller(self) -> Optional[StrategyBase]:
        strategy = self.strategies.get('mode_controller')
        if strategy:
            return strategy

        for strategy in self.strategies.values():
            if hasattr(strategy, 'get_mode_summary') and hasattr(strategy, 'get_mode_config'):
                return strategy
        return None

    def _build_fallback_mode_config(self) -> Dict[str, Any]:
        config = getattr(self.data_collector, 'config', None)
        use_simulated_devices = True
        state_config = {'max_data_age_seconds': 30, 'manual_override': False}
        export_settings = {
            'export_limit_w': 5000,
            'export_enter_ratio': 1.0,
            'storage_soc_soft_limit': 95,
        }
        export_enabled = True

        if config and hasattr(config, 'get'):
            use_simulated_devices = bool(config.get('control.use_simulated_devices', True))
            state_config['max_data_age_seconds'] = int(config.get('control.mode_controller.state.max_data_age_seconds', 30))
            state_config['manual_override'] = bool(config.get('control.mode_controller.state.manual_override', False))
            export_enabled = bool(config.get('control.mode_controller.mode.export_protect_enabled', True))
            export_settings['export_limit_w'] = int(config.get('control.mode_controller.mode.export_limit_w', 5000))
            export_settings['export_enter_ratio'] = float(config.get('control.mode_controller.mode.export_enter_ratio', 1.0))
            export_settings['storage_soc_soft_limit'] = float(config.get('control.mode_controller.mode.storage_soc_soft_limit', 95))

        return {
            'use_simulated_devices': use_simulated_devices,
            'state': state_config,
            'modes': {
                'manual_override': {
                    'name': 'manual_override',
                    'label': '人工接管',
                    'description': '人工接管时暂停自动模式控制。',
                    'enabled': True,
                    'configurable': True,
                    'toggleable': False,
                    'settings': {
                        'active': bool(state_config['manual_override']),
                    },
                    'fields': [
                        {
                            'key': 'active',
                            'label': '手动接管激活',
                            'type': 'boolean',
                            'description': '开启后系统强制进入人工接管模式。',
                        }
                    ],
                },
                'safe_hold': {
                    'name': 'safe_hold',
                    'label': '保守运行',
                    'description': '关键测量缺失或不可信时，系统只保留监控和保守动作。',
                    'enabled': True,
                    'configurable': True,
                    'toggleable': False,
                    'settings': {
                        'max_data_age_seconds': int(state_config['max_data_age_seconds']),
                    },
                    'fields': [
                        {
                            'key': 'max_data_age_seconds',
                            'label': '最大数据时效（秒）',
                            'type': 'number',
                            'min': 1,
                            'step': 1,
                            'description': '超过该时效的关键测量会触发保守运行。',
                        }
                    ],
                },
                'business_normal': {
                    'name': 'business_normal',
                    'label': '正常运行',
                    'description': '默认模式，系统保持监控和轻量运行。',
                    'enabled': True,
                    'configurable': False,
                    'toggleable': False,
                    'settings': {},
                    'fields': [],
                },
                'export_protect': {
                    'name': 'export_protect',
                    'label': '反送保护',
                    'description': '反送功率超限时，优先用储能、充电负荷和光伏限发消纳光伏。',
                    'enabled': export_enabled,
                    'configurable': True,
                    'settings': export_settings,
                    'toggleable': True,
                    'fields': [
                        {
                            'key': 'export_limit_w',
                            'label': '反送上限（W）',
                            'type': 'number',
                            'min': 0,
                            'step': 100,
                        },
                        {
                            'key': 'export_enter_ratio',
                            'label': '进入比例',
                            'type': 'number',
                            'min': 0,
                            'step': 0.05,
                        },
                        {
                            'key': 'storage_soc_soft_limit',
                            'label': '储能 SOC 软上限',
                            'type': 'number',
                            'min': 0,
                            'max': 100,
                            'step': 1,
                        },
                    ],
                },
            },
        }

    def _get_mode_summary(self) -> Dict[str, Any]:
        controller = self._get_mode_controller()
        if controller and hasattr(controller, 'get_mode_summary'):
            return controller.get_mode_summary()

        devices = self.device_manager.get_devices()
        return {
            'current_mode': 'business_normal',
            'current_mode_label': '正常运行',
            'current_reason': 'mode_controller_unavailable',
            'control_state': 'monitor_only',
            'supported_modes': [],
            'key_measurements': {
                'timestamp': None,
                'grid_power_w': None,
                'pv_power_w': 0,
            },
            'trust': {
                'trusted': False,
                'issues': ['mode_controller_unavailable'],
            },
            'blockers': ['mode_controller_unavailable'],
            'counts': {
                'active_devices': len(devices),
                'online_devices': sum(1 for d in devices if d.get('status') == 'online'),
                'participating_devices': 0,
            },
            'participating_devices': [],
            'recent_actions': [],
            'use_simulated_devices': self._get_control_settings()['use_simulated_devices'],
        }

    def _get_mode_config(self) -> Dict[str, Any]:
        controller = self._get_mode_controller()
        if controller and hasattr(controller, 'get_mode_config'):
            return controller.get_mode_config()
        return self._build_fallback_mode_config()

    def _set_mode_config(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        controller = self._get_mode_controller()
        if controller and hasattr(controller, 'update_mode_config'):
            mode_config = controller.update_mode_config(updates)
        else:
            mode_config = self._build_fallback_mode_config()
            if 'use_simulated_devices' in updates:
                mode_config['use_simulated_devices'] = bool(updates['use_simulated_devices'])

        config = getattr(self.data_collector, 'config', None)
        if config and hasattr(config, 'set'):
            config.set('control.use_simulated_devices', mode_config['use_simulated_devices'])
            config.set(
                'control.mode_controller.state.max_data_age_seconds',
                int(mode_config['state']['max_data_age_seconds']),
            )
            config.set(
                'control.mode_controller.state.manual_override',
                bool(mode_config['state'].get('manual_override', False)),
            )
            export_protect = mode_config['modes']['export_protect']
            config.set(
                'control.mode_controller.mode.export_protect_enabled',
                bool(export_protect['enabled']),
            )
            config.set(
                'control.mode_controller.mode.export_limit_w',
                int(export_protect['settings']['export_limit_w']),
            )
            config.set(
                'control.mode_controller.mode.export_enter_ratio',
                float(export_protect['settings']['export_enter_ratio']),
            )
            config.set(
                'control.mode_controller.mode.storage_soc_soft_limit',
                float(export_protect['settings']['storage_soc_soft_limit']),
            )

        for strategy in self.strategies.values():
            if hasattr(strategy, 'use_simulated_devices'):
                strategy.use_simulated_devices = bool(mode_config['use_simulated_devices'])
            if hasattr(strategy, 'config') and isinstance(strategy.config, dict):
                strategy.config['use_simulated_devices'] = bool(mode_config['use_simulated_devices'])

        return mode_config

    def _get_control_settings(self) -> Dict[str, Any]:
        mode_config = self._get_mode_config()
        return {'use_simulated_devices': bool(mode_config.get('use_simulated_devices', True))}

    def _set_control_settings(self, use_simulated_devices: bool) -> Dict[str, Any]:
        mode_config = self._set_mode_config({'use_simulated_devices': use_simulated_devices})
        return {'use_simulated_devices': bool(mode_config.get('use_simulated_devices', True))}
    
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
