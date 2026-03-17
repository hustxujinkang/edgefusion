#!/usr/bin/env python3
import importlib
import warnings

from edgefusion.monitor import Database
import edgefusion.monitor.database as database_module


def test_database_connection(tmp_path):
    memory_db = Database("sqlite:///:memory:")
    file_db_path = tmp_path / "test.db"
    file_db = Database(f"sqlite:///{file_db_path.as_posix()}")

    test_data = {
        "device_id": "test_device",
        "device_type": "test_type",
        "timestamp": "2026-02-23T12:00:00",
        "data": {"power": 1000, "status": "ok"},
    }

    try:
        assert memory_db.get_device_stats() == {}
        assert file_db.insert_data(test_data) is True

        data_list = file_db.get_data_by_device("test_device")

        assert len(data_list) == 1
        assert data_list[0]["device_id"] == "test_device"
        assert data_list[0]["data"]["power"] == 1000
    finally:
        memory_db.engine.dispose()
        file_db.engine.dispose()


def test_database_module_reload_has_no_sqlalchemy_deprecation_warning():
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        importlib.reload(database_module)

    assert not [
        warning
        for warning in caught
        if "declarative_base" in str(warning.message)
    ]
