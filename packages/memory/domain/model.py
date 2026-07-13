from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from uuid import UUID


class MemorySource(StrEnum):
    EXPLICIT_CLI = "explicit_cli"


@dataclass(frozen=True, slots=True)
class Memory:
    id: str
    content: str
    source: MemorySource
    created_at: datetime
    updated_at: datetime

    def __post_init__(self) -> None:
        UUID(self.id)
        if not self.content.strip():
            raise ValueError("O conteúdo da memória não pode ser vazio.")
        if self.created_at.utcoffset() != timedelta(0):
            raise ValueError("created_at deve usar UTC.")
        if self.updated_at.utcoffset() != timedelta(0):
            raise ValueError("updated_at deve usar UTC.")
        if self.updated_at < self.created_at:
            raise ValueError("updated_at não pode ser anterior a created_at.")
