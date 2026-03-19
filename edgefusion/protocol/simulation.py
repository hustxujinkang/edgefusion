from typing import Any, Dict, Optional

from ..logger import get_logger
from ..simulator.scenarios import DEFAULT_SCENARIO, SCENARIO_TEMPLATES
from ..simulator.site import SiteSimulator
from .base import ProtocolBase


class SimulationProtocol(ProtocolBase):
    """Protocol adapter exposing the in-process site simulator as virtual devices."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.simulator = None
        self.logger = get_logger("SimulationProtocol")

    def connect(self) -> bool:
        try:
            self._replace_simulator(self.config)
            self.simulator.start()
            self.connected = True
            return True
        except Exception as e:
            self.logger.error("Simulation连接失败: %s", e)
            self.connected = False
            return False

    def disconnect(self) -> bool:
        try:
            if self.simulator:
                self.simulator.stop()
            self.connected = False
            return True
        except Exception as e:
            self.logger.error("Simulation断开失败: %s", e)
            return False

    def read_data(self, device_id: str, register: str) -> Optional[Any]:
        if not self.connected or not self.simulator:
            return None
        return self.simulator.read_device_data(device_id, register)

    def write_data(self, device_id: str, register: str, value: Any) -> bool:
        if not self.connected or not self.simulator:
            return False
        return self.simulator.write_device_data(device_id, register, value)

    def discover_devices(self) -> Dict[str, Dict[str, Any]]:
        if not self.connected or not self.simulator:
            return {}
        return self.simulator.get_device_infos()

    def list_scenarios(self) -> list[str]:
        return sorted(SCENARIO_TEMPLATES.keys())

    def get_current_scenario(self) -> str:
        if self.simulator:
            return self.simulator.config.get("scenario", DEFAULT_SCENARIO)
        return self.config.get("scenario", DEFAULT_SCENARIO)

    def switch_scenario(self, scenario: str) -> bool:
        if scenario not in SCENARIO_TEMPLATES:
            return False

        next_config = dict(self.config)
        next_config["scenario"] = scenario
        old_simulator = self.simulator
        was_running = self.connected

        try:
            if old_simulator:
                old_simulator.stop()
            self._replace_simulator(next_config)
            if was_running and self.simulator:
                self.simulator.start()
            self.connected = True
            return True
        except Exception as e:
            self.logger.error("Simulation场景切换失败: %s", e)
            self.simulator = old_simulator
            if was_running and self.simulator and not self.simulator.running:
                self.simulator.start()
            return False

    def _replace_simulator(self, config: Dict[str, Any]):
        self.config = dict(config)
        self.simulator = SiteSimulator(self.config)
