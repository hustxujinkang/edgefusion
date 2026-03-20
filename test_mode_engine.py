from datetime import datetime, timedelta

from edgefusion.control.mode_engine import arbitrate_mode
from edgefusion.control.export_protect import plan_export_protect
from edgefusion.control.site_state import build_site_state
from edgefusion.strategy.mode_controller import ModeControllerStrategy


def _snapshot(device_id, device_type, data, timestamp=None):
    return {
        "device_id": device_id,
        "device_type": device_type,
        "timestamp": (timestamp or datetime.now()).isoformat(),
        "data": data,
    }


class _FakeCollector:
    def __init__(self, snapshots):
        self._snapshots = snapshots

    def get_latest_data(self, device_id=None):
        if device_id is None:
            return list(self._snapshots)
        return [snapshot for snapshot in self._snapshots if snapshot["device_id"] == device_id]


class _FakeDeviceManager:
    def __init__(self, devices=None):
        self.writes = []
        self.devices = devices or {}

    def write_device_data(self, device_id, register, value):
        self.writes.append((device_id, register, value))
        return True

    def get_device(self, device_id):
        return self.devices.get(device_id)

    def get_devices(self):
        return list(self.devices.values())


def test_build_site_state_marks_missing_grid_power_as_untrusted():
    state = build_site_state(
        [
            _snapshot(
                "pv-1",
                "pv",
                {"power": 5000, "status": "online"},
            )
        ],
        {"max_data_age_seconds": 30},
    )

    assert state.trusted is False
    assert "missing_grid_power" in state.trust_issues


def test_arbitrate_prefers_export_protect_when_export_limit_is_exceeded():
    state = build_site_state(
        [
            _snapshot(
                "grid-meter-1",
                "grid_meter",
                {"power": -6200, "status": "online"},
            )
        ],
        {"max_data_age_seconds": 30},
    )

    decision = arbitrate_mode(
        state,
        {
            "export_limit_w": 5000,
            "export_enter_ratio": 1.0,
        },
    )

    assert decision.mode == "export_protect"
    assert decision.reason == "export_limit_exceeded"


def test_arbitrate_skips_export_protect_when_mode_is_disabled():
    state = build_site_state(
        [
            _snapshot(
                "grid-meter-1",
                "grid_meter",
                {"power": -6200, "status": "online"},
            )
        ],
        {"max_data_age_seconds": 30},
    )

    decision = arbitrate_mode(
        state,
        {
            "export_protect_enabled": False,
            "export_limit_w": 5000,
            "export_enter_ratio": 1.0,
        },
    )

    assert decision.mode == "business_normal"
    assert decision.reason == "export_protect_disabled"


def test_export_protect_allocates_storage_then_active_chargers_then_pv_curtailment():
    state = build_site_state(
        [
            _snapshot("grid-meter-1", "grid_meter", {"power": -12000, "status": "online"}),
            _snapshot(
                "storage-1",
                "energy_storage",
                {
                    "status": "online",
                    "mode": "idle",
                    "power": 0,
                    "soc": 45,
                    "max_charge_power": 3000,
                },
            ),
            _snapshot(
                "charger-1:1",
                "charging_connector",
                {
                    "status": "Charging",
                    "power": 3000,
                    "max_power": 4500,
                    "min_power": 1000,
                },
            ),
            _snapshot(
                "charger-2:1",
                "charging_connector",
                {
                    "status": "Charging",
                    "power": 2000,
                    "max_power": 3000,
                    "min_power": 1000,
                },
            ),
            _snapshot(
                "pv-1",
                "pv",
                {
                    "status": "online",
                    "power": 8000,
                    "power_limit": 8000,
                    "min_power_limit": 0,
                },
            ),
        ],
        {"max_data_age_seconds": 30},
    )

    plan = plan_export_protect(state, {"export_limit_w": 5000})

    assert plan.remaining_gap_w == 0
    assert [(action.device_id, action.action) for action in plan.actions] == [
        ("storage-1", "set_charge_power"),
        ("charger-1:1", "set_power_limit"),
        ("charger-2:1", "set_power_limit"),
        ("pv-1", "set_power_limit"),
    ]
    assert plan.actions[0].value_w == 3000
    assert plan.actions[1].delta_w == 1500
    assert plan.actions[2].delta_w == 1000
    assert plan.actions[3].delta_w == -1500


