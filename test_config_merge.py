from pathlib import Path

import yaml

from edgefusion.config import Config


def test_config_merges_missing_defaults_into_existing_file(tmp_path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        yaml.safe_dump(
            {
                "device_manager": {
                    "modbus": {"host": "localhost", "port": 502, "timeout": 5}
                },
                "monitor": {"collect_interval": 5},
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )

    config = Config(str(config_path))
    merged_content = yaml.safe_load(config_path.read_text(encoding="utf-8"))

    assert config.get("monitor.collect_interval") == 5
    assert config.get("control.mode_controller.mode.export_limit_w") == 5000
    assert config.get("simulation.enabled") is False
    assert "control" in merged_content
    assert "simulation" in merged_content
