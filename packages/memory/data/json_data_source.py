import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

from packages.memory.data.local_data_source import MemoryLocalDataSourceError
from packages.memory.domain.model import Memory, MemorySource


class JsonMemoryDataSource:
    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._cache: list[Memory] | None = None
        self._load_error: MemoryLocalDataSourceError | None = None

    def load(self) -> list[Memory]:
        if self._cache is None and self._load_error is None:
            self._load_from_disk()
        if self._load_error is not None:
            raise self._load_error
        return list(self._cache) if self._cache is not None else []

    def save_all(self, memories: list[Memory]) -> None:
        persisted_memories = list(memories)
        self._write_to_disk(persisted_memories)
        self._cache = persisted_memories
        self._load_error = None

    def _load_from_disk(self) -> None:
        if not self._path.exists():
            self.save_all([])
            return

        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            if not isinstance(data, list):
                self._load_error = MemoryLocalDataSourceError(
                    "O arquivo de memórias não contém uma lista."
                )
                return
            self._cache = [self._deserialize(item) for item in data]
        except (
            json.JSONDecodeError,
            FileNotFoundError,
            KeyError,
            TypeError,
            ValueError,
        ) as error:
            self._load_error = MemoryLocalDataSourceError(
                "O arquivo de memórias possui formato inválido."
            )
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

    def _write_to_disk(self, memories: list[Memory]) -> None:
        data = [self._serialize(memory) for memory in memories]
        serialized = json.dumps(data, ensure_ascii=False, indent=2)
        temporary_path: Path | None = None
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=self._path.parent,
                prefix=f".{self._path.name}.",
                suffix=".tmp",
                delete=False,
            ) as temporary_file:
                temporary_file.write(serialized)
                temporary_file.flush()
                os.fsync(temporary_file.fileno())
                temporary_path = Path(temporary_file.name)
            os.replace(temporary_path, self._path)
        except OSError as error:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)
            raise MemoryLocalDataSourceError(
                "Não foi possível gravar o arquivo de memórias."
            ) from error
