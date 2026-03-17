import os


def get_config_file(default: str = "config.yaml") -> str:
    return os.environ.get("EDGEFUSION_CONFIG_FILE", default)


def get_log_dir(default: str = "logs") -> str:
    return os.environ.get("EDGEFUSION_LOG_DIR", default)


def get_database_url(configured_url: str | None = None) -> str:
    env_url = os.environ.get("EDGEFUSION_DB_URL")
    if env_url:
        return env_url

    if configured_url:
        return configured_url

    return "sqlite:///edgefusion.db"
