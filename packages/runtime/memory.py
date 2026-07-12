import json
from pathlib import Path


class MemoryStore:
    def __init__(self, path: str | Path | None = None) -> None:
        self._path = Path(path) if path is not None else None
        if self._path is not None:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            if not self._path.exists():
                self._path.write_text("[]", encoding="utf-8")

    def add(self, memory: str) -> None:
        normalized_memory = memory.strip()
        if not normalized_memory or self._path is None:
            return

        memories = self.list()
        if normalized_memory not in memories:
            memories.append(normalized_memory)
            self._write(memories)

    def remove(self, memory: str) -> bool:
        normalized_memory = memory.strip()
        if not normalized_memory or self._path is None:
            return False

        memories = self.list()
        if normalized_memory not in memories:
            return False

        memories.remove(normalized_memory)
        self._write(memories)
        return True

    def list(self) -> list[str]:
        if self._path is None:
            return []

        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, FileNotFoundError):
            return []

        if isinstance(data, list) and all(isinstance(item, str) for item in data):
            return data
        return []

    def _write(self, memories: list[str]) -> None:
        if self._path is None:
            return
        self._path.write_text(json.dumps(memories, ensure_ascii=False, indent=2), encoding="utf-8")
