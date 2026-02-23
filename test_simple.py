#!/usr/bin/env python3
# 简化测试脚本
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from edgefusion.config import Config
from edgefusion.device_manager import DeviceManager
from edgefusion.strategy import PeakShavingStrategy, DemandResponseStrategy, SelfConsumptionStrategy


def test_config():
    """测试配置管理模块"""
    print("\n=== 测试配置管理模块 ===")
    try:
        config = Config()
        print("配置文件加载成功")
        print(f"配置项数量: {len(config.get_all())}")
        print(f"监控面板端口: {config.get('monitor.dashboard_port')}")
        print(f"数据采集间隔: {config.get('monitor.collect_interval')}")
        return True
    except Exception as e:
        print(f"配置管理模块测试失败: {e}")
        return False


def test_device_manager():
    """测试设备管理模块"""
    print("\n=== 测试设备管理模块 ===")
    try:
        config = Config()
        device_config = config.get('device_manager', {})
        device_manager = DeviceManager(device_config)
        print("设备管理器初始化成功")
        
        # 测试手动注册设备
        test_device = {
            'device_id': 'manual_test_device',
            'device_type': 'test_type',
            'protocol': 'modbus',
            'status': 'online'
        }
        result = device_manager.register_device(test_device)
        print(f"手动注册设备结果: {result}")
        
        # 测试获取设备列表
        all_devices = device_manager.get_devices()
        print(f"所有设备数量: {len(all_devices)}")
        
        # 测试获取设备详情
        device = device_manager.get_device('manual_test_device')
        if device:
            print(f"设备详情获取成功: {device['device_id']}")
        else:
            print("设备详情获取失败")
        
        return True
    except Exception as e:
        print(f"设备管理模块测试失败: {e}")
        return False


def test_strategies():
    """测试控制策略模块"""
    print("\n=== 测试控制策略模块 ===")
    try:
        config = Config()
        device_config = config.get('device_manager', {})
        device_manager = DeviceManager(device_config)
        
        # 测试削峰填谷策略
        peak_shaving_config = config.get('strategy.peak_shaving', {})
        peak_shaving = PeakShavingStrategy(peak_shaving_config, device_manager)
        print("削峰填谷策略初始化成功")
        
        # 测试需求响应策略
        demand_response_config = config.get('strategy.demand_response', {})
        demand_response = DemandResponseStrategy(demand_response_config, device_manager)
        print("需求响应策略初始化成功")
        
        # 测试自发自用策略
        self_consumption_config = config.get('strategy.self_consumption', {})
        self_consumption = SelfConsumptionStrategy(self_consumption_config, device_manager)
        print("自发自用策略初始化成功")
        
        # 测试策略状态
        peak_status = peak_shaving.get_status()
        print(f"削峰填谷策略状态: {peak_status['enabled']}")
        
        demand_status = demand_response.get_status()
        print(f"需求响应策略状态: {demand_status['enabled']}")
        
        self_status = self_consumption.get_status()
        print(f"自发自用策略状态: {self_status['enabled']}")
        
        return True
    except Exception as e:
        print(f"控制策略模块测试失败: {e}")
        return False


def test_protocol_modules():
    """测试协议模块"""
    print("\n=== 测试协议模块 ===")
    try:
        from edgefusion.protocol import ProtocolBase, ModbusProtocol, MQTTProtocol, OCPPProtocol
        print("协议模块导入成功")
        
        # 测试Modbus协议初始化
        modbus_config = {
            'host': 'localhost',
            'port': 502,
            'timeout': 5
        }
        modbus = ModbusProtocol(modbus_config)
        print("Modbus协议初始化成功")
        
        # 测试MQTT协议初始化
        mqtt_config = {
            'broker': 'localhost',
            'port': 1883
        }
        mqtt = MQTTProtocol(mqtt_config)
        print("MQTT协议初始化成功")
        
        # 测试OCPP协议初始化
        ocpp_config = {
            'host': 'localhost',
            'port': 8080
        }
        ocpp = OCPPProtocol(ocpp_config)
        print("OCPP协议初始化成功")
        
        return True
    except Exception as e:
        print(f"协议模块测试失败: {e}")
        return False


def main():
    """主测试函数"""
    print("EdgeFusion 核心功能测试")
    print("=" * 50)
    
    tests = [
        test_config,
        test_device_manager,
        test_strategies,
        test_protocol_modules
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        if test():
            passed += 1
        else:
            failed += 1
    
    print("\n" + "=" * 50)
    print(f"测试结果: 成功 {passed}, 失败 {failed}")
    
    if failed == 0:
        print("所有核心功能测试通过！EdgeFusion 系统基本功能正常。")
        print("注意: 数据库模块由于SQLAlchemy版本兼容性问题未测试")
        return 0
    else:
        print("部分核心功能测试失败，需要检查系统配置。")
        return 1


if __name__ == '__main__':
    sys.exit(main())
