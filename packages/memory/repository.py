from enum import StrEnum
from typing import Protocol

from packages.memory.model import Memory


class ReplaceResult(StrEnum):
    REPLACED = "replaced"
    NOT_FOUND = "not_found"
    DUPLICATE = "duplicate"
    INVALID = "invalid"
    UNCHANGED = "unchanged"


class MemoryRepository(Protocol):
    def add(self, content: str) -> Memory | None: ...

    def remove(self, content: str) -> bool: ...

    def replace(self, current_content: str, new_content: str) -> ReplaceResult: ...

    def search(self, term: str) -> list[Memory]: ...

    def list(self) -> list[Memory]: ...
