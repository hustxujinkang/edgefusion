import threading
import time
from datetime import datetime
from typing import Any

from .base_load_simulator import BaseLoadSimulator
from .charger_simulator import ChargerSimulator
from .grid_meter_simulator import GridMeterSimulator
from .pv_simulator import PVSimulator
from .scenarios import apply_scenario_step, resolve_site_config
from .storage_simulator import StorageSimulator


class SiteSimulator:
    """In-process site simulator that keeps virtual devices and grid balance consistent."""

    def __init__(self, config: dict[str, Any] | None = None):
        self.config = resolve_site_config(config)
        self.tick_seconds = float(self.config.get("tick_seconds", 1.0))
        self.running = False
        self.thread = None
        self.devices: dict[str, Any] = {}
        self.step_count = 0
        self._init_devices()
        self.step()

    def _init_devices(self):
        base_load_w = float(self.config.get("base_load_w", 2000))
        self.base_load = BaseLoadSimulator("base_load_0", power_w=base_load_w)
        self.grid_meter = GridMeterSimulator("grid_meter_0")

        pv_config = self.config.get("pv", {})
        self.pvs = []
        for index in range(int(pv_config.get("count", 1))):
            device_id = f"pv_{index}"
            pv = PVSimulator(
                device_id,
                available_power_w=float(pv_config.get("available_power_w", 7000)),
                power_limit_w=float(pv_config.get("power_limit_w", pv_config.get("available_power_w", 7000))),
                min_power_limit_w=float(pv_config.get("min_power_limit_w", 0)),
                enable_time_profile=False,
            )
            self.pvs.append(pv)

        storage_config = self.config.get("storage", {})
        self.storages = []
        for index in range(int(storage_config.get("count", 1))):
            device_id = f"storage_{index}"
            storage = StorageSimulator(
                device_id,
                soc=float(storage_config.get("soc", 50)),
                max_charge_power_w=float(storage_config.get("max_charge_power_w", 3000)),
                max_discharge_power_w=float(storage_config.get("max_discharge_power_w", 3000)),
                initial_mode=storage_config.get("initial_mode", "auto"),
                initial_charge_power_w=float(storage_config.get("initial_charge_power_w", storage_config.get("max_charge_power_w", 3000))),
                initial_discharge_power_w=float(storage_config.get("initial_discharge_power_w", storage_config.get("max_discharge_power_w", 3000))),
            )
            self.storages.append(storage)

        charger_config = self.config.get("chargers", {})
        self.chargers = []
        for index in range(int(charger_config.get("count", 1))):
            device_id = f"charger_{index}"
            charger = ChargerSimulator(
                device_id,
                auto_session_changes=False,
                initial_status="Charging" if charger_config.get("session_active", False) else "Available",
                charging_rate_w=float(charger_config.get("power_w", 3000)),
                max_power_w=float(charger_config.get("max_power_w", 7000)),
                min_power_w=float(charger_config.get("min_power_w", 1000)),
                power_limit_w=float(charger_config.get("power_limit_w", charger_config.get("max_power_w", 7000))),
            )
            self.chargers.append(charger)

        self.devices = {
            self.grid_meter.device_id: self.grid_meter,
            **{sim.device_id: sim for sim in self.pvs},
            **{sim.device_id: sim for sim in self.storages},
            **{sim.device_id: sim for sim in self.chargers},
        }

    def start(self):
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)

    def _loop(self):
        while self.running:
            self.step()
            time.sleep(self.tick_seconds)

    def step(self):
        apply_scenario_step(self, self.step_count)

        for simulator in self.pvs:
            simulator.update()
        for simulator in self.storages:
            simulator.update()
        for simulator in self.chargers:
            simulator.update()

        base_load_w = float(self.base_load.get_data("power") or 0)
        pv_power_w = sum(float(sim.get_data("power") or 0) for sim in self.pvs)
        storage_power_w = sum(float(sim.get_data("power") or 0) for sim in self.storages)
        charger_power_w = sum(float(sim.get_data("power") or 0) for sim in self.chargers)

        grid_power_w = base_load_w + charger_power_w + storage_power_w - pv_power_w
        self.grid_meter.set_data("power", round(grid_power_w, 3))
        self.step_count += 1

    def get_device_infos(self) -> dict[str, dict[str, Any]]:
        info = {}
        for device_id, simulator in self.devices.items():
            raw_status = str(simulator.get_status()).lower()
            device_info = {
                "device_id": device_id,
                "type": simulator.device_type,
                "protocol": "simulation",
                "source": "simulated",
                "status": "offline" if raw_status == "offline" else "online",
            }
            if simulator.device_type == "charging_station":
                device_info["connector_count"] = 1
                device_info["connectors"] = [
                    {
                        "device_id": f"{device_id}:1",
                        "connector_id": 1,
                        "io_device_id": device_id,
                    }
                ]
            info[device_id] = device_info
        return info

    def read_device_data(self, device_id: str, register: str):
        simulator = self.devices.get(device_id)
        if simulator is None:
            return None
        return simulator.get_data(register)

    def write_device_data(self, device_id: str, register: str, value: Any) -> bool:
        simulator = self.devices.get(device_id)
        if simulator is None:
            return False
        success = simulator.set_data(register, value)
        if success:
            self.step()
        return success

    def get_snapshots(self) -> list[dict[str, Any]]:
        timestamp = datetime.now().isoformat()
        snapshots = []
        for device_id, simulator in self.devices.items():
            snapshots.append(
                {
                    "device_id": device_id,
                    "device_type": simulator.device_type,
                    "timestamp": timestamp,
                    "data": dict(simulator.data),
                }
            )
        return snapshots
