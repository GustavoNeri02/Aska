from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class MemorySource(StrEnum):
    EXPLICIT_CLI = "explicit_cli"


@dataclass(frozen=True, slots=True)
class Memory:
    id: str
    content: str
    source: MemorySource
    created_at: datetime
    updated_at: datetime
