from .base import DeviceSimulator


class BaseLoadSimulator(DeviceSimulator):
    """Simple base-load simulator for site-level energy balance."""

    def __init__(self, device_id: str, power_w: float = 2000.0):
        super().__init__(device_id, "base_load")
        self.data = {
            "power": float(power_w),
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
