from typing import Any, Dict, Optional

from ..transport import ModbusRtuTransport, ModbusTcpTransport
from .modbus import ModbusProtocol


def normalize_modbus_config(config: Dict[str, Any], defaults: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    merged: Dict[str, Any] = {}
    if defaults:
        merged.update(defaults)
    if config:
        merged.update(config)

    transport_mode = str(merged.get("transport", merged.get("mode", "tcp"))).lower()
    timeout = int(merged.get("timeout", 5))

    if transport_mode in {"rtu", "serial"}:
        serial_port = merged.get("serial_port")
        if serial_port is None and isinstance(merged.get("port"), str):
            serial_port = merged["port"]
        if not serial_port:
            raise ValueError("Modbus RTU requires serial_port")
        return {
            "transport": "rtu",
            "serial_port": str(serial_port),
            "baudrate": int(merged.get("baudrate", 9600)),
            "bytesize": int(merged.get("bytesize", 8)),
            "parity": str(merged.get("parity", "N")),
            "stopbits": int(merged.get("stopbits", 1)),
            "timeout": timeout,
        }

    host = merged.get("host")
    if not host:
        raise ValueError("Modbus TCP requires host")
    return {
        "transport": "tcp",
        "host": str(host),
        "port": int(merged.get("port", 502)),
        "timeout": timeout,
    }


def build_modbus_endpoint_key(config: Dict[str, Any], defaults: Optional[Dict[str, Any]] = None) -> str:
    normalized = normalize_modbus_config(config, defaults)
    if normalized["transport"] == "rtu":
        return (
            f"modbus+rtu://{normalized['serial_port']}"
            f"?baudrate={normalized['baudrate']}&bytesize={normalized['bytesize']}"
            f"&parity={normalized['parity']}&stopbits={normalized['stopbits']}&timeout={normalized['timeout']}"
        )
    return f"modbus://{normalized['host']}:{normalized['port']}?timeout={normalized['timeout']}"


def create_modbus_transport(config: Dict[str, Any], defaults: Optional[Dict[str, Any]] = None):
    normalized = normalize_modbus_config(config, defaults)
    if normalized["transport"] == "rtu":
        return ModbusRtuTransport(
            serial_port=normalized["serial_port"],
            baudrate=normalized["baudrate"],
            bytesize=normalized["bytesize"],
            parity=normalized["parity"],
            stopbits=normalized["stopbits"],
            timeout=normalized["timeout"],
        )
    return ModbusTcpTransport(
        normalized["host"],
        port=normalized["port"],
        timeout=normalized["timeout"],
    )


def create_modbus_protocol(config: Dict[str, Any], defaults: Optional[Dict[str, Any]] = None) -> ModbusProtocol:
    normalized = normalize_modbus_config(config, defaults)
    transport = create_modbus_transport(normalized)
    return ModbusProtocol(normalized, transport=transport)
