#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Modbus集成测试脚本
测试Modbus充电桩模拟器和后台协议的通信
"""

import sys
import os
import time

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from edgefusion.protocol import ModbusProtocol


def test_modbus_connection():
    """测试Modbus连接和数据读取"""
    print("=" * 60)
    print("Modbus集成测试")
    print("=" * 60)
    
    # 创建Modbus协议实例
    config = {
        'host': 'localhost',
        'port': 502,
        'timeout': 5
    }
    
    print(f"\n1. 连接到Modbus设备 {config['host']}:{config['port']}...")
    modbus = ModbusProtocol(config)
    
    if not modbus.connect():
        print("❌ 连接失败！请确保Modbus模拟器已启动")
        print("   运行命令: python modbus_charger_simulator.py")
        return False
    
    print("✅ 连接成功！")
    
    # 测试读取寄存器
    print("\n2. 读取充电桩数据...")
    
    test_registers = [
        (0, "电压", 10, "V"),
        (1, "电流", 10, "A"),
        (2, "功率", 1, "W"),
        (3, "累计能量", 100, "kWh"),
        (4, "温度", 10, "°C"),
        (5, "状态", 1, ""),
        (6, "充电时间", 1, "秒"),
        (10, "设备类型", 1, ""),
        (11, "额定功率", 1, "kW"),
    ]
    
    all_success = True
    for addr, name, scale, unit in test_registers:
        value = modbus.read_data('1', str(addr))
        if value is not None:
            scaled_value = value / scale if scale != 1 else value
            status_text = ""
            if addr == 5:
                status_map = {0: "可用", 1: "充电中", 2: "故障"}
                status_text = f" ({status_map.get(value, '未知')})"
            print(f"   ✅ {name}: {scaled_value}{unit}{status_text}")
        else:
            print(f"   ❌ {name}: 读取失败")
            all_success = False
    
    # 测试状态描述
    status_value = modbus.read_data('1', '5')
    if status_value is not None:
        status_map = {0: "空闲可用", 1: "充电中", 2: "故障"}
        print(f"\n3. 充电桩状态: {status_map.get(status_value, '未知')}")
    
    # 断开连接
    print("\n4. 断开连接...")
    modbus.disconnect()
    print("✅ 已断开")
    
    print("\n" + "=" * 60)
    if all_success:
        print("🎉 所有测试通过！")
        print("\n下一步:")
        print("  1. 保持Modbus模拟器运行")
        print("  2. 启动后台: python -m edgefusion.main")
        print("  3. 访问: http://localhost:5000")
        return True
    else:
        print("⚠️  部分测试失败")
        return False


if __name__ == '__main__':
    try:
        success = test_modbus_connection()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 测试出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
