import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

from packages.memory.model import Memory, MemorySource
from packages.memory.repository import ReplaceResult


class MemoryStoreError(Exception):
    """Raised when persisted memories cannot be safely changed."""


class JsonMemoryStore:
    def __init__(self, path: str | Path | None = None) -> None:
        self._path = Path(path) if path is not None else None
        self._cache: list[Memory] | None = None
        self._load_error: MemoryStoreError | None = None
        if self._path is not None:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            if not self._path.exists():
                self._path.write_text("[]", encoding="utf-8")

    def add(self, content: str) -> Memory | None:
        normalized_content = content.strip()
        if not normalized_content or self._path is None:
            return None

        memories = self._memories(strict=True)
        if any(memory.content == normalized_content for memory in memories):
            return None

        now = self._utc_now()
        memory = Memory(
            id=str(uuid4()),
            content=normalized_content,
            source=MemorySource.EXPLICIT_CLI,
            created_at=now,
            updated_at=now,
        )
        memories.append(memory)
        self._write()
        return memory

    def remove(self, content: str) -> bool:
        normalized_content = content.strip()
        if not normalized_content or self._path is None:
            return False

        memories = self._memories(strict=True)
        index = next(
            (
                index
                for index, memory in enumerate(memories)
                if memory.content == normalized_content
            ),
            None,
        )
        if index is None:
            return False

        del memories[index]
        self._write()
        return True

    def replace(self, current_content: str, new_content: str) -> ReplaceResult:
        current_value = current_content.strip()
        new_value = new_content.strip()
        if not current_value or not new_value or self._path is None:
            return ReplaceResult.INVALID

        memories = self._memories(strict=True)
        index = next(
            (index for index, memory in enumerate(memories) if memory.content == current_value),
            None,
        )
        if index is None:
            return ReplaceResult.NOT_FOUND
        if new_value == current_value:
            return ReplaceResult.UNCHANGED
        if any(memory.content == new_value for memory in memories):
            return ReplaceResult.DUPLICATE

        updated_at = self._utc_now()
        if updated_at <= memories[index].updated_at:
            updated_at = memories[index].updated_at + timedelta(microseconds=1)
        memories[index] = replace(memories[index], content=new_value, updated_at=updated_at)
        self._write()
        return ReplaceResult.REPLACED

    def search(self, term: str) -> list[Memory]:
        normalized_term = term.strip().casefold()
        if not normalized_term or self._path is None:
            return []

        return [
            memory
            for memory in self._memories(strict=False)
            if normalized_term in memory.content.casefold()
        ]

    def list(self) -> list[Memory]:
        return list(self._memories(strict=False))

    def _memories(self, *, strict: bool) -> list[Memory]:
        if self._cache is None and self._load_error is None:
            self._load()

        if self._load_error is not None:
            if strict:
                raise self._load_error
            return []
        return self._cache if self._cache is not None else []

    def _load(self) -> None:
        if self._path is None:
            self._cache = []
            return

        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            if not isinstance(data, list):
                raise MemoryStoreError("O arquivo de memórias não contém uma lista.")
            self._cache = [self._deserialize(item) for item in data]
        except (
            json.JSONDecodeError,
            FileNotFoundError,
            KeyError,
            TypeError,
            ValueError,
        ) as error:
            self._load_error = MemoryStoreError("O arquivo de memórias possui formato inválido.")
            self._load_error.__cause__ = error

    @staticmethod
    def _deserialize(data: Any) -> Memory:
        if not isinstance(data, dict):
            raise TypeError("Cada memória deve ser um objeto JSON.")
        return Memory(
            id=data["id"],
            content=data["content"],
            source=MemorySource(data["source"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
        )

    @staticmethod
    def _serialize(memory: Memory) -> dict[str, str]:
        return {
            "id": memory.id,
            "content": memory.content,
            "source": memory.source.value,
            "created_at": memory.created_at.isoformat(),
            "updated_at": memory.updated_at.isoformat(),
        }

    @staticmethod
    def _utc_now() -> datetime:
        return datetime.now(UTC)

    def _write(self) -> None:
        if self._path is None or self._cache is None:
            return
        data = [self._serialize(memory) for memory in self._cache]
        self._path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
