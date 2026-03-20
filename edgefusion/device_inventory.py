from typing import Any, Callable, Dict, Iterable, List, Optional

from .charger_layout import build_connector_views


class DeviceInventory:
    """轻量设备清单与生命周期组件。

    只负责设备/候选设备的存取、连接器视图解析和生命周期动作，
    不负责协议发现、连接建立或读写编排。
    """

    def __init__(
        self,
        normalizer: Callable[[Dict[str, Any]], Dict[str, Any]],
        connector_builder: Callable[[Dict[str, Any]], List[Dict[str, Any]]] = build_connector_views,
    ):
        self._normalizer = normalizer
        self._connector_builder = connector_builder
        self.devices: Dict[str, Dict[str, Any]] = {}
        self.device_candidates: Dict[str, Dict[str, Any]] = {}

    def normalize(self, device_info: Dict[str, Any]) -> Dict[str, Any]:
        return self._normalizer(device_info)

    def _get_connector_view(self, device_id: str, *, include_candidates: bool = False) -> Optional[Dict[str, Any]]:
        collections = [self.devices.values()]
        if include_candidates:
            collections.append(self.device_candidates.values())

        for collection in collections:
            for device_info in collection:
                for connector in self._connector_builder(device_info):
                    if connector.get("device_id") == device_id:
                        return connector
        return None

    def replace_protocol_candidates(
        self,
        protocol_name: str,
        discovered_candidates: Dict[str, Dict[str, Any]],
        *,
        clear_active: bool = False,
    ) -> Dict[str, Dict[str, Any]]:
        stale_candidate_ids = [
            device_id
            for device_id, device_info in self.device_candidates.items()
            if device_info.get("protocol") == protocol_name
        ]
        for device_id in stale_candidate_ids:
            del self.device_candidates[device_id]

        if clear_active:
            stale_device_ids = [
                device_id
                for device_id, device_info in self.devices.items()
                if device_info.get("protocol") == protocol_name
            ]
            for device_id in stale_device_ids:
                del self.devices[device_id]

        self.device_candidates.update(discovered_candidates)
        return {
            device_id: device_info
            for device_id, device_info in self.device_candidates.items()
            if device_info.get("protocol") == protocol_name
        }

    def replace_protocol_devices(
        self,
        protocol_name: str,
        discovered_devices: Dict[str, Dict[str, Any]],
    ) -> Dict[str, Dict[str, Any]]:
        stale_device_ids = [
            device_id
            for device_id, device_info in self.devices.items()
            if device_info.get("protocol") == protocol_name
        ]
        for device_id in stale_device_ids:
            del self.devices[device_id]

        self.devices.update(discovered_devices)
        return {
            device_id: device_info
            for device_id, device_info in self.devices.items()
            if device_info.get("protocol") == protocol_name
        }

    def register_candidate(self, device_info: Dict[str, Any]) -> bool:
        device_id = device_info.get("device_id")
        if not device_id or device_id in self.devices:
            return False
        self.device_candidates[str(device_id)] = self.normalize(device_info)
        return True

    def unregister_candidate(self, device_id: str) -> bool:
        if device_id in self.devices:
            return False
        if device_id in self.device_candidates:
            del self.device_candidates[device_id]
            return True
        return False

    def activate_device(self, device_id: str) -> bool:
        device_info = self.device_candidates.get(device_id)
        if not device_info or device_id in self.devices:
            return False
        self.devices[device_id] = device_info
        return True

    def register_device(self, device_info: Dict[str, Any]) -> bool:
        device_id = device_info.get("device_id")
        if not device_id:
            return False
        self.devices[str(device_id)] = self.normalize(device_info)
        return True

    def unregister_device(self, device_id: str) -> bool:
        if device_id in self.devices:
            del self.devices[device_id]
            return True
        return False

    def get_device(self, device_id: str) -> Optional[Dict[str, Any]]:
        device = self.devices.get(device_id)
        if device:
            return device
        return self._get_connector_view(device_id)

    def get_candidate(self, device_id: str) -> Optional[Dict[str, Any]]:
        device = self.device_candidates.get(device_id)
        if device:
            return device
        return self._get_connector_view(device_id, include_candidates=True)

    def is_connected(self, device_id: str) -> bool:
        return device_id in self.devices or self._get_connector_view(device_id) is not None

    def get_devices(self, device_type: Optional[str] = None) -> List[Dict[str, Any]]:
        if device_type:
            return [device for device in self.devices.values() if device.get("type") == device_type]
        return list(self.devices.values())

    def get_candidates(self, device_type: Optional[str] = None) -> List[Dict[str, Any]]:
        if device_type:
            return [device for device in self.device_candidates.values() if device.get("type") == device_type]
        return list(self.device_candidates.values())

    def get_connectors(self, device_id: str, include_candidates: bool = False) -> List[Dict[str, Any]]:
        device_info = self.devices.get(device_id)
        if device_info is None and include_candidates:
            device_info = self.device_candidates.get(device_id)
        if not device_info:
            return []
        return self._connector_builder(device_info)

    def get_device_status(self, device_id: str) -> str:
        device_info = self.get_device(device_id)
        if not device_info:
            return "Unknown"
        return device_info.get("status", "Unknown")

    def update_device_status(self, device_id: str, status: str):
        if device_id in self.devices:
            self.devices[device_id]["status"] = "offline" if str(status).lower() == "offline" else "online"
