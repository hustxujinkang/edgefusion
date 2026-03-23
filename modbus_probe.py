#! /usr/bin/env python
# -*- coding: utf-8 -*-
"""最小 Modbus 原始寄存器探测脚本。

用途：
- 在不启动 edgefusion.main 的情况下验证 TCP / RTU 连通性
- 读取单个原始寄存器
- 对简单单寄存器进行写入测试

示例：
  python modbus_probe.py --host 192.168.1.10 --unit-id 1 --register 32001 --type u16
  python modbus_probe.py --host 192.168.1.10 --unit-id 1 --device-type energy_storage --vendor generic --model generic_storage
  python modbus_probe.py --transport rtu --serial-port COM3 --baudrate 9600 --unit-id 1 --register 32001 --type u16
  python modbus_probe.py --host 192.168.1.10 --unit-id 1 --register 42001 --type u16 --write 3000
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict

from edgefusion.adapters.model_catalog import get_modbus_model_probe_register
from edgefusion.protocol import create_modbus_protocol


def _parse_numeric(value: str) -> Any:
    text = str(value).strip()
    if not text:
        raise ValueError("empty numeric value")
    if text.lower().startswith(("0x", "-0x")):
        return int(text, 16)
    if any(ch in text for ch in ".eE"):
        number = float(text)
        if number.is_integer():
            return int(number)
        return number
    return int(text)


def _build_protocol_config(args: argparse.Namespace) -> Dict[str, Any]:
    if args.transport == "rtu":
        if not args.serial_port:
            raise ValueError("--serial-port is required when --transport rtu")
        return {
            "transport": "rtu",
            "serial_port": args.serial_port,
            "baudrate": args.baudrate,
            "bytesize": args.bytesize,
            "parity": args.parity,
            "stopbits": args.stopbits,
            "timeout": args.timeout,
        }

    if not args.host:
        raise ValueError("--host is required when --transport tcp")
    return {
        "transport": "tcp",
        "host": args.host,
        "port": args.port,
        "timeout": args.timeout,
    }


def _build_register_definition(args: argparse.Namespace) -> Dict[str, Any]:
    register: Dict[str, Any] = {
        "addr": args.register,
        "type": args.data_type,
    }
    if args.scale != 1:
        register["scale"] = args.scale
    if args.count is not None:
        register["count"] = args.count
    if args.unit:
        register["unit"] = args.unit
    return register


def _resolve_register_definition(args: argparse.Namespace) -> tuple[Dict[str, Any], str]:
    if args.register is not None:
        return _build_register_definition(args), "explicit"

    register = get_modbus_model_probe_register(
        device_type=args.device_type,
        model=args.model,
        vendor=args.vendor,
    )
    if not register:
        raise ValueError(
            "--register is required unless --device-type/--model resolve to a known default probe register"
        )
    return dict(register), "model-default"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Probe a single Modbus register without starting EdgeFusion runtime.")
    parser.add_argument("--transport", choices=["tcp", "rtu"], default="tcp")
    parser.add_argument("--host", help="Modbus TCP host")
    parser.add_argument("--port", type=int, default=502, help="Modbus TCP port")
    parser.add_argument("--serial-port", help="Modbus RTU serial port, e.g. COM3 or /dev/ttyUSB0")
    parser.add_argument("--baudrate", type=int, default=9600)
    parser.add_argument("--bytesize", type=int, default=8)
    parser.add_argument("--parity", default="N")
    parser.add_argument("--stopbits", type=int, default=1)
    parser.add_argument("--timeout", type=int, default=5)
    parser.add_argument("--unit-id", type=int, required=True, help="Modbus slave id")
    parser.add_argument("--device-type", help="EdgeFusion device type, e.g. grid_meter/pv/energy_storage/charging_station")
    parser.add_argument("--vendor", help="Vendor key used by EdgeFusion model catalog")
    parser.add_argument("--model", help="Model key used by EdgeFusion model catalog")
    parser.add_argument("--register", type=int, help="Register address; optional when device_type/vendor/model can resolve a default probe register")
    parser.add_argument("--type", dest="data_type", default="u16", help="u16/i16/u32/i32")
    parser.add_argument("--scale", type=float, default=1.0, help="Scale applied by ModbusProtocol")
    parser.add_argument("--count", type=int, help="Override read register count")
    parser.add_argument("--unit", help="Optional unit label")
    parser.add_argument("--write", help="When set, perform a write instead of a read")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        protocol_config = _build_protocol_config(args)
        register, register_source = _resolve_register_definition(args)
        write_value = _parse_numeric(args.write) if args.write is not None else None
    except ValueError as exc:
        parser.error(str(exc))
        return 2

    protocol = create_modbus_protocol(protocol_config)
    if not protocol.connect():
        print(json.dumps({"success": False, "error": "connect failed"}, ensure_ascii=False))
        return 2

    try:
        if write_value is None:
            value = protocol.read_data(str(args.unit_id), register)
            success = value is not None
            print(
                json.dumps(
                    {
                        "success": success,
                        "action": "read",
                        "transport": protocol_config["transport"],
                        "unit_id": args.unit_id,
                        "device_type": args.device_type,
                        "vendor": args.vendor,
                        "model": args.model,
                        "register_source": register_source,
                        "register": register,
                        "value": value,
                    },
                    ensure_ascii=False,
                )
            )
            return 0 if success else 2

        success = protocol.write_data(str(args.unit_id), register, write_value)
        print(
            json.dumps(
                {
                    "success": bool(success),
                    "action": "write",
                    "transport": protocol_config["transport"],
                    "unit_id": args.unit_id,
                    "device_type": args.device_type,
                    "vendor": args.vendor,
                    "model": args.model,
                    "register_source": register_source,
                    "register": register,
                    "value": write_value,
                },
                ensure_ascii=False,
            )
        )
        return 0 if success else 2
    finally:
        protocol.disconnect()


if __name__ == "__main__":
    raise SystemExit(main())
