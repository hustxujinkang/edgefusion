import importlib
from pathlib import Path


def test_config_uses_env_config_file(monkeypatch, tmp_path):
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        "monitor:\n  dashboard_port: 6100\n  collect_interval: 3\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("EDGEFUSION_CONFIG_FILE", str(config_file))

    from edgefusion.config import Config

    config = Config()

    assert Path(config.config_file) == config_file
    assert config.get("monitor.dashboard_port") == 6100
    assert config.get("monitor.collect_interval") == 3


def test_logger_uses_env_log_dir(monkeypatch, tmp_path):
    monkeypatch.setenv("EDGEFUSION_LOG_DIR", str(tmp_path))

    import edgefusion.logger as logger_module

    logger_module = importlib.reload(logger_module)

    app_logger = logger_module.get_logger("runtime-test")
    app_logger.info("write into configured log directory")

    assert Path(logger_module.logger.log_dir) == tmp_path
    assert list(tmp_path.glob("edgefusion_*.log"))


def test_database_uses_env_database_url(monkeypatch, tmp_path):
    db_path = tmp_path / "edgefusion.db"
    monkeypatch.setenv("EDGEFUSION_DB_URL", f"sqlite:///{db_path.as_posix()}")

    from edgefusion.monitor.database import Database

    database = Database()
    try:
        assert Path(database.engine.url.database) == db_path
    finally:
        database.engine.dispose()
