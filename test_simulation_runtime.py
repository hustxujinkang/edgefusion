#!/usr/bin/env python3
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from edgefusion.config import Config
from edgefusion.device_manager import DeviceManager
from edgefusion.monitor.collector import DataCollector
from edgefusion.protocol.simulation import SimulationProtocol
from edgefusion.simulator.site import SiteSimulator
from edgefusion.strategy.mode_controller import ModeControllerStrategy


def _simulation_config():
    return {
        "tick_seconds": 0.1,
        "scenario": "sunny_midday",
        "base_load_w": 2000,
        "pv": {"count": 1, "available_power_w": 7000, "power_limit_w": 7000},
        "storage": {
            "count": 1,
            "soc": 50,
            "max_charge_power_w": 1000,
            "initial_mode": "charge",
            "initial_charge_power_w": 1000,
        },
        "chargers": {
            "count": 1,
            "session_active": True,
            "power_w": 3000,
            "max_power_w": 5000,
            "min_power_w": 1000,
        },
    }


def test_site_simulator_derives_grid_power_from_device_balance():
    simulator = SiteSimulator(_simulation_config())
    simulator.step()

    snapshots = simulator.get_snapshots()
    grid_snapshot = next(item for item in snapshots if item["device_type"] == "grid_meter")

    assert grid_snapshot["data"]["power"] == -1000


def test_simulation_protocol_discovers_virtual_devices_and_reads_values():
    protocol = SimulationProtocol(_simulation_config())

    try:
        assert protocol.connect() is True
        devices = protocol.discover_devices()

        assert "grid_meter_0" in devices
        assert devices["grid_meter_0"]["type"] == "grid_meter"
        assert devices["grid_meter_0"]["source"] == "simulated"
        assert devices["grid_meter_0"]["status"] == "online"
        assert protocol.read_data("grid_meter_0", "power") == -1000
    finally:
        protocol.disconnect()


def test_device_manager_keeps_simulation_devices_available_for_reconnect_after_activation():
    device_manager = DeviceManager({"simulation": {"scenario": "sunny_midday", "tick_seconds": 0.1}})

    try:
        device_manager.start()
        assert device_manager.get_devices() == []

        candidates = device_manager.get_device_candidates()
        candidate_ids = {device["device_id"] for device in candidates}
        assert {"grid_meter_0", "pv_0", "storage_0", "charger_0", "charger_1"} <= candidate_ids
        charger_pile = device_manager.get_device_candidate("charger_0")
        assert charger_pile["type"] == "charging_station"
        assert charger_pile["connector_count"] == 1

        assert device_manager.activate_device("grid_meter_0") is True
        active_ids = {device["device_id"] for device in device_manager.get_devices()}
        remaining_candidate_ids = {device["device_id"] for device in device_manager.get_device_candidates()}
        assert "grid_meter_0" in active_ids
        assert "grid_meter_0" in remaining_candidate_ids
    finally:
        device_manager.stop()


def test_simulation_protocol_lists_and_switches_scenarios():
    protocol = SimulationProtocol({"scenario": "sunny_midday", "tick_seconds": 0.1})

    try:
        assert protocol.connect() is True
        assert protocol.get_current_scenario() == "sunny_midday"
        assert protocol.list_scenarios() == ["charger_rush", "cloud_pass", "low_soc", "sunny_midday"]

        before_devices = protocol.discover_devices()
        assert "charger_2" not in before_devices

        assert protocol.switch_scenario("charger_rush") is True
        after_devices = protocol.discover_devices()

        assert protocol.get_current_scenario() == "charger_rush"
        assert "charger_2" in after_devices
        assert protocol.read_data("grid_meter_0", "power") > 0
    finally:
        protocol.disconnect()


