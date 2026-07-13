from typing import Protocol

from packages.memory.domain.model import Memory


class MemoryLocalDataSourceError(RuntimeError):
    """Raised when the local memory data source cannot read or write data."""


class MemoryLocalDataSource(Protocol):
    def load(self) -> list[Memory]: ...

    def save_all(self, memories: list[Memory]) -> None: ...
