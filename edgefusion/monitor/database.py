# 数据库模块
from typing import Dict, Any, List
from datetime import datetime
from sqlalchemy import create_engine, Column, String, Float, Text, DateTime, JSON
from sqlalchemy.orm import declarative_base, sessionmaker
from ..logger import get_logger
from ..runtime_paths import get_database_url

Base = declarative_base()


class DeviceData(Base):
    """设备数据表"""
    __tablename__ = 'device_data'
    
    id = Column(String, primary_key=True)
    device_id = Column(String, index=True)
    device_type = Column(String, index=True)
    timestamp = Column(DateTime, index=True)
    data = Column(JSON)
    created_at = Column(DateTime, default=datetime.now)


class Database:
    """数据库管理类"""
    
    def __init__(self, db_url: str | None = None):
        """初始化数据库
        
        Args:
            db_url: 数据库连接URL
        """
        self.db_url = get_database_url(db_url)
        self.engine = create_engine(self.db_url, echo=False)
        self.Session = sessionmaker(bind=self.engine)
        self.logger = get_logger('Database')
        self._create_tables()
    
    def _create_tables(self):
        """创建数据库表"""
        Base.metadata.create_all(self.engine)
    
    def insert_data(self, data: Dict[str, Any]) -> bool:
        """插入设备数据
        
        Args:
            data: 设备数据
            
        Returns:
            bool: 插入是否成功
        """
        try:
            session = self.Session()
            
            # 生成唯一ID
            data_id = f"{data['device_id']}_{data['timestamp']}"
            
            # 创建数据记录
            device_data = DeviceData(
                id=data_id,
                device_id=data['device_id'],
                device_type=data.get('device_type', 'unknown'),
                timestamp=datetime.fromisoformat(data['timestamp']),
                data=data['data']
            )
            
            # 插入数据
            session.add(device_data)
            session.commit()
            session.close()
            return True
        except Exception as e:
            self.logger.error("插入数据失败: %s", e)
            return False
    
    def get_data_by_device(self, device_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """根据设备ID获取数据
        
        Args:
            device_id: 设备ID
            limit: 数据条数限制
            
        Returns:
            List[Dict[str, Any]]: 设备数据列表
        """
        try:
            session = self.Session()
            
            # 查询数据
            data_records = session.query(DeviceData).filter(
                DeviceData.device_id == device_id
            ).order_by(
                DeviceData.timestamp.desc()
            ).limit(limit).all()
            
            # 转换数据格式
            result = []
            for record in data_records:
                result.append({
                    'device_id': record.device_id,
                    'device_type': record.device_type,
                    'timestamp': record.timestamp.isoformat(),
                    'data': record.data
                })
            
            session.close()
            return result
        except Exception as e:
            self.logger.error("获取设备数据失败: %s", e)
            return []
    
    def get_data_by_time_range(self, start_time: datetime, end_time: datetime, device_id: str = None) -> List[Dict[str, Any]]:
        """根据时间范围获取数据
        
        Args:
            start_time: 开始时间
            end_time: 结束时间
            device_id: 设备ID，None表示所有设备
            
        Returns:
            List[Dict[str, Any]]: 数据列表
        """
        try:
            session = self.Session()
            
            # 构建查询
            query = session.query(DeviceData).filter(
                DeviceData.timestamp >= start_time,
                DeviceData.timestamp <= end_time
            )
            
            # 如果指定了设备ID
            if device_id:
                query = query.filter(DeviceData.device_id == device_id)
            
            # 执行查询
            data_records = query.order_by(DeviceData.timestamp.desc()).all()
            
            # 转换数据格式
            result = []
            for record in data_records:
                result.append({
                    'device_id': record.device_id,
                    'device_type': record.device_type,
                    'timestamp': record.timestamp.isoformat(),
                    'data': record.data
                })
            
            session.close()
            return result
        except Exception as e:
            self.logger.error("获取时间范围数据失败: %s", e)
            return []
    
    def get_latest_data(self, device_id: str = None) -> List[Dict[str, Any]]:
        """获取最新数据
        
        Args:
            device_id: 设备ID，None表示所有设备
            
        Returns:
            List[Dict[str, Any]]: 最新数据列表
        """
        try:
            session = self.Session()
            
            # 构建查询
            if device_id:
                # 获取指定设备的最新数据
                data_record = session.query(DeviceData).filter(
                    DeviceData.device_id == device_id
                ).order_by(
                    DeviceData.timestamp.desc()
                ).first()
                
                if data_record:
                    result = [{
                        'device_id': data_record.device_id,
                        'device_type': data_record.device_type,
                        'timestamp': data_record.timestamp.isoformat(),
                        'data': data_record.data
                    }]
                else:
                    result = []
            else:
                # 获取所有设备的最新数据
                # 这里简化处理，实际应使用更高效的查询
                device_ids = session.query(DeviceData.device_id).distinct().all()
                result = []
                
                for (device_id,) in device_ids:
                    latest_record = session.query(DeviceData).filter(
                        DeviceData.device_id == device_id
                    ).order_by(
                        DeviceData.timestamp.desc()
                    ).first()
                    
                    if latest_record:
                        result.append({
                            'device_id': latest_record.device_id,
                            'device_type': latest_record.device_type,
                            'timestamp': latest_record.timestamp.isoformat(),
                            'data': latest_record.data
                        })
            
            session.close()
            return result
        except Exception as e:
            self.logger.error("获取最新数据失败: %s", e)
            return []
    
    def get_device_stats(self) -> Dict[str, Any]:
        """获取设备统计信息
        
        Returns:
            Dict[str, Any]: 设备统计信息，格式为 {device_id: data_count}
        """
        try:
            session = self.Session()
            
            # 按设备统计数据条数
            from sqlalchemy import func
            stats = session.query(
                DeviceData.device_id,
                func.count(DeviceData.id).label('count')
            ).group_by(DeviceData.device_id).all()
            
            result = {}
            for device_id, count in stats:
                result[device_id] = count
            
            session.close()
            return result
        except Exception as e:
            self.logger.error("获取设备统计信息失败: %s", e)
            return {}
    
    def delete_old_data(self, days: int = 7):
        """删除旧数据
        
        Args:
            days: 保留天数
        """
        try:
            session = self.Session()
            
            # 计算删除时间点
            delete_before = datetime.now() - timedelta(days=days)
            
            # 删除旧数据
            deleted_count = session.query(DeviceData).filter(
                DeviceData.timestamp < delete_before
            ).delete()
            
            session.commit()
            session.close()
            
            self.logger.info("删除了%s条旧数据", deleted_count)
        except Exception as e:
            self.logger.error("删除旧数据失败: %s", e)


# 导入timedelta
from datetime import timedelta