def test_data_collector_captures_grid_meter_and_control_capability_fields_from_simulation():
    config = Config()
    device_config = dict(config.get("device_manager", {}))
    device_config["simulation"] = _simulation_config()
    device_manager = DeviceManager(device_config)

    try:
        device_manager.start()
        for device in list(device_manager.get_device_candidates()):
            assert device_manager.activate_device(device["device_id"]) is True
        collector = DataCollector(config, device_manager, None)
        collected = collector.collect_data()
    finally:
        device_manager.stop()

    by_type = {item["device_type"]: item for item in collected}
    connector_snapshot = next(item for item in collected if item["device_type"] == "charging_connector")

    assert by_type["grid_meter"]["data"]["power"] == -1000
    assert by_type["pv"]["data"]["power_limit"] == 7000
    assert by_type["energy_storage"]["data"]["max_charge_power"] == 1000
    assert "power_limit" in by_type["pv"]["capabilities"]["writable_fields"]
    assert "charge_power" in by_type["energy_storage"]["capabilities"]["writable_fields"]
    assert connector_snapshot["device_id"] == "charger_0:1"
    assert connector_snapshot["pile_id"] == "charger_0"
    assert connector_snapshot["connector_id"] == 1
    assert "power_limit" in connector_snapshot["capabilities"]["writable_fields"]
    assert connector_snapshot["data"]["max_power"] == 5000
    assert connector_snapshot["data"]["min_power"] == 1000


def test_mode_controller_reduces_export_against_live_simulation():
    config = Config()
    device_config = dict(config.get("device_manager", {}))
    simulation_config = _simulation_config()
    simulation_config["base_load_w"] = 0
    simulation_config["storage"]["initial_mode"] = "auto"
    simulation_config["storage"]["initial_charge_power_w"] = 1000
    simulation_config["chargers"]["power_w"] = 1000
    device_config["simulation"] = simulation_config
    device_manager = DeviceManager(device_config)

    try:
        device_manager.start()
        for device in list(device_manager.get_device_candidates()):
            assert device_manager.activate_device(device["device_id"]) is True
        collector = DataCollector(config, device_manager, None)
        before = collector.collect_data()
        before_grid = next(item for item in before if item["device_type"] == "grid_meter")["data"]["power"]

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
        after = collector.collect_data()
        after_grid = next(item for item in after if item["device_type"] == "grid_meter")["data"]["power"]
    finally:
        device_manager.stop()

    assert before_grid == -6000
    assert result["mode"] == "export_protect"
    assert after_grid == -5000


def test_sunny_midday_scenario_applies_export_friendly_defaults():
    simulator = SiteSimulator({"scenario": "sunny_midday"})

    grid_power = simulator.grid_meter.get_data("power")

    assert len(simulator.pvs) == 1
    assert len(simulator.storages) == 1
    assert len(simulator.chargers) == 2
    assert simulator.pvs[0].get_data("available_power") > simulator.base_load.get_data("power")
    assert grid_power < 0


def test_cloud_pass_scenario_cycles_pv_available_power():
    simulator = SiteSimulator({"scenario": "cloud_pass"})

    available_powers = []
    for _ in range(6):
        simulator.step()
        available_powers.append(simulator.pvs[0].get_data("available_power"))

    assert min(available_powers) < max(available_powers)
    assert len(set(available_powers)) >= 3


def test_low_soc_scenario_starts_storage_constrained():
    simulator = SiteSimulator({"scenario": "low_soc"})
    storage = simulator.storages[0]

    assert storage.get_data("soc") <= 10
    assert storage.get_data("status") == "low_soc"
    assert storage.get_data("max_charge_power") <= 800
    assert storage.get_data("max_discharge_power") <= 800


def test_charger_rush_scenario_creates_heavy_import_load():
    simulator = SiteSimulator({"scenario": "charger_rush"})

    charging_chargers = [charger for charger in simulator.chargers if charger.get_data("status") == "Charging"]

    assert len(simulator.chargers) >= 3
    assert len(charging_chargers) == len(simulator.chargers)
    assert simulator.base_load.get_data("power") >= 4000
    assert simulator.grid_meter.get_data("power") > 0
