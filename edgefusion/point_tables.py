# 设备型号点表配置
# 定义不同型号设备的Modbus寄存器映射

POINT_TABLES = {
    # 通用充电桩（现有模拟器用的简单寄存器）
    'generic_charger': {
        'name': '通用充电桩',
        'manufacturer': 'Generic',
        'registers': {
            'voltage': {'addr': 0, 'type': 'u16', 'scale': 0.1, 'unit': 'V'},
            'current': {'addr': 1, 'type': 'u16', 'scale': 0.01, 'unit': 'A'},
            'power': {'addr': 2, 'type': 'u16', 'scale': 1, 'unit': 'W'},
            'energy': {'addr': 3, 'type': 'u16', 'scale': 0.01, 'unit': 'kWh'},
            'temperature': {'addr': 4, 'type': 'u16', 'scale': 0.1, 'unit': '°C'},
            'status': {'addr': 5, 'type': 'u16', 'scale': 1, 'unit': ''},
        }
    },
    
    # 许继 120kW 直流充电桩
    'xj_dc_120kw': {
        'name': '许继 120kW 直流充电桩',
        'manufacturer': '许继',
        'max_power': 120,  # kW
        'max_guns': 2,
        'registers': {
            # 整桩信息 (基地址 0x1000)
            'pile': {
                'gun_count': {'addr': 0x1000, 'type': 'u16', 'scale': 1, 'unit': '个'},
                'max_power': {'addr': 0x1001, 'type': 'u16', 'scale': 1, 'unit': 'kW'},
            },
            # 枪1信息 (基地址 0x2000)
            'gun1': {
                'state': {'addr': 0x2000, 'type': 'u16', 'scale': 1, 'unit': ''},
                'mode': {'addr': 0x2001, 'type': 'u16', 'scale': 1, 'unit': ''},
                'alarm': {'addr': 0x2002, 'type': 'u32', 'scale': 1, 'unit': ''},
                'fault': {'addr': 0x2004, 'type': 'u32', 'scale': 1, 'unit': ''},
                'meter_reading': {'addr': 0x2006, 'type': 'u32', 'scale': 0.001, 'unit': 'kWh'},
                'amount': {'addr': 0x2008, 'type': 'u32', 'scale': 0.01, 'unit': '元'},
                'energy': {'addr': 0x200A, 'type': 'u32', 'scale': 0.001, 'unit': 'kWh'},
                'duration': {'addr': 0x200C, 'type': 'u32', 'scale': 1, 'unit': '秒'},
                'power': {'addr': 0x200E, 'type': 'u32', 'scale': 0.001, 'unit': 'kW'},
                'voltage': {'addr': 0x2010, 'type': 'u16', 'scale': 0.1, 'unit': 'V'},
                'current': {'addr': 0x2011, 'type': 'u16', 'scale': 0.01, 'unit': 'A'},
                'soc': {'addr': 0x2012, 'type': 'u16', 'scale': 1, 'unit': '%'},
                'temperature': {'addr': 0x2013, 'type': 'u16', 'scale': 1, 'unit': '°C'},
            },
            # 枪2信息 (基地址 0x2100, 偏移 0x100)
            'gun2': {
                'state': {'addr': 0x2100, 'type': 'u16', 'scale': 1, 'unit': ''},
                'mode': {'addr': 0x2101, 'type': 'u16', 'scale': 1, 'unit': ''},
                'alarm': {'addr': 0x2102, 'type': 'u32', 'scale': 1, 'unit': ''},
                'fault': {'addr': 0x2104, 'type': 'u32', 'scale': 1, 'unit': ''},
                'meter_reading': {'addr': 0x2106, 'type': 'u32', 'scale': 0.001, 'unit': 'kWh'},
                'amount': {'addr': 0x2108, 'type': 'u32', 'scale': 0.01, 'unit': '元'},
                'energy': {'addr': 0x210A, 'type': 'u32', 'scale': 0.001, 'unit': 'kWh'},
                'duration': {'addr': 0x210C, 'type': 'u32', 'scale': 1, 'unit': '秒'},
                'power': {'addr': 0x210E, 'type': 'u32', 'scale': 0.001, 'unit': 'kW'},
                'voltage': {'addr': 0x2110, 'type': 'u16', 'scale': 0.1, 'unit': 'V'},
                'current': {'addr': 0x2111, 'type': 'u16', 'scale': 0.01, 'unit': 'A'},
                'soc': {'addr': 0x2112, 'type': 'u16', 'scale': 1, 'unit': '%'},
                'temperature': {'addr': 0x2113, 'type': 'u16', 'scale': 1, 'unit': '°C'},
            }
        },
        # 控制寄存器
        'control': {
            'power_absolute': {'addr': 0x4000, 'cmd': 'write_registers'},
            'power_percentage': {'addr': 0x4000, 'cmd': 'write_registers'},
        }
    },
    
    # 许继 240kW 直流充电桩（点表结构与120kW相同）
    'xj_dc_240kw': {
        'name': '许继 240kW 直流充电桩',
        'manufacturer': '许继',
        'max_power': 240,
        'max_guns': 2,
        'registers': {
            'pile': {
                'gun_count': {'addr': 0x1000, 'type': 'u16', 'scale': 1, 'unit': '个'},
                'max_power': {'addr': 0x1001, 'type': 'u16', 'scale': 1, 'unit': 'kW'},
            },
            'gun1': {
                'state': {'addr': 0x2000, 'type': 'u16', 'scale': 1, 'unit': ''},
                'mode': {'addr': 0x2001, 'type': 'u16', 'scale': 1, 'unit': ''},
                'voltage': {'addr': 0x2010, 'type': 'u16', 'scale': 0.1, 'unit': 'V'},
                'current': {'addr': 0x2011, 'type': 'u16', 'scale': 0.01, 'unit': 'A'},
                'power': {'addr': 0x200E, 'type': 'u32', 'scale': 0.001, 'unit': 'kW'},
                'soc': {'addr': 0x2012, 'type': 'u16', 'scale': 1, 'unit': '%'},
                'temperature': {'addr': 0x2013, 'type': 'u16', 'scale': 1, 'unit': '°C'},
            },
            'gun2': {
                'state': {'addr': 0x2100, 'type': 'u16', 'scale': 1, 'unit': ''},
                'mode': {'addr': 0x2101, 'type': 'u16', 'scale': 1, 'unit': ''},
                'voltage': {'addr': 0x2110, 'type': 'u16', 'scale': 0.1, 'unit': 'V'},
                'current': {'addr': 0x2111, 'type': 'u16', 'scale': 0.01, 'unit': 'A'},
                'power': {'addr': 0x210E, 'type': 'u32', 'scale': 0.001, 'unit': 'kW'},
                'soc': {'addr': 0x2112, 'type': 'u16', 'scale': 1, 'unit': '%'},
                'temperature': {'addr': 0x2113, 'type': 'u16', 'scale': 1, 'unit': '°C'},
            }
        },
        'control': {
            'power_absolute': {'addr': 0x4000, 'cmd': 'write_registers'},
        }
    }
}


def get_point_table(model: str) -> dict:
    """获取指定型号的点表配置"""
    return POINT_TABLES.get(model, POINT_TABLES['generic_charger'])


def get_gun_registers(model: str, gun_id: int = 1) -> dict:
    """获取指定枪的寄存器配置"""
    table = get_point_table(model)
    registers = table.get('registers', {})
    gun_key = f'gun{gun_id}'
    return registers.get(gun_key, {})
