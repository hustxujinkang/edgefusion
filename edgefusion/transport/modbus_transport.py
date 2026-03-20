from abc import ABC, abstractmethod
from typing import Any, Dict


class ModbusTransport(ABC):
    @abstractmethod
    def connect(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def disconnect(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def read_holding_registers(self, addr: int, count: int, slave: int) -> Any:
        raise NotImplementedError

    @abstractmethod
    def write_register(self, addr: int, value: int, slave: int) -> Any:
        raise NotImplementedError

    @abstractmethod
    def write_registers(self, addr: int, values: list[int], slave: int) -> Any:
        raise NotImplementedError

    @abstractmethod
    def describe_endpoint(self) -> Dict[str, Any]:
        raise NotImplementedError

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        raise NotImplementedError
