from typing import Protocol

from packages.memory.domain.model import Memory


class MemoryRepositoryError(RuntimeError):
    """Raised when persisted memories cannot be safely read or written."""


class MemoryRepository(Protocol):
    def list(self) -> list[Memory]: ...

    def save_all(self, memories: list[Memory]) -> None: ...
