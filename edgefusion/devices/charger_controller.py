# 充电桩控制器
# 封装不同型号的控制逻辑

from typing import Dict, Any, Optional
from ..protocol import ModbusProtocol
from ..point_tables import POINT_TABLES


class ChargerController:
    """充电桩控制器 - 支持多种型号"""
    
    def __init__(self, device_info: Dict[str, Any], protocol: ModbusProtocol):
        """
        Args:
            device_info: 设备信息
            protocol: Modbus协议实例（已连接）
        """
        self.device_info = device_info
        self.protocol = protocol
        self.model = device_info.get('model', 'generic_charger')
        self.unit_id = device_info.get('unit_id', 1)
        self.pt = POINT_TABLES.get(self.model, {})
    
    def _write_register(self, addr: int, value: int) -> bool:
        """写单个寄存器"""
        try:
            return self.protocol.write_data(str(self.unit_id), str(addr), value)
        except Exception as e:
            print(f"写寄存器失败 addr={addr}: {e}")
            return False
    
    def _write_control(self, gun_id: int, ctrl_type: int, param: int) -> bool:
        """写控制寄存器（许继协议格式）
        
        Args:
            gun_id: 枪号
            ctrl_type: 0x01=百分比, 0x02=绝对值
            param: 参数值（功率为0.001kW单位）
        """
        try:
            # 许继控制协议：写12个寄存器到 0x4000
            # 格式: [枪号, 控制类型, 参数低, 参数高, 0,0,0,0,0,0,0,0]
            values = [
                gun_id,      # 0: 枪号
                ctrl_type,   # 1: 控制类型
                param & 0xFFFF,        # 2: 参数低16位
                (param >> 16) & 0xFFFF, # 3: 参数高16位
                0, 0, 0, 0, 0, 0, 0, 0  # 4-11: 预留
            ]
            
            # 使用协议写多个寄存器
            if hasattr(self.protocol, '_write_registers'):
                return self.protocol._write_registers(0x4000, values, self.unit_id)
            else:
                # 不支持批量写，用单个寄存器模拟（简化）
                self.protocol.write_data(str(self.unit_id), str(0x4000), gun_id)
                self.protocol.write_data(str(self.unit_id), str(0x4001), ctrl_type)
                self.protocol.write_data(str(self.unit_id), str(0x4002), param & 0xFFFF)
                self.protocol.write_data(str(self.unit_id), str(0x4003), (param >> 16) & 0xFFFF)
                return True
        except Exception as e:
            print(f"写控制寄存器失败: {e}")
            return False
    
    def start_charging(self, gun_id: int = 1, power_kw: float = 120) -> bool:
        """开始充电（带功率限制）
        
        Args:
            gun_id: 枪号（从1开始）
            power_kw: 功率限制（kW）
            
        Returns:
            bool: 是否成功
        """
        if self.model.startswith('xj_'):
            # 许继型号：写控制寄存器 0x4000
            # 控制类型0x02=绝对值，参数=功率*1000（0.001kW单位）
            param = int(power_kw * 1000)
            return self._write_control(gun_id, 0x02, param)
        else:
            # 通用型号：写状态寄存器
            return self._write_register(5, 1)  # 地址5=状态
    
    def stop_charging(self, gun_id: int = 1) -> bool:
        """停止充电（功率设为0）"""
        if self.model.startswith('xj_'):
            # 许继：功率设为0表示停止
            return self._write_control(gun_id, 0x02, 0)
        else:
            return self._write_register(5, 0)
    
    def emergency_stop(self, gun_id: int = 1) -> bool:
        """急停"""
        if self.model.startswith('xj_'):
            # 许继：功率设为0，模拟器会识别为故障
            return self._write_control(gun_id, 0x02, 0xFFFFFFFF)  # 特殊值表示急停
        else:
            return self._write_register(5, 2)
    
    def set_power_limit(self, gun_id: int, power_kw: float) -> bool:
        """设置功率限制（运行时调整）"""
        if self.model.startswith('xj_'):
            # 许继：通过控制命令调整功率
            param = int(power_kw * 1000)
            return self._write_control(gun_id, 0x02, param)
        else:
            print(f"通用型号不支持功率控制")
            return False
    
    def clear_fault(self, gun_id: int = 1) -> bool:
        """清除故障（通过开始充电后停止）"""
        if self.model.startswith('xj_'):
            # 许继：模拟器会在功率设为0时清除故障
            return self._write_control(gun_id, 0x02, 0)
        else:
            return self._write_register(5, 0)
