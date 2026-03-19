#!/usr/bin/env python3
# 测试脚本
import sys
import os
import copy

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from edgefusion.config import Config
from edgefusion.device_manager import DeviceManager
from edgefusion.strategy import PeakShavingStrategy, DemandResponseStrategy, SelfConsumptionStrategy
from edgefusion.strategy.mode_controller import ModeControllerStrategy
from edgefusion.monitor import DataCollector, Database, Dashboard
from edgefusion.main import EdgeFusion


def test_config():
    """测试配置管理模块"""
    print("\n=== 测试配置管理模块 ===")
    try:
        config = Config()
        print("配置文件加载成功")
        print(f"配置项数量: {len(config.get_all())}")
        print(f"监控面板端口: {config.get('monitor.dashboard_port')}")
        return True
    except Exception as e:
        print(f"配置管理模块测试失败: {e}")
        return False


def test_database():
    """测试数据库模块"""
    print("\n=== 测试数据库模块 ===")
    try:
        db = Database('sqlite:///:memory:')
        print("数据库初始化成功")
        
        # 测试插入数据
        test_data = {
            'device_id': 'test_device',
            'device_type': 'test_type',
            'timestamp': '2026-02-23T12:00:00',
            'data': {'power': 1000, 'status': 'ok'}
        }
        result = db.insert_data(test_data)
        print(f"数据插入结果: {result}")
        
        # 测试查询数据
        data_list = db.get_data_by_device('test_device')
        print(f"查询到的数据数量: {len(data_list)}")
        
        # 测试设备统计
        stats = db.get_device_stats()
        print(f"设备统计: {stats}")
        
        return True
    except Exception as e:
        print(f"数据库模块测试失败: {e}")
        return False


def test_device_manager():
    """测试设备管理模块"""
    print("\n=== 测试设备管理模块 ===")
    try:
        config = Config()
        device_config = config.get('device_manager', {})
        device_manager = DeviceManager(device_config)
        print("设备管理器初始化成功")
        
        # 测试设备发现
        devices = device_manager.discover_devices()
        print(f"发现的设备数量: {len(devices)}")
        
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
        
        # 测试策略执行
        result = peak_shaving.execute()
        print(f"削峰填谷策略执行结果: {result['status']}")
        
        result = demand_response.execute()
        print(f"需求响应策略执行结果: {result['status']}")
        
        result = self_consumption.execute()
        print(f"自发自用策略执行结果: {result['status']}")
        
        return True
    except Exception as e:
        print(f"控制策略模块测试失败: {e}")
        return False


def test_monitor():
    """测试监控模块"""
    print("\n=== 测试监控模块 ===")
    try:
        config = Config()
        device_config = config.get('device_manager', {})
        device_manager = DeviceManager(device_config)
        
        # 测试数据库
        db = Database('sqlite:///:memory:')
        
        # 测试数据采集器
        collector = DataCollector(config, device_manager, db)
        print("数据采集器初始化成功")
        
        # 测试数据采集
        data = collector.collect_data()
        print(f"采集到的数据数量: {len(data)}")
        
        # 测试监控面板
        monitor_config = config.get('monitor', {})
        dashboard = Dashboard(monitor_config, device_manager, collector, db)
        print("监控面板初始化成功")
        
        # 测试系统状态
        status = dashboard.get_system_status()
        print(f"系统状态: {status['status']}")
        print(f"监控面板URL: {status['dashboard_url']}")
        
        return True
    except Exception as e:
        print(f"监控模块测试失败: {e}")
        return False


def test_edgefusion_initializes_single_mode_controller_strategy():
    app = EdgeFusion()

    assert list(app.strategies.keys()) == ["mode_controller"]
    assert isinstance(app.strategies["mode_controller"], ModeControllerStrategy)


def test_edgefusion_wires_simulation_protocol_when_enabled(monkeypatch):
    base_config = copy.deepcopy(Config().get_all())
    base_config["device_manager"] = {}
    simulation_config = base_config.setdefault("simulation", {})
    simulation_config["enabled"] = True
    simulation_config["tick_seconds"] = 0.1
    simulation_config["scenario"] = "sunny_midday"
    simulation_config["base_load_w"] = 2000
    simulation_config.setdefault("pv", {})
    simulation_config["pv"]["count"] = 1
    simulation_config["pv"]["available_power_w"] = 7000
    simulation_config["pv"]["power_limit_w"] = 7000
    simulation_config.setdefault("storage", {})
    simulation_config["storage"]["count"] = 1
    simulation_config["storage"]["initial_mode"] = "charge"
    simulation_config["storage"]["max_charge_power_w"] = 1000
    simulation_config["storage"]["initial_charge_power_w"] = 1000
    simulation_config.setdefault("chargers", {})
    simulation_config["chargers"]["count"] = 1
    simulation_config["chargers"]["session_active"] = True
    simulation_config["chargers"]["power_w"] = 3000

    class FakeConfig:
        def __init__(self):
            self.config = copy.deepcopy(base_config)

        def get(self, key, default=None):
            value = self.config
            for part in key.split("."):
                if isinstance(value, dict) and part in value:
                    value = value[part]
                else:
                    return default
            return value

        def get_all(self):
            return self.config

    monkeypatch.setattr("edgefusion.main.Config", FakeConfig)

    app = EdgeFusion()

    try:
        assert "simulation" in app.device_manager.protocols
        app.device_manager.start()
        device_ids = {device["device_id"] for device in app.device_manager.get_device_candidates()}
        assert "grid_meter_0" in device_ids
        assert "pv_0" in device_ids
        assert app.device_manager.get_devices() == []
    finally:
        app.device_manager.stop()


def main():
    """主测试函数"""
    print("EdgeFusion 功能测试")
    print("=" * 50)
    
    tests = [
        test_config,
        test_database,
        test_device_manager,
        test_strategies,
        test_monitor
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
        print("所有测试通过！EdgeFusion 系统功能正常。")
        return 0
    else:
        print("部分测试失败，需要检查系统配置和依赖。")
        return 1


if __name__ == '__main__':
    sys.exit(main())