def test_export_protect_splits_charger_headroom_evenly_with_caps():
    state = build_site_state(
        [
            _snapshot("grid-meter-1", "grid_meter", {"power": -8500, "status": "online"}),
            _snapshot(
                "charger-1:1",
                "charging_connector",
                {
                    "status": "Charging",
                    "power": 2000,
                    "max_power": 3000,
                    "min_power": 1000,
                },
            ),
            _snapshot(
                "charger-2:1",
                "charging_connector",
                {
                    "status": "Charging",
                    "power": 1000,
                    "max_power": 5000,
                    "min_power": 1000,
                },
            ),
        ],
        {"max_data_age_seconds": 30},
    )

    plan = plan_export_protect(state, {"export_limit_w": 5000})
    charger_actions = {action.device_id: action for action in plan.actions}

    assert charger_actions["charger-1:1"].delta_w == 1000
    assert charger_actions["charger-2:1"].delta_w == 2500


def test_export_protect_can_use_active_charger_with_numeric_status_code():
    state = build_site_state(
        [
            _snapshot("grid-meter-1", "grid_meter", {"power": -7000, "status": "online"}),
            _snapshot(
                "charger-1:1",
                "charging_connector",
                {
                    "status": 3,
                    "power": 2000,
                    "max_power": 3500,
                    "min_power": 1000,
                },
            ),
        ],
        {"max_data_age_seconds": 30},
    )

    plan = plan_export_protect(state, {"export_limit_w": 5000})

    assert [(action.device_id, action.action, action.value_w) for action in plan.actions] == [
        ("charger-1:1", "set_power_limit", 3500),
    ]


def test_export_protect_skips_devices_without_declared_write_capability():
    state = build_site_state(
        [
            _snapshot("grid-meter-1", "grid_meter", {"power": -9000, "status": "online"}),
            _snapshot(
                "storage-1",
                "energy_storage",
                {
                    "status": "online",
                    "mode": "idle",
                    "power": 0,
                    "soc": 40,
                    "max_charge_power": 3000,
                },
            )
            | {"capabilities": {"readable_fields": ["soc", "power", "mode", "max_charge_power"], "writable_fields": []}},
            _snapshot(
                "charger-1:1",
                "charging_connector",
                {"status": "charging", "power": 2000, "max_power": 3500, "min_power": 1000},
            )
            | {"capabilities": {"readable_fields": ["status", "power", "max_power"], "writable_fields": []}},
            _snapshot(
                "pv-1",
                "pv",
                {"status": "online", "power": 8000, "power_limit": 8000, "min_power_limit": 0},
            )
            | {"capabilities": {"readable_fields": ["power", "power_limit"], "writable_fields": []}},
        ],
        {"max_data_age_seconds": 30},
    )

    plan = plan_export_protect(state, {"export_limit_w": 5000})

    assert plan.actions == []
    assert plan.remaining_gap_w == 4000


def test_mode_controller_uses_collector_snapshots_and_executes_export_actions():
    collector = _FakeCollector(
        [
            _snapshot("grid-meter-1", "grid_meter", {"power": -9000, "status": "online"}),
            _snapshot(
                "storage-1",
                "energy_storage",
                {"status": "online", "power": 0, "soc": 40, "max_charge_power": 2500},
            ),
            _snapshot(
                "charger-1:1",
                "charging_connector",
                {"status": "Charging", "power": 2000, "max_power": 3500, "min_power": 1000},
            ),
        ]
    )
    device_manager = _FakeDeviceManager()
    controller = ModeControllerStrategy(
        {
            "state": {"max_data_age_seconds": 30},
            "mode": {"export_limit_w": 5000, "export_enter_ratio": 1.0},
        },
        device_manager,
        collector,
    )

    controller.start()
    result = controller.execute()

    assert result["mode"] == "export_protect"
    assert result["status"] == "executed"
    assert device_manager.writes == [
        ("storage-1", "mode", "charge"),
        ("storage-1", "charge_power", 2500),
        ("charger-1:1", "power_limit", 3500),
    ]


def test_mode_controller_enters_safe_hold_when_required_state_is_missing():
    collector = _FakeCollector(
        [
            _snapshot("pv-1", "pv", {"power": 5000, "status": "online"}),
        ]
    )
    device_manager = _FakeDeviceManager()
    controller = ModeControllerStrategy(
        {
            "state": {"max_data_age_seconds": 30},
            "mode": {"export_limit_w": 5000, "export_enter_ratio": 1.0},
        },
        device_manager,
        collector,
    )

    controller.start()
    result = controller.execute()

    assert result["mode"] == "safe_hold"
    assert result["reason"] == "untrusted_site_state"
    assert result["actions"] == []
    assert device_manager.writes == []


