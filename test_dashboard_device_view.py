import werkzeug

from edgefusion.device_manager import DeviceManager
from edgefusion.charger_layout import build_connector_device_id
from edgefusion.monitor.dashboard import Dashboard
from edgefusion.strategy.mode_controller import ModeControllerStrategy


class DummyCollector:
    def __init__(self, latest_data=None, config=None):
        self.latest_data = latest_data or []
        self.config = config or DummyConfig()

    def get_data_summary(self):
        return {}

    def get_latest_data(self, device_id=None):
        if device_id:
            return [item for item in self.latest_data if item["device_id"] == device_id]
        return list(self.latest_data)


class DummyDatabase:
    def get_device_stats(self):
        return {}


class DummyConfig:
    def __init__(self, initial=None):
        self.values = dict(initial or {"control.use_simulated_devices": True})

    def get(self, key, default=None):
        return self.values.get(key, default)

    def set(self, key, value):
        self.values[key] = value


class DummyStrategy:
    def __init__(self):
        self.use_simulated_devices = True
        self.config = {}

    def get_status(self):
        return {"enabled": True}


def _snapshot(device_id, device_type, data, timestamp="2026-03-19T12:00:00"):
    return {
        "device_id": device_id,
        "device_type": device_type,
        "timestamp": timestamp,
        "data": data,
    }


class FakeModbusProtocol:
    def __init__(self, config):
        self.config = config
        self.connected = False

    def connect(self):
        self.connected = True
        return True

    def disconnect(self):
        self.connected = False
        return True


class RecordingDeviceManager(DeviceManager):
    def __init__(self):
        super().__init__({"modbus": {"host": "127.0.0.1", "port": 1502}})
        self.write_calls = []
        self.read_values = {}
        self.read_calls = []

    def write_device_data(self, device_id, register, value):
        self.write_calls.append((device_id, register, value))
        return True

    def read_device_data(self, device_id, register):
        self.read_calls.append((device_id, register))
        return self.read_values.get((device_id, register))


def build_dashboard(device_manager, collector=None):
    if not hasattr(werkzeug, "__version__"):
        werkzeug.__version__ = "3"
    dashboard = Dashboard(
        {"dashboard_host": "127.0.0.1", "dashboard_port": 5000},
        device_manager,
        collector or DummyCollector(),
        DummyDatabase(),
    )
    dashboard.register_strategy("dummy", DummyStrategy())
    return dashboard


def test_connected_devices_endpoint_uses_device_manager_inventory():
    device_manager = DeviceManager({"modbus": {"host": "127.0.0.1", "port": 1502}})
    device_info = {
        "device_id": "sim_charger_1",
        "type": "charger",
        "protocol": "modbus",
        "host": "127.0.0.1",
        "port": 1502,
        "unit_id": 1,
        "status": "online",
    }
    assert device_manager.register_device(device_info) is True

    dashboard = build_dashboard(device_manager)
    client = dashboard.app.test_client()

    response = client.get("/api/devices/connected")

    assert response.status_code == 200
    payload = response.get_json()
    assert len(payload) == 1
    assert payload[0] | {"capabilities": payload[0]["capabilities"]} == {**device_info, "source": "real", "capabilities": payload[0]["capabilities"]}
    assert "capabilities" in payload[0]


def test_dashboard_root_uses_mode_console_tabs():
    dashboard = build_dashboard(DeviceManager({}))
    client = dashboard.app.test_client()

    response = client.get("/")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "运行总览" in html
    assert "设备接入" in html
    assert "模式中心" in html
    assert "模式配置" in html
    assert "诊断" in html
    assert "控制策略" not in html
    assert "模式参数" in html
    assert "反送保护参数" not in html
    assert "采集状态" in html
    assert "采集周期" in html
    assert "最近采集" in html
    assert "下次采集" in html


