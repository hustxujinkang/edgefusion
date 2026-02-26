# 监控面板（增强版）
from typing import Dict, Any, List, Optional
from flask import Flask, jsonify, request, render_template
import threading
import time
import os
from ..device_manager import DeviceManager
from ..strategy import StrategyBase
from .collector import DataCollector
from .database import Database
from ..protocol import ModbusProtocol
from ..point_tables import get_gun_registers, get_point_table


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
        self.connected_devices: Dict[str, Any] = {}
        
        # 配置模板目录
        template_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates')
        self.app = Flask(__name__, template_folder=template_dir)
        
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
        
        # ============ 新增：设备管理API ============
        
        # 测试Modbus连接
        @self.app.route('/api/devices/test-modbus', methods=['POST'])
        def test_modbus_connection():
            try:
                data = request.get_json()
                host = data.get('host', 'localhost')
                port = data.get('port', 502)
                unit_id = data.get('unit_id', 1)
                
                config = {'host': host, 'port': port, 'timeout': 5}
                protocol = ModbusProtocol(config)
                
                if protocol.connect():
                    # 尝试读取一个寄存器验证连接
                    test_value = protocol.read_data(str(unit_id), '0')
                    protocol.disconnect()
                    return jsonify({
                        'success': True, 
                        'message': '连接成功',
                        'test_value': test_value
                    })
                else:
                    return jsonify({'success': False, 'message': '连接失败'})
            except Exception as e:
                return jsonify({'success': False, 'message': str(e)})
        
        # 添加Modbus设备
        @self.app.route('/api/devices/add-modbus', methods=['POST'])
        def add_modbus_device():
            try:
                data = request.get_json()
                device_id = data.get('device_id')
                host = data.get('host', 'localhost')
                port = data.get('port', 502)
                unit_id = data.get('unit_id', 1)
                device_type = data.get('device_type', 'modbus_device')
                model = data.get('model')  # 【新增】型号标识
                
                if not device_id:
                    return jsonify({'success': False, 'message': '设备ID不能为空'})
                
                # 测试连接
                config = {'host': host, 'port': port, 'timeout': 5}
                protocol = ModbusProtocol(config)
                
                if not protocol.connect():
                    return jsonify({'success': False, 'message': '设备连接失败'})
                
                protocol.disconnect()
                
                # 保存设备信息
                device_info = {
                    'device_id': device_id,
                    'type': device_type,
                    'model': model,  # 【新增】型号标识
                    'protocol': 'modbus',
                    'host': host,
                    'port': port,
                    'unit_id': unit_id,
                    'status': 'online'
                }
                
                self.connected_devices[device_id] = device_info
                
                return jsonify({
                    'success': True, 
                    'message': '设备添加成功',
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
                
                if device_id not in self.connected_devices:
                    return jsonify({'success': False, 'message': '设备不存在'})
                
                device_info = self.connected_devices[device_id]
                
                config = {
                    'host': device_info['host'],
                    'port': device_info['port'],
                    'timeout': 5
                }
                
                protocol = ModbusProtocol(config)
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
                
                if device_id not in self.connected_devices:
                    return jsonify({'success': False, 'message': '设备不存在'})
                
                device_info = self.connected_devices[device_id]
                
                config = {
                    'host': device_info['host'],
                    'port': device_info['port'],
                    'timeout': 5
                }
                
                protocol = ModbusProtocol(config)
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
                
                if device_id not in self.connected_devices:
                    return jsonify({'success': False, 'message': '设备不存在'})
                
                device_info = self.connected_devices[device_id]
                model = device_info.get('model', 'generic_charger')
                
                # 获取该型号的点表配置
                gun_regs = get_gun_registers(model, gun_id)
                if not gun_regs:
                    return jsonify({'success': False, 'message': f'型号 {model} 不支持枪{gun_id}'})
                
                # 连接设备
                config = {
                    'host': device_info['host'],
                    'port': device_info['port'],
                    'timeout': 5
                }
                protocol = ModbusProtocol(config)
                if not protocol.connect():
                    return jsonify({'success': False, 'message': '设备连接失败'})
                
                # 按点表读取所有寄存器
                result = {'gun_id': gun_id, 'model': model}
                for name, cfg in gun_regs.items():
                    try:
                        addr = cfg['addr']
                        reg_type = cfg.get('type', 'u16')
                        scale = cfg.get('scale', 1)
                        unit = cfg.get('unit', '')
                        
                        # 计算读取数量（u32读2个寄存器，u16读1个）
                        count = 2 if reg_type == 'u32' else 1
                        
                        # 读取寄存器（传入正确的 slave_id）
                        values = protocol._read_registers(addr, count, slave_id=device_info['unit_id'])
                        if values:
                            if reg_type == 'u32':
                                # 合并两个16位寄存器为32位
                                raw_value = (values[1] << 16) | values[0]
                            else:
                                raw_value = values[0]
                            
                            # 应用缩放因子
                            scaled_value = raw_value * scale
                            
                            result[name] = {
                                'value': round(scaled_value, 3),
                                'unit': unit,
                                'raw': raw_value
                            }
                        else:
                            result[name] = {'value': None, 'error': '读取失败'}
                    except Exception as e:
                        result[name] = {'value': None, 'error': str(e)}
                
                protocol.disconnect()
                return jsonify({'success': True, 'data': result})
                
            except Exception as e:
                return jsonify({'success': False, 'message': str(e)})
        
        # 获取已连接设备列表
        @self.app.route('/api/devices/connected', methods=['GET'])
        def get_connected_devices():
            return jsonify(list(self.connected_devices.values()))
        
        # 删除设备
        @self.app.route('/api/devices/<device_id>', methods=['DELETE'])
        def delete_device(device_id):
            if device_id in self.connected_devices:
                del self.connected_devices[device_id]
                return jsonify({'success': True, 'message': '设备已删除'})
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
            print(f"启动监控面板（增强版），访问地址: http://{self.host}:{self.port}")
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
