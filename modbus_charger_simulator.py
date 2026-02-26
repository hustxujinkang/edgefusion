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
    """充电桩Modbus TCP模拟器 - 支持多型号"""
    
    def __init__(self, host="0.0.0.0", port=502, unit_id=1, model="generic"):
        """初始化模拟器
        
        Args:
            host: 监听地址
            port: 监听端口
            unit_id: Modbus单元ID
            model: 型号标识，如 "generic" 或 "xj_dc_120kw"
        """
        self.host = host
        self.port = port
        self.unit_id = unit_id
        self.model = model
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
        
        # 根据型号初始化寄存器
        self._init_datastore()
    
    def _init_datastore(self):
        """初始化Modbus数据存储 - 根据型号分配地址空间"""
        # 根据型号决定地址空间大小
        if self.model.startswith('xj_'):
            # 许继型号：需要支持到 0x2100+（约 8500 个地址）
            ir_size = 0x3000  # 输入寄存器
            hr_size = 0x3000  # 保持寄存器
        else:
            # 通用型号：小地址空间
            ir_size = 100
            hr_size = 100
        
        # 输入寄存器 (3x区域) - 只读
        ir_block = ModbusSequentialDataBlock(0, [0] * ir_size)
        
        # 保持寄存器 (4x区域) - 读写
        hr_block = ModbusSequentialDataBlock(0, [0] * hr_size)
        
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
        
        # 初始化寄存器数据（按型号）
        self._update_registers()
    
    def _sync_from_registers(self):
        """从寄存器同步状态到内部变量 - 检测外部写入"""
        try:
            # 读取寄存器当前值
            reg0 = self.store.getValues(3, 0, 1)[0]  # 电压
            reg1 = self.store.getValues(3, 1, 1)[0]  # 电流
            reg2 = self.store.getValues(3, 2, 1)[0]  # 功率
            reg3 = self.store.getValues(3, 3, 1)[0]  # 能量
            reg4 = self.store.getValues(3, 4, 1)[0]  # 温度
            reg5 = self.store.getValues(3, 5, 1)[0]  # 状态
            
            # 比较并同步
            expected_voltage = int(self.voltage * 10)
            expected_current = int(self.current * 10)
            expected_power = int(self.power)
            expected_energy = int(self.energy * 100)
            expected_temp = int(self.temperature * 10)
            
            status_code = {
                "Available": 0,
                "Charging": 1,
                "Fault": 2
            }.get(self.status, 0)
            
            # 如果寄存器值与预期不同，说明被外部写入了
            if reg0 != expected_voltage:
                self.voltage = reg0 / 10.0
                print(f"[同步] 外部写入电压: {self.voltage}V")
            
            if reg1 != expected_current:
                self.current = reg1 / 10.0
                print(f"[同步] 外部写入电流: {self.current}A")
            
            if reg2 != expected_power:
                self.power = reg2
                print(f"[同步] 外部写入功率: {self.power}W")
            
            if reg3 != expected_energy:
                self.energy = reg3 / 100.0
                print(f"[同步] 外部写入能量: {self.energy}kWh")
            
            if reg4 != expected_temp:
                self.temperature = reg4 / 10.0
                print(f"[同步] 外部写入温度: {self.temperature}°C")
            
            if reg5 != status_code:
                new_status = {
                    0: "Available",
                    1: "Charging",
                    2: "Fault"
                }.get(reg5, self.status)
                if new_status != self.status:
                    self.status = new_status
                    if self.status == "Charging" and not self.charging_start_time:
                        self.charging_start_time = datetime.now()
                    elif self.status == "Available":
                        self.charging_start_time = None
                    print(f"[同步] 外部写入状态: {self.status}")
        
        except Exception as e:
            print(f"[同步] 错误: {e}")
    
    def _update_registers(self):
        """更新Modbus寄存器数据"""
        # 先同步外部写入的寄存器值到内部变量
        self._sync_from_registers()
        
        # 状态码: 0=Available, 1=Charging, 2=Fault
        status_code = {
            "Available": 0,
            "Charging": 1,
            "Fault": 2
        }.get(self.status, 0)
        
        if self.model.startswith('xj_'):
            # 许继型号寄存器布局
            self._update_xj_registers(status_code)
        else:
            # 通用型号寄存器布局
            self._update_generic_registers(status_code)
    
    def _update_generic_registers(self, status_code):
        """通用型号寄存器更新（地址 0-20）"""
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
        for addr, value in registers.items():
            self.store.setValues(3, addr, [value])
    
    def _update_xj_registers(self, status_code):
        """许继型号寄存器更新（地址 0x1000, 0x2000, 0x2100）"""
        # 整桩信息 (0x1000)
        self.store.setValues(3, 0x1000, [2])       # 枪个数
        self.store.setValues(3, 0x1001, [120])     # 最大功率 120kW
        
        # 枪1信息 (0x2000)
        gun1_base = 0x2000
        self.store.setValues(3, gun1_base + 0, [status_code])  # 状态
        self.store.setValues(3, gun1_base + 1, [0])           # 模式: 充电
        self.store.setValues(3, gun1_base + 2, [0, 0])        # 告警 (u32)
        self.store.setValues(3, gun1_base + 4, [0, 0])        # 故障 (u32)
        self.store.setValues(3, gun1_base + 16, [int(self.voltage * 10)])  # 电压
        self.store.setValues(3, gun1_base + 17, [int(self.current * 100)])  # 电流 (x100)
        # 功率 (u32, 0.001kW单位)
        power_raw = int(self.power * 0.001)  # W -> 0.001kW
        self.store.setValues(3, gun1_base + 14, [power_raw & 0xFFFF, (power_raw >> 16) & 0xFFFF])
        self.store.setValues(3, gun1_base + 18, [85])         # SOC 85%
        self.store.setValues(3, gun1_base + 19, [int(self.temperature)])  # 温度
        
        # 枪2信息 (0x2100) - 默认空闲
        gun2_base = 0x2100
        self.store.setValues(3, gun2_base + 0, [0])  # 状态: 空闲
        self.store.setValues(3, gun2_base + 1, [0])  # 模式
        self.store.setValues(3, gun2_base + 16, [2200])  # 电压 220V
        self.store.setValues(3, gun2_base + 17, [0])     # 电流 0A
        self.store.setValues(3, gun2_base + 18, [0])     # SOC 0%
    
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
        print(f"型号: {self.model}")
        print(f"监听地址: {self.host}:{self.port}")
        print(f"单元ID: {self.unit_id}")
        if self.model.startswith('xj_'):
            print("寄存器布局: 许继协议 (0x1000/0x2000/0x2100)")
        else:
            print("寄存器布局: 通用协议 (地址 0-20)")
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
    parser.add_argument(
        "--model",
        default="generic",
        help="充电桩型号: generic(通用), xj_dc_120kw(许继120kW) (默认: generic)",
    )
    
    args = parser.parse_args()
    
    simulator = ChargerModbusSimulator(
        host=args.host,
        port=args.port,
        unit_id=args.unit_id,
        model=args.model,
    )
    
    try:
        simulator.start()
    except Exception as e:
        print(f"启动失败: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
