#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Modbus/TCP 充电桩模拟器
用于在PC上模拟真实的Modbus TCP充电桩设备
"""

import sys
import time
import threading
from datetime import datetime
from pymodbus.server import StartTcpServer
from pymodbus.datastore import (
    ModbusSequentialDataBlock,
    ModbusSlaveContext,
    ModbusServerContext,
)
from pymodbus.device import ModbusDeviceIdentification


class ChargerModbusSimulator:
    """充电桩Modbus TCP模拟器"""
    
    def __init__(self, host="0.0.0.0", port=502, unit_id=1):
        """初始化模拟器
        
        Args:
            host: 监听地址
            port: 监听端口
            unit_id: Modbus单元ID
        """
        self.host = host
        self.port = port
        self.unit_id = unit_id
        self.running = False
        self.server_thread = None
        
        # 充电桩状态
        self.status = "Available"  # Available, Charging, Fault
        self.power = 0.0  # 充电功率 (W)
        self.energy = 0.0  # 累计充电量 (kWh)
        self.voltage = 220.0  # 电压 (V)
        self.current = 0.0  # 电流 (A)
        self.temperature = 25.0  # 温度 (°C)
        self.session_time = 0  # 充电会话时间 (秒)
        self.charging_start_time = None
        
        # Modbus寄存器映射
        # 保持寄存器 (4x区域)
        # 地址 0-9: 基本信息
        # 地址 10-19: 电气参数
        # 地址 20-29: 状态控制
        
        self._init_datastore()
    
    def _init_datastore(self):
        """初始化Modbus数据存储"""
        # 输入寄存器 (3x区域) - 只读
        ir_block = ModbusSequentialDataBlock(0, [0] * 100)
        
        # 保持寄存器 (4x区域) - 读写
        hr_block = ModbusSequentialDataBlock(0, [0] * 100)
        
        # 线圈 (0x区域) - 读写位
        co_block = ModbusSequentialDataBlock(0, [False] * 100)
        
        # 离散输入 (1x区域) - 只读位
        di_block = ModbusSequentialDataBlock(0, [False] * 100)
        
        # 创建从站上下文
        self.store = ModbusSlaveContext(
            di=di_block,
            co=co_block,
            hr=hr_block,
            ir=ir_block,
        )
        
        # 创建服务器上下文
        self.context = ModbusServerContext(slaves=self.store, single=True)
        
        # 初始化保持寄存器数据
        self._update_registers()
    
    def _update_registers(self):
        """更新Modbus寄存器数据"""
        # 状态码: 0=Available, 1=Charging, 2=Fault
        status_code = {
            "Available": 0,
            "Charging": 1,
            "Fault": 2
        }.get(self.status, 0)
        
        # 保持寄存器映射
        registers = {
            0: int(self.voltage * 10),  # 电压 (x10)
            1: int(self.current * 10),  # 电流 (x10)
            2: int(self.power),  # 功率 (W)
            3: int(self.energy * 100),  # 能量 (x100 kWh)
            4: int(self.temperature * 10),  # 温度 (x10)
            5: status_code,  # 状态码
            6: self.session_time,  # 充电时间 (秒)
            10: 1,  # 设备类型: 1=充电桩
            11: 100,  # 额定功率 (100kW)
        }
        
        # 更新保持寄存器
        for addr, value in registers.items():
            self.store.setValues(3, addr, [value])
    
    def _simulation_loop(self):
        """模拟循环 - 在后台更新状态"""
        while self.running:
            try:
                self._update_state()
                self._update_registers()
                time.sleep(1)
            except Exception as e:
                print(f"模拟错误: {e}")
                time.sleep(1)
    
    def _update_state(self):
        """更新充电桩状态"""
        if self.status == "Charging":
            # 充电中，更新参数
            self.power = 7000 + (time.time() % 1000)  # 7-8kW波动
            self.current = self.power / self.voltage
            self.energy += self.power / 3600000  # Wh -> kWh
            self.temperature = 25 + (self.power / 1000)  # 温度随功率上升
            
            if self.charging_start_time:
                self.session_time = int(
                    (datetime.now() - self.charging_start_time).total_seconds()
                )
        
        elif self.status == "Available":
            # 空闲状态
            self.power = 0.0
            self.current = 0.0
            self.temperature = 25.0 + (time.time() % 5)  # 轻微波动
    
    def start_charging(self):
        """开始充电"""
        if self.status == "Available":
            self.status = "Charging"
            self.charging_start_time = datetime.now()
            self.session_time = 0
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 充电桩开始充电")
    
    def stop_charging(self):
        """停止充电"""
        if self.status == "Charging":
            self.status = "Available"
            self.charging_start_time = None
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 充电桩停止充电")
    
    def set_fault(self):
        """设置故障状态"""
        self.status = "Fault"
        self.power = 0.0
        self.current = 0.0
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 充电桩故障")
    
    def clear_fault(self):
        """清除故障"""
        if self.status == "Fault":
            self.status = "Available"
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 充电桩故障清除")
    
    def start(self):
        """启动模拟器"""
        print("=" * 60)
        print("Modbus/TCP 充电桩模拟器")
        print("=" * 60)
        print(f"监听地址: {self.host}:{self.port}")
        print(f"单元ID: {self.unit_id}")
        print("=" * 60)
        
        self.running = True
        
        # 启动模拟线程
        self.server_thread = threading.Thread(target=self._simulation_loop, daemon=True)
        self.server_thread.start()
        
        # 设备识别信息
        identity = ModbusDeviceIdentification()
        identity.VendorName = "EdgeFusion"
        identity.ProductCode = "CHARGER-001"
        identity.VendorUrl = "https://edgefusion.com"
        identity.ProductName = "智能充电桩模拟器"
        identity.ModelName = "Charger-Sim-v1"
        identity.MajorMinorRevision = "1.0"
        
        print("模拟器已启动！按 Ctrl+C 停止")
        print(f"当前状态: {self.status}")
        print("-" * 60)
        
        try:
            # 启动Modbus TCP服务器
            StartTcpServer(
                context=self.context,
                identity=identity,
                address=(self.host, self.port),
            )
        except KeyboardInterrupt:
            print("\n正在停止模拟器...")
            self.stop()
    
    def stop(self):
        """停止模拟器"""
        self.running = False
        if self.server_thread and self.server_thread.is_alive():
            self.server_thread.join(timeout=2)
        print("模拟器已停止")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Modbus/TCP 充电桩模拟器")
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="监听地址 (默认: 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=502,
        help="监听端口 (默认: 502)",
    )
    parser.add_argument(
        "--unit-id",
        type=int,
        default=1,
        help="Modbus单元ID (默认: 1)",
    )
    
    args = parser.parse_args()
    
    simulator = ChargerModbusSimulator(
        host=args.host,
        port=args.port,
        unit_id=args.unit_id,
    )
    
    try:
        simulator.start()
    except Exception as e:
        print(f"启动失败: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
