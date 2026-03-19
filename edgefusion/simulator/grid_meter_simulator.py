from .base import DeviceSimulator


class GridMeterSimulator(DeviceSimulator):
    """Derived grid-meter simulator updated by the site energy balance."""

    def __init__(self, device_id: str):
        super().__init__(device_id, "grid_meter")
        self.data = {
            "power": 0.0,
            "status": "online",
        }

    def get_data(self, register: str):
        return self.data.get(register)

    def set_data(self, register: str, value):
        if register == "power":
            self.data["power"] = float(value)
            return True
        if register == "status":
            self.data["status"] = value
            return True
        return False

    def update(self):
        self.last_updated = self.last_updated