def test_register_device_defaults_to_real_source_and_online_status():
    device_manager = DeviceManager({"modbus": {"host": "127.0.0.1", "port": 1502}})

    assert device_manager.register_device(
        {
            "device_id": "grid_meter_real",
            "type": "grid_meter",
            "protocol": "modbus",
        }
    ) is True

    payload = device_manager.get_device("grid_meter_real")
    assert payload["device_id"] == "grid_meter_real"
    assert payload["type"] == "grid_meter"
    assert payload["protocol"] == "modbus"
    assert payload["status"] == "online"
    assert payload["source"] == "real"
    assert "capabilities" in payload


def test_add_modbus_device_registers_into_device_manager(monkeypatch):
    monkeypatch.setattr("edgefusion.monitor.dashboard.ModbusProtocol", FakeModbusProtocol)
    device_manager = DeviceManager({"modbus": {"host": "127.0.0.1", "port": 1502}})
    dashboard = build_dashboard(device_manager)
    client = dashboard.app.test_client()

    response = client.post(
        "/api/devices/add-modbus",
        json={
            "device_id": "charger-a",
            "device_type": "charger",
            "model": "generic_charger",
            "host": "192.168.1.8",
            "port": 502,
            "unit_id": 3,
        },
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert device_manager.get_device("charger-a") is None
    candidate = device_manager.get_device_candidate("charger-a")
    assert candidate["device_id"] == "charger-a"
    assert candidate["type"] == "charger"
    assert candidate["model"] == "generic_charger"
    assert candidate["protocol"] == "modbus"
    assert candidate["host"] == "192.168.1.8"
    assert candidate["port"] == 502
    assert candidate["unit_id"] == 3
    assert candidate["status"] == "online"
    assert candidate["source"] == "real"
    assert "capabilities" in candidate

    activate_response = client.post("/api/devices/candidates/charger-a/activate")
    assert activate_response.status_code == 200
    assert activate_response.get_json()["success"] is True

    connected_response = client.get("/api/devices/connected")
    assert connected_response.get_json() == [device_manager.get_device("charger-a")]

    delete_response = client.delete("/api/devices/charger-a")
    assert delete_response.status_code == 200
    assert delete_response.get_json()["success"] is True
    assert device_manager.get_device("charger-a") is None


def test_activate_candidate_keeps_candidate_inventory_and_marks_connected():
    device_manager = DeviceManager({"modbus": {"host": "127.0.0.1", "port": 1502}})
    assert device_manager.register_device_candidate(
        {
            "device_id": "charger-candidate",
            "type": "charging_station",
            "protocol": "modbus",
            "host": "127.0.0.1",
            "port": 1502,
            "unit_id": 1,
        }
    ) is True

    dashboard = build_dashboard(device_manager)
    client = dashboard.app.test_client()

    activate_response = client.post("/api/devices/candidates/charger-candidate/activate")

    assert activate_response.status_code == 200
    assert activate_response.get_json()["success"] is True
    assert device_manager.get_device("charger-candidate") is not None
    assert device_manager.get_device_candidate("charger-candidate") is not None

    candidate_response = client.get("/api/devices/candidates")
    assert candidate_response.status_code == 200
    payload = candidate_response.get_json()
    assert len(payload) == 1
    candidate = payload[0]
    assert candidate["connector_count"] == 1
    assert candidate["device_id"] == "charger-candidate"
    assert candidate["type"] == "charging_station"
    assert candidate["protocol"] == "modbus"
    assert candidate["host"] == "127.0.0.1"
    assert candidate["port"] == 1502
    assert candidate["unit_id"] == 1
    assert candidate["status"] == "online"
    assert candidate["source"] == "real"
    assert candidate["connected"] is True
    assert "capabilities" in candidate
    assert len(candidate["connectors"]) == 1
    connector = candidate["connectors"][0]
    assert connector["connector_id"] == 1
    assert connector["device_id"] == "charger-candidate:1"
    assert connector["io_device_id"] == "charger-candidate"
    assert connector["pile_id"] == "charger-candidate"
    assert connector["protocol"] == "modbus"
    assert connector["status"] == "online"
    assert connector["type"] == "charging_connector"
    assert "capabilities" in connector


def test_collector_latest_endpoint_surfaces_connector_snapshots_from_pile_inventory():
    latest_data = [
        {
            "device_id": "charger_0:1",
            "device_type": "charging_connector",
            "pile_id": "charger_0",
            "connector_id": 1,
            "timestamp": "2026-03-19T15:00:00",
            "data": {"status": "Charging", "power": 1800, "max_power": 5000, "min_power": 1000},
        }
    ]
    dashboard = build_dashboard(DeviceManager({}), collector=DummyCollector(latest_data=latest_data))
    client = dashboard.app.test_client()

    response = client.get("/api/collector/latest")

    assert response.status_code == 200
    assert response.get_json() == latest_data


def test_device_control_action_routes_xj_start_charging_through_connector_semantics(monkeypatch):
    class _FailOnInitProtocol:
        def __init__(self, config):
            raise AssertionError("dashboard should not instantiate ModbusProtocol directly")

    monkeypatch.setattr("edgefusion.monitor.dashboard.ModbusProtocol", _FailOnInitProtocol)

    device_manager = RecordingDeviceManager()
    assert device_manager.register_device(
        {
            "device_id": "charger-xj",
            "type": "charging_station",
            "model": "xj_dc_120kw",
            "protocol": "modbus",
            "host": "127.0.0.1",
            "port": 1502,
            "unit_id": 7,
        }
    ) is True

    dashboard = build_dashboard(device_manager)
    client = dashboard.app.test_client()

    response = client.post(
        "/api/devices/charger-xj/control",
        json={"action": "start_charging", "gun_id": 2, "params": {"power_kw": 7.2}},
    )

    assert response.status_code == 200
    assert response.get_json()["success"] is True
    assert device_manager.write_calls == [
        (build_connector_device_id("charger-xj", 2), "power_limit", 7200),
    ]


def test_device_control_action_routes_generic_stop_to_semantic_command(monkeypatch):
    class _FailOnInitProtocol:
        def __init__(self, config):
            raise AssertionError("dashboard should not instantiate ModbusProtocol directly")

    monkeypatch.setattr("edgefusion.monitor.dashboard.ModbusProtocol", _FailOnInitProtocol)

    device_manager = RecordingDeviceManager()
    assert device_manager.register_device(
        {
            "device_id": "charger-generic",
            "type": "charging_station",
            "model": "generic_charger",
            "protocol": "modbus",
            "host": "127.0.0.1",
            "port": 1502,
            "unit_id": 3,
        }
    ) is True

    dashboard = build_dashboard(device_manager)
    client = dashboard.app.test_client()

    response = client.post(
        "/api/devices/charger-generic/control",
        json={"action": "stop_charging", "gun_id": 1},
    )

    assert response.status_code == 200
    assert response.get_json()["success"] is True
    assert device_manager.write_calls == [
        (build_connector_device_id("charger-generic", 1), "stop_charging", 1),
    ]


def test_device_control_action_rejects_set_soc_without_semantic_mapping(monkeypatch):
    class _FailOnInitProtocol:
        def __init__(self, config):
            raise AssertionError("dashboard should not instantiate ModbusProtocol directly")

    monkeypatch.setattr("edgefusion.monitor.dashboard.ModbusProtocol", _FailOnInitProtocol)

    device_manager = RecordingDeviceManager()
    assert device_manager.register_device(
        {
            "device_id": "charger-xj",
            "type": "charging_station",
            "model": "xj_dc_120kw",
            "protocol": "modbus",
            "host": "127.0.0.1",
            "port": 1502,
            "unit_id": 7,
        }
    ) is True

    dashboard = build_dashboard(device_manager)
    client = dashboard.app.test_client()

    response = client.post(
        "/api/devices/charger-xj/control",
        json={"action": "set_soc", "gun_id": 1, "params": {"target_soc": 80}},
    )

    assert response.status_code == 400
    assert response.get_json()["success"] is False
    assert "不支持" in response.get_json()["message"]
    assert device_manager.write_calls == []


def test_gun_data_endpoint_reads_connector_semantics_without_direct_modbus(monkeypatch):
    class _FailOnInitProtocol:
        def __init__(self, config):
            raise AssertionError("dashboard should not instantiate ModbusProtocol directly")

    monkeypatch.setattr("edgefusion.monitor.dashboard.ModbusProtocol", _FailOnInitProtocol)

    device_manager = RecordingDeviceManager()
    assert device_manager.register_device(
        {
            "device_id": "charger-xj",
            "type": "charging_station",
            "model": "xj_dc_120kw",
            "protocol": "modbus",
            "host": "127.0.0.1",
            "port": 1502,
            "unit_id": 7,
        }
    ) is True
    connector_device_id = build_connector_device_id("charger-xj", 2)
    device_manager.read_values[(connector_device_id, "state")] = 3
    device_manager.read_values[(connector_device_id, "power")] = 7200
    device_manager.read_values[(connector_device_id, "energy")] = 12.5

    dashboard = build_dashboard(device_manager)
    client = dashboard.app.test_client()

    response = client.get("/api/devices/charger-xj/gun-data?gun_id=2")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["data"]["gun_id"] == 2
    assert payload["data"]["model"] == "xj_dc_120kw"
    assert payload["data"]["state"]["value"] == 3
    assert payload["data"]["power"]["value"] == 7200
    assert payload["data"]["energy"]["value"] == 12.5
    assert (connector_device_id, "state") in device_manager.read_calls
    assert (connector_device_id, "power") in device_manager.read_calls


def test_disconnect_active_device_keeps_candidate_available_for_reconnect():
    device_manager = DeviceManager({"modbus": {"host": "127.0.0.1", "port": 1502}})
    assert device_manager.register_device_candidate(
        {
            "device_id": "charger-disconnect",
            "type": "charging_station",
            "protocol": "modbus",
            "host": "127.0.0.1",
            "port": 1502,
            "unit_id": 2,
        }
    ) is True
    assert device_manager.activate_device("charger-disconnect") is True

    dashboard = build_dashboard(device_manager)
    client = dashboard.app.test_client()

    disconnect_response = client.delete("/api/devices/charger-disconnect")

    assert disconnect_response.status_code == 200
    assert disconnect_response.get_json()["success"] is True
    assert disconnect_response.get_json()["message"] == "设备已断开"
    assert device_manager.get_device("charger-disconnect") is None
    assert device_manager.get_device_candidate("charger-disconnect") is not None

    candidate_response = client.get("/api/devices/candidates")
    assert candidate_response.status_code == 200
    assert candidate_response.get_json()[0]["connected"] is False


def test_connected_candidate_cannot_be_deleted_from_candidate_inventory():
    device_manager = DeviceManager({"modbus": {"host": "127.0.0.1", "port": 1502}})
    assert device_manager.register_device_candidate(
        {
            "device_id": "charger-protected",
            "type": "charging_station",
            "protocol": "modbus",
            "host": "127.0.0.1",
            "port": 1502,
            "unit_id": 3,
        }
    ) is True
    assert device_manager.activate_device("charger-protected") is True

    dashboard = build_dashboard(device_manager)
    client = dashboard.app.test_client()

    delete_response = client.delete("/api/devices/candidates/charger-protected")

    assert delete_response.status_code == 409
    assert delete_response.get_json()["success"] is False
    assert delete_response.get_json()["message"] == "设备已接入，请先断开"
    assert device_manager.get_device("charger-protected") is not None
    assert device_manager.get_device_candidate("charger-protected") is not None


def test_add_modbus_device_bootstraps_registry_when_protocol_is_missing(monkeypatch):
    monkeypatch.setattr("edgefusion.monitor.dashboard.ModbusProtocol", FakeModbusProtocol)
    device_manager = DeviceManager({})
    dashboard = build_dashboard(device_manager)
    client = dashboard.app.test_client()

    response = client.post(
        "/api/devices/add-modbus",
        json={
            "device_id": "charger-b",
            "device_type": "charger",
            "model": "generic_charger",
            "host": "10.0.0.2",
            "port": 2502,
            "unit_id": 6,
        },
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert "modbus" in device_manager.protocols
    assert device_manager.get_device("charger-b") is None
    assert device_manager.get_device_candidate("charger-b")["host"] == "10.0.0.2"


def test_simulation_scenario_endpoints_switch_live_devices():
    device_manager = DeviceManager(
        {
            "simulation": {
                "scenario": "sunny_midday",
                "tick_seconds": 0.1,
            }
        }
    )
    device_manager.start()

    try:
        dashboard = build_dashboard(device_manager)
        client = dashboard.app.test_client()

        list_response = client.get("/api/simulation/scenarios")
        assert list_response.status_code == 200
        assert list_response.get_json()["current"] == "sunny_midday"
        assert device_manager.get_devices() == []
        simulation_candidates = [
            device for device in device_manager.get_device_candidates()
            if device.get("protocol") == "simulation"
        ]
        assert simulation_candidates
        assert all(device["source"] == "simulated" for device in simulation_candidates)

        switch_response = client.post("/api/simulation/scenario", json={"scenario": "charger_rush"})
        assert switch_response.status_code == 200
        payload = switch_response.get_json()
        assert payload["success"] is True
        assert payload["current"] == "charger_rush"

        simulation_devices = [device for device in device_manager.get_devices() if device.get("protocol") == "simulation"]
        simulation_candidates = [device for device in device_manager.get_device_candidates() if device.get("protocol") == "simulation"]
        device_ids = {device["device_id"] for device in simulation_candidates}
        assert simulation_devices == []
        assert "charger_2" in device_ids
        assert simulation_candidates
        assert all(device["source"] == "simulated" for device in simulation_candidates)
        assert all(device["status"] == "online" for device in simulation_candidates)
    finally:
        device_manager.stop()


def test_control_settings_endpoint_updates_mode_controller_toggle():
    device_manager = DeviceManager({})
    collector = DummyCollector(config=DummyConfig({"control.use_simulated_devices": True}))
    dashboard = build_dashboard(device_manager, collector=collector)
    strategy = DummyStrategy()
    dashboard.register_strategy("mode_controller", strategy)
    client = dashboard.app.test_client()

    response = client.get("/api/control/settings")
    assert response.status_code == 200
    assert response.get_json()["use_simulated_devices"] is True

    update_response = client.post("/api/control/settings", json={"use_simulated_devices": False})
    assert update_response.status_code == 200
    assert update_response.get_json()["use_simulated_devices"] is False
    assert collector.config.get("control.use_simulated_devices") is False
    assert strategy.use_simulated_devices is False


def test_modes_summary_endpoint_reports_mode_context():
    collector = DummyCollector(
        latest_data=[
            _snapshot("grid_meter_real", "grid_meter", {"power": -9000, "status": "online"}),
            _snapshot(
                "storage_real",
                "energy_storage",
                {"status": "online", "power": 0, "soc": 35, "max_charge_power": 2500},
            ),
        ],
        config=DummyConfig({"control.use_simulated_devices": True}),
    )
    device_manager = DeviceManager({"modbus": {"host": "127.0.0.1", "port": 1502}})
    assert device_manager.register_device(
        {"device_id": "grid_meter_real", "type": "grid_meter", "protocol": "modbus"}
    )
    assert device_manager.register_device(
        {"device_id": "storage_real", "type": "energy_storage", "protocol": "modbus"}
    )

    dashboard = build_dashboard(device_manager, collector=collector)
    strategy = ModeControllerStrategy(
        {
            "use_simulated_devices": True,
            "state": {"max_data_age_seconds": 30},
            "mode": {"export_limit_w": 5000, "export_enter_ratio": 1.0, "storage_soc_soft_limit": 95},
        },
        device_manager,
        collector,
    )
    strategy.start()
    dashboard.register_strategy("mode_controller", strategy)
    client = dashboard.app.test_client()

    response = client.get("/api/modes/summary")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["current_mode"] == "export_protect"
    assert payload["current_reason"] == "export_limit_exceeded"
    assert payload["control_state"] == "closed_loop"
    assert payload["counts"]["active_devices"] == 2
    assert payload["counts"]["participating_devices"] == 2
    assert payload["counts"]["candidate_devices"] == 0
    assert payload["key_measurements"]["grid_power_w"] == -9000.0
    assert payload["blockers"] == []
    assert any(mode["name"] == "export_protect" and mode["available"] is True for mode in payload["supported_modes"])


def test_modes_summary_reports_candidate_only_state_when_no_active_devices():
    collector = DummyCollector(config=DummyConfig({"control.use_simulated_devices": True}))
    device_manager = DeviceManager({"modbus": {"host": "127.0.0.1", "port": 1502}})
    assert device_manager.register_device_candidate(
        {"device_id": "grid_meter_sim", "type": "grid_meter", "protocol": "modbus", "source": "simulated"}
    )
    assert device_manager.register_device_candidate(
        {"device_id": "pv_sim", "type": "pv", "protocol": "modbus", "source": "simulated"}
    )

    dashboard = build_dashboard(device_manager, collector=collector)
    strategy = ModeControllerStrategy(
        {
            "use_simulated_devices": True,
            "state": {"max_data_age_seconds": 30},
            "mode": {"export_limit_w": 5000, "export_enter_ratio": 1.0, "storage_soc_soft_limit": 95},
        },
        device_manager,
        collector,
    )
    dashboard.register_strategy("mode_controller", strategy)
    client = dashboard.app.test_client()

    response = client.get("/api/modes/summary")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["counts"]["active_devices"] == 0
    assert payload["counts"]["candidate_devices"] == 2
    assert "no_active_devices" in payload["blockers"]


def test_modes_config_endpoint_updates_export_protect_parameters():
    collector = DummyCollector(config=DummyConfig({"control.use_simulated_devices": True}))
    device_manager = DeviceManager({})
    dashboard = build_dashboard(device_manager, collector=collector)
    strategy = ModeControllerStrategy(
        {
            "use_simulated_devices": True,
            "state": {"max_data_age_seconds": 30},
            "mode": {
                "export_protect_enabled": True,
                "export_limit_w": 5000,
                "export_enter_ratio": 1.0,
                "storage_soc_soft_limit": 95,
            },
        },
        device_manager,
        collector,
    )
    dashboard.register_strategy("mode_controller", strategy)
    client = dashboard.app.test_client()

    get_response = client.get("/api/modes/config")

    assert get_response.status_code == 200
    initial = get_response.get_json()
    assert initial["use_simulated_devices"] is True
    assert initial["state"]["max_data_age_seconds"] == 30
    assert initial["modes"]["export_protect"]["enabled"] is True
    assert initial["modes"]["export_protect"]["settings"]["export_limit_w"] == 5000

    update_response = client.post(
        "/api/modes/config",
        json={
            "use_simulated_devices": False,
            "state": {"max_data_age_seconds": 45},
            "modes": {
                "export_protect": {
                    "enabled": False,
                    "settings": {
                        "export_limit_w": 4200,
                        "export_enter_ratio": 0.85,
                        "storage_soc_soft_limit": 88,
                    },
                }
            },
        },
    )

    assert update_response.status_code == 200
    updated = update_response.get_json()
    assert updated["success"] is True
    assert updated["use_simulated_devices"] is False
    assert updated["state"]["max_data_age_seconds"] == 45
    assert updated["modes"]["export_protect"]["enabled"] is False
    assert updated["modes"]["export_protect"]["settings"]["export_limit_w"] == 4200
    assert updated["modes"]["export_protect"]["settings"]["export_enter_ratio"] == 0.85
    assert updated["modes"]["export_protect"]["settings"]["storage_soc_soft_limit"] == 88
    assert collector.config.get("control.use_simulated_devices") is False
    assert strategy.use_simulated_devices is False


def test_modes_config_endpoint_exposes_dynamic_mode_metadata_and_updates_runtime_controls():
    collector = DummyCollector(config=DummyConfig({"control.use_simulated_devices": True}))
    device_manager = DeviceManager({})
    dashboard = build_dashboard(device_manager, collector=collector)
    strategy = ModeControllerStrategy(
        {
            "use_simulated_devices": True,
            "state": {"max_data_age_seconds": 30, "manual_override": False},
            "mode": {
                "export_protect_enabled": True,
                "export_limit_w": 5000,
                "export_enter_ratio": 1.0,
                "storage_soc_soft_limit": 95,
            },
        },
        device_manager,
        collector,
    )
    strategy.start()
    dashboard.register_strategy("mode_controller", strategy)
    client = dashboard.app.test_client()

    get_response = client.get("/api/modes/config")

    assert get_response.status_code == 200
    payload = get_response.get_json()
    assert payload["modes"]["manual_override"]["configurable"] is True
    assert payload["modes"]["manual_override"]["settings"]["active"] is False
    assert payload["modes"]["manual_override"]["fields"][0]["key"] == "active"
    assert payload["modes"]["safe_hold"]["configurable"] is True
    assert payload["modes"]["safe_hold"]["settings"]["max_data_age_seconds"] == 30
    assert payload["modes"]["safe_hold"]["fields"][0]["key"] == "max_data_age_seconds"
    assert payload["modes"]["business_normal"]["configurable"] is False
    assert payload["modes"]["export_protect"]["toggleable"] is True

    update_response = client.post(
        "/api/modes/config",
        json={
            "modes": {
                "manual_override": {"settings": {"active": True}},
                "safe_hold": {"settings": {"max_data_age_seconds": 75}},
                "export_protect": {
                    "enabled": False,
                    "settings": {
                        "export_limit_w": 4100,
                        "export_enter_ratio": 0.8,
                        "storage_soc_soft_limit": 87,
                    },
                },
            }
        },
    )

    assert update_response.status_code == 200
    updated = update_response.get_json()
    assert updated["modes"]["manual_override"]["settings"]["active"] is True
    assert updated["modes"]["safe_hold"]["settings"]["max_data_age_seconds"] == 75
    assert updated["modes"]["export_protect"]["enabled"] is False
    assert strategy.state_config["manual_override"] is True
    assert strategy.state_config["max_data_age_seconds"] == 75
    assert strategy.mode_config["export_protect_enabled"] is False

    summary_response = client.get("/api/modes/summary")
    assert summary_response.status_code == 200
    assert summary_response.get_json()["current_mode"] == "manual_override"


def test_collector_latest_endpoint_returns_live_snapshots():
    latest_data = [
        {
            "device_id": "grid_meter_0",
            "device_type": "grid_meter",
            "timestamp": "2026-03-18T16:00:00",
            "data": {"power": -2500},
        }
    ]
    dashboard = build_dashboard(DeviceManager({}), collector=DummyCollector(latest_data=latest_data))
    client = dashboard.app.test_client()

    response = client.get("/api/collector/latest")

    assert response.status_code == 200
    assert response.get_json() == latest_data