def test_mode_controller_ignores_simulated_snapshots_when_disabled():
    collector = _FakeCollector(
        [
            _snapshot("grid_meter_0", "grid_meter", {"power": -9000, "status": "online"}),
            _snapshot(
                "storage_0",
                "energy_storage",
                {"status": "online", "power": 0, "soc": 40, "max_charge_power": 2500},
            ),
        ]
    )
    device_manager = _FakeDeviceManager(
        {
            "grid_meter_0": {"device_id": "grid_meter_0", "source": "simulated", "status": "online"},
            "storage_0": {"device_id": "storage_0", "source": "simulated", "status": "online"},
        }
    )
    controller = ModeControllerStrategy(
        {
            "use_simulated_devices": False,
            "state": {"max_data_age_seconds": 30},
            "mode": {"export_limit_w": 5000, "export_enter_ratio": 1.0},
        },
        device_manager,
        collector,
    )

    controller.start()
    result = controller.execute()

    assert result["mode"] == "safe_hold"
    assert result["reason"] == "untrusted_site_state"
    assert device_manager.writes == []


def test_mode_controller_stays_monitor_only_without_real_control_path():
    collector = _FakeCollector(
        [
            _snapshot("grid_meter_real", "grid_meter", {"power": -9000, "status": "online"}),
            _snapshot(
                "charger_sim",
                "charging_connector",
                {"status": "Charging", "power": 2000, "max_power": 3500, "min_power": 1000},
            ),
        ]
    )
    device_manager = _FakeDeviceManager(
        {
            "grid_meter_real": {"device_id": "grid_meter_real", "source": "real", "status": "online"},
            "charger_sim": {"device_id": "charger_sim", "source": "simulated", "status": "online"},
        }
    )
    controller = ModeControllerStrategy(
        {
            "use_simulated_devices": False,
            "state": {"max_data_age_seconds": 30},
            "mode": {"export_limit_w": 5000, "export_enter_ratio": 1.0},
        },
        device_manager,
        collector,
    )

    controller.start()
    result = controller.execute()

    assert result["mode"] == "business_normal"
    assert result["reason"] == "no_export_control_capability"
    assert result["actions"] == []
    assert device_manager.writes == []


def test_mode_controller_stays_monitor_only_when_device_capabilities_disallow_control():
    collector = _FakeCollector(
        [
            _snapshot("grid-meter-1", "grid_meter", {"power": -9000, "status": "online"}),
            {
                **_snapshot(
                    "storage-1",
                    "energy_storage",
                    {"status": "online", "power": 0, "soc": 40, "max_charge_power": 2500},
                ),
                "capabilities": {"readable_fields": ["soc", "power", "max_charge_power"], "writable_fields": []},
            },
        ]
    )
    device_manager = _FakeDeviceManager(
        {
            "grid-meter-1": {"device_id": "grid-meter-1", "source": "real", "status": "online"},
            "storage-1": {
                "device_id": "storage-1",
                "type": "energy_storage",
                "source": "real",
                "status": "online",
                "capabilities": {"readable_fields": ["soc", "power", "max_charge_power"], "writable_fields": []},
            },
        }
    )
    controller = ModeControllerStrategy(
        {
            "state": {"max_data_age_seconds": 30},
            "mode": {"export_limit_w": 5000, "export_enter_ratio": 1.0},
        },
        device_manager,
        collector,
    )

    controller.start()
    result = controller.execute()

    assert result["mode"] == "business_normal"
    assert result["reason"] == "no_export_control_capability"
    assert device_manager.writes == []


def test_mode_controller_includes_connector_metadata_in_participating_devices():
    collector = _FakeCollector(
        [
            _snapshot("grid-meter-1", "grid_meter", {"power": -6500, "status": "online"}),
            {
                "device_id": "charger-pile-1:1",
                "device_type": "charging_connector",
                "pile_id": "charger-pile-1",
                "connector_id": 1,
                "timestamp": datetime.now().isoformat(),
                "data": {"status": "Charging", "power": 1200, "max_power": 3000, "min_power": 1000},
            },
        ]
    )
    device_manager = _FakeDeviceManager(
        {
            "grid-meter-1": {"device_id": "grid-meter-1", "source": "real", "status": "online"},
            "charger-pile-1:1": {
                "device_id": "charger-pile-1:1",
                "type": "charging_connector",
                "pile_id": "charger-pile-1",
                "connector_id": 1,
                "source": "real",
                "status": "online",
            },
        }
    )
    controller = ModeControllerStrategy(
        {
            "use_simulated_devices": True,
            "state": {"max_data_age_seconds": 30},
            "mode": {"export_limit_w": 5000, "export_enter_ratio": 1.0},
        },
        device_manager,
        collector,
    )

    controller.start()
    summary = controller.get_mode_summary()

    connector_entry = next(item for item in summary["participating_devices"] if item["device_id"] == "charger-pile-1:1")
    assert connector_entry["device_type"] == "charging_connector"
    assert connector_entry["source"] == "real"
