from typing import Any, Callable, Dict, Optional

from ..logger import get_logger
from .base import ProtocolBase
from .modbus_factory import build_modbus_endpoint_key, create_modbus_protocol
from .mqtt import MQTTProtocol
from .ocpp import OCPPProtocol
from .simulation import SimulationProtocol


class ProtocolRegistry:
    def __init__(
        self,
        config: Dict[str, Any],
        *,
        protocol_builders: Optional[Dict[str, Callable[[Dict[str, Any]], ProtocolBase]]] = None,
        modbus_protocol_factory: Callable[..., ProtocolBase] = create_modbus_protocol,
        modbus_endpoint_builder: Callable[..., str] = build_modbus_endpoint_key,
    ):
        self.logger = get_logger("ProtocolRegistry")
        self.config = config
        self.protocols: Dict[str, ProtocolBase] = {}
        self.endpoint_protocols: Dict[str, ProtocolBase] = {}
        self._protocol_builders = protocol_builders or {
            "mqtt": MQTTProtocol,
            "ocpp": OCPPProtocol,
            "simulation": SimulationProtocol,
        }
        self._modbus_protocol_factory = modbus_protocol_factory
        self._modbus_endpoint_builder = modbus_endpoint_builder
        self._init_protocols()

    def _init_protocols(self):
        if "modbus" in self.config:
            self.protocols["modbus"] = self._modbus_protocol_factory(self.config["modbus"])
            endpoint_key = self._modbus_endpoint_builder(self.config["modbus"])
            self.endpoint_protocols[endpoint_key] = self.protocols["modbus"]

        for protocol_name, builder in self._protocol_builders.items():
            if protocol_name in self.config:
                self.protocols[protocol_name] = builder(self.config[protocol_name])

    def get_protocol(self, protocol_name: Optional[str]) -> Optional[ProtocolBase]:
        if not protocol_name:
            return None
        return self.protocols.get(protocol_name)

    def get_protocol_for_device(self, device_info: Dict[str, Any]) -> Optional[ProtocolBase]:
        protocol_name = device_info.get("protocol")
        if protocol_name != "modbus":
            return self.get_protocol(protocol_name)

        endpoint_key = self._build_modbus_endpoint_key(device_info)
        if not endpoint_key:
            return self.protocols.get("modbus")

        protocol = self.endpoint_protocols.get(endpoint_key)
        if protocol is None:
            protocol = self._modbus_protocol_factory(device_info, defaults=self.config.get("modbus", {}))
            self.endpoint_protocols[endpoint_key] = protocol

        if not protocol.is_connected:
            protocol.connect()
        return protocol

    def _build_modbus_endpoint_key(self, device_info: Dict[str, Any]) -> Optional[str]:
        try:
            return self._modbus_endpoint_builder(device_info, defaults=self.config.get("modbus", {}))
        except ValueError:
            return None

    def connect_all(self) -> list[str]:
        connected_protocols: list[str] = []
        for protocol_name, protocol in self.protocols.items():
            self.logger.info(f"连接{protocol_name}协议...")
            try:
                success = protocol.connect()
                if success:
                    self.logger.info(f"{protocol_name}协议连接成功")
                    connected_protocols.append(protocol_name)
                else:
                    self.logger.warning(f"{protocol_name}协议连接失败，将在无此协议模式下运行")
            except Exception as exc:
                self.logger.error(f"{protocol_name}协议连接异常: {exc}，将在无此协议模式下运行")
        return connected_protocols

    def disconnect_all(self):
        disconnected: set[int] = set()
        for protocol_name, protocol in self.protocols.items():
            self.logger.info(f"断开{protocol_name}协议...")
            protocol.disconnect()
            disconnected.add(id(protocol))

        for protocol in self.endpoint_protocols.values():
            if id(protocol) in disconnected:
                continue
            protocol.disconnect()
            disconnected.add(id(protocol))
