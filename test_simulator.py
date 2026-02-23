#!/usr/bin/env python3
# 设备模拟器测试脚本
import sys
import os
import time

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from edgefusion.simulator import SimulatorManager


def test_pv_simulator():
    """测试光伏模拟器"""
    print("\n=== 测试光伏模拟器 ===")
    try:
        manager = SimulatorManager()
        pv = manager.create_pv_simulator("test_pv")
        
        print(f"光伏模拟器创建成功: {pv.device_id}")
        print(f"初始功率: {pv.get_data('power')} W")
        print(f"初始能量: {pv.get_data('energy')} kWh")
        
        # 更新状态
        pv.update()
        print(f"更新后功率: {pv.get_data('power')} W")
        print(f"更新后能量: {pv.get_data('energy')} kWh")
        print(f"设备状态: {pv.get_status()}")
        
        # 测试设置模式
        pv.set_data('mode', 'manual')
        print(f"设置模式后: {pv.get_data('mode')}")
        
        return True
    except Exception as e:
        print(f"光伏模拟器测试失败: {e}")
        return False


def test_storage_simulator():
    """测试储能模拟器"""
    print("\n=== 测试储能模拟器 ===")
    try:
        manager = SimulatorManager()
        storage = manager.create_storage_simulator("test_storage")
        
        print(f"储能模拟器创建成功: {storage.device_id}")
        print(f"初始SOC: {storage.get_data('soc')}%")
        print(f"初始功率: {storage.get_data('power')} W")
        
        # 测试充电模式
        storage.set_data('mode', 'charge')
        print(f"设置充电模式后功率: {storage.get_data('power')} W")
        
        # 更新状态
        storage.update()
        time.sleep(1)
        storage.update()
        print(f"充电后SOC: {storage.get_data('soc')}%")
        
        # 测试放电模式
        storage.set_data('mode', 'discharge')
        print(f"设置放电模式后功率: {storage.get_data('power')} W")
        
        # 更新状态
        storage.update()
        time.sleep(1)
        storage.update()
        print(f"放电后SOC: {storage.get_data('soc')}%")
        
        return True
    except Exception as e:
        print(f"储能模拟器测试失败: {e}")
        return False


def test_charger_simulator():
    """测试充电桩模拟器"""
    print("\n=== 测试充电桩模拟器 ===")
    try:
        manager = SimulatorManager()
        charger = manager.create_charger_simulator("test_charger")
        
        print(f"充电桩模拟器创建成功: {charger.device_id}")
        print(f"初始状态: {charger.get_data('status')}")
        print(f"初始功率: {charger.get_data('power')} W")
        
        # 测试充电状态
        charger.set_data('status', 'Charging')
        print(f"设置充电状态后: {charger.get_data('status')}")
        print(f"充电功率: {charger.get_data('power')} W")
        
        # 更新状态
        charger.update()
        time.sleep(1)
        charger.update()
        print(f"充电后能量: {charger.get_data('energy')} kWh")
        
        # 测试空闲状态
        charger.set_data('status', 'Available')
        print(f"设置空闲状态后: {charger.get_data('status')}")
        print(f"空闲功率: {charger.get_data('power')} W")
        
        return True
    except Exception as e:
        print(f"充电桩模拟器测试失败: {e}")
        return False


def test_simulator_manager():
    """测试模拟器管理器"""
    print("\n=== 测试模拟器管理器 ===")
    try:
        manager = SimulatorManager()
        
        # 创建多个模拟器
        pv1 = manager.create_pv_simulator()
        pv2 = manager.create_pv_simulator()
        storage = manager.create_storage_simulator()
        charger = manager.create_charger_simulator()
        
        print(f"创建的模拟器数量: {len(manager.get_all_simulators())}")
        print(f"光伏模拟器数量: {len(manager.get_simulators_by_type('pv'))}")
        print(f"储能模拟器数量: {len(manager.get_simulators_by_type('energy_storage'))}")
        print(f"充电桩模拟器数量: {len(manager.get_simulators_by_type('charging_station'))}")
        
        # 测试更新所有
        manager.update_all()
        print("更新所有模拟器成功")
        
        # 测试获取信息
        info = manager.get_all_simulator_info()
        print(f"获取所有模拟器信息成功，数量: {len(info)}")
        
        # 测试移除模拟器
        result = manager.remove_simulator(pv1.device_id)
        print(f"移除模拟器结果: {result}")
        print(f"移除后模拟器数量: {len(manager.get_all_simulators())}")
        
        return True
    except Exception as e:
        print(f"模拟器管理器测试失败: {e}")
        return False


def main():
    """主测试函数"""
    print("EdgeFusion 设备模拟器测试")
    print("=" * 50)
    
    tests = [
        test_pv_simulator,
        test_storage_simulator,
        test_charger_simulator,
        test_simulator_manager
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
        print("所有模拟器测试通过！")
        return 0
    else:
        print("部分模拟器测试失败，需要检查。")
        return 1


if __name__ == '__main__':
    sys.exit(main())
