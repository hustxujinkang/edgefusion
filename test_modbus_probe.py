import json

import modbus_probe


class FakeProbeProtocol:
    def __init__(self, config):
        self.config = config
        self.read_calls = []
        self.write_calls = []
        self.connected = False

    def connect(self):
        self.connected = True
        return True

    def disconnect(self):
        self.connected = False
        return True

    def read_data(self, device_id, register):
        self.read_calls.append((device_id, register))
        return 61

    def write_data(self, device_id, register, value):
        self.write_calls.append((device_id, register, value))
        return True


def test_modbus_probe_uses_model_probe_register_when_register_is_omitted(monkeypatch, capsys):
    protocol = FakeProbeProtocol({})
    monkeypatch.setattr(modbus_probe, "create_modbus_protocol", lambda config: protocol)
    monkeypatch.setattr(
        modbus_probe,
        "get_modbus_model_probe_register",
        lambda **kwargs: {"addr": 52001, "type": "u16", "scale": 1, "unit": "%"},
        raising=False,
    )

    exit_code = modbus_probe.main(
        [
            "--host",
            "192.168.1.18",
            "--unit-id",
            "7",
            "--device-type",
            "energy_storage",
            "--vendor",
            "generic",
            "--model",
            "generic_storage",
        ]
    )

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["success"] is True
    assert payload["register"] == {"addr": 52001, "type": "u16", "scale": 1, "unit": "%"}
    assert protocol.read_calls == [("7", {"addr": 52001, "type": "u16", "scale": 1, "unit": "%"})]


def test_modbus_probe_prefers_explicit_register_over_model_default(monkeypatch, capsys):
    protocol = FakeProbeProtocol({})
    monkeypatch.setattr(modbus_probe, "create_modbus_protocol", lambda config: protocol)
    monkeypatch.setattr(
        modbus_probe,
        "get_modbus_model_probe_register",
        lambda **kwargs: {"addr": 52001, "type": "u16", "scale": 1, "unit": "%"},
        raising=False,
    )

    exit_code = modbus_probe.main(
        [
            "--host",
            "192.168.1.18",
            "--unit-id",
            "7",
            "--device-type",
            "energy_storage",
            "--vendor",
            "generic",
            "--model",
            "generic_storage",
            "--register",
            "53001",
            "--type",
            "i16",
        ]
    )

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["success"] is True
    assert payload["register"] == {"addr": 53001, "type": "i16"}
    assert protocol.read_calls == [("7", {"addr": 53001, "type": "i16"})]
