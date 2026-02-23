#!/usr/bin/env python3
# 测试数据库连接
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from edgefusion.monitor import Database

def test_database_connection():
    """测试数据库连接"""
    print("=== 测试数据库连接 ===")
    try:
        # 测试内存数据库
        db = Database('sqlite:///:memory:')
        print("内存数据库连接成功")
        
        # 测试文件数据库
        db_file = Database('sqlite:///test.db')
        print("文件数据库连接成功")
        
        # 测试数据插入
        test_data = {
            'device_id': 'test_device',
            'device_type': 'test_type',
            'timestamp': '2026-02-23T12:00:00',
            'data': {'power': 1000, 'status': 'ok'}
        }
        result = db_file.insert_data(test_data)
        print(f"数据插入结果: {result}")
        
        # 测试数据查询
        data_list = db_file.get_data_by_device('test_device')
        print(f"查询到的数据数量: {len(data_list)}")
        
        print("数据库测试通过！")
        return True
    except Exception as e:
        print(f"数据库测试失败: {e}")
        return False

if __name__ == '__main__':
    test_database_connection()
