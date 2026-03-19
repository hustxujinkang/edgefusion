from edgefusion.config import Config
from edgefusion.device_manager import DeviceManager
from edgefusion.monitor.collector import DataCollector


def test_collector_get_latest_data_returns_latest_entry_per_device():
    collector = DataCollector(Config(), DeviceManager({}), None)
    collector.data_buffer = [
        {
            "device_id": "pv_0",
            "device_type": "pv",
            "timestamp": "2026-03-18T16:00:00",
            "data": {"power": 5000},
        },
        {
            "device_id": "pv_0",
            "device_type": "pv",
            "timestamp": "2026-03-18T16:00:05",
            "data": {"power": 4200},
        },
        {
            "device_id": "grid_meter_0",
            "device_type": "grid_meter",
            "timestamp": "2026-03-18T16:00:03",
            "data": {"power": -1800},
        },
    ]

    latest = collector.get_latest_data()

    assert latest == [
        {
            "device_id": "pv_0",
            "device_type": "pv",
            "timestamp": "2026-03-18T16:00:05",
            "data": {"power": 4200},
        },
        {
            "device_id": "grid_meter_0",
            "device_type": "grid_meter",
            "timestamp": "2026-03-18T16:00:03",
            "data": {"power": -1800},
        },
    ]
