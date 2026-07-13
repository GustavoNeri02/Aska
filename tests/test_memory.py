import json
from datetime import UTC
from pathlib import Path
from uuid import UUID

import pytest

from packages.memory import (
    AddMemoryStatus,
    EditMemoryStatus,
    JsonMemoryDataSource,
    LocalMemoryRepository,
    MemoryRepositoryError,
    MemoryService,
)


def create_memory_service(path: str | Path) -> MemoryService:
    return MemoryService(LocalMemoryRepository(JsonMemoryDataSource(path)))


def test_creation_has_unique_stable_ids_and_utc_metadata(tmp_path: Path) -> None:
    path = tmp_path / "memories.json"
    memory_service = create_memory_service(path)

    first = memory_service.add("gosto de Python").memory
    second = memory_service.add("gosto de Dart").memory

    assert first is not None
    assert second is not None
    assert first.id != second.id
    assert UUID(first.id)
    assert first.source == "explicit_cli"
    assert first.created_at == first.updated_at
    assert first.created_at.tzinfo is UTC
    assert [memory.id for memory in memory_service.list()] == [first.id, second.id]
    assert [memory.id for memory in create_memory_service(path).search("gosto")] == [
        first.id,
        second.id,
    ]


def test_edit_preserves_identity_and_creation_metadata(tmp_path: Path) -> None:
    memory_service = create_memory_service(tmp_path / "memories.json")
    original = memory_service.add("gosto de Python").memory
    assert original is not None

    status = memory_service.edit("gosto de Python", "gosto de Dart")
    edited = memory_service.list()[0]

    assert status is EditMemoryStatus.EDITED
    assert edited.content == "gosto de Dart"
    assert edited.id == original.id
    assert edited.source == original.source
    assert edited.created_at == original.created_at
    assert edited.updated_at > original.updated_at


def test_serialization_round_trip_uses_structured_objects(tmp_path: Path) -> None:
    path = tmp_path / "memories.json"
    created = create_memory_service(path).add("conteúdo persistido").memory
    assert created is not None

    data = json.loads(path.read_text(encoding="utf-8"))

    assert data == [
        {
            "id": created.id,
            "content": created.content,
            "source": created.source.value,
            "created_at": created.created_at.isoformat(),
            "updated_at": created.updated_at.isoformat(),
        }
    ]
    assert create_memory_service(path).list() == [created]


def test_string_list_is_rejected_without_being_overwritten(tmp_path: Path) -> None:
    path = tmp_path / "memories.json"
    string_list = json.dumps(["primeira", "segunda"], ensure_ascii=False)
    path.write_text(string_list, encoding="utf-8")
    memory_service = create_memory_service(path)

    with pytest.raises(MemoryRepositoryError):
        memory_service.list()
    with pytest.raises(MemoryRepositoryError):
        memory_service.add("nova memória")
    assert path.read_text(encoding="utf-8") == string_list


def test_invalid_json_is_not_silently_overwritten(tmp_path: Path) -> None:
    path = tmp_path / "memories.json"
    invalid_json = "{not valid json"
    path.write_text(invalid_json, encoding="utf-8")
    memory_service = create_memory_service(path)

    with pytest.raises(MemoryRepositoryError):
        memory_service.list()
    with pytest.raises(MemoryRepositoryError):
        memory_service.add("não pode sobrescrever")
    assert path.read_text(encoding="utf-8") == invalid_json


def test_remove_deletes_only_selected_memory(tmp_path: Path) -> None:
    memory_service = create_memory_service(tmp_path / "memories.json")
    first = memory_service.add("primeira").memory
    second = memory_service.add("segunda").memory
    third = memory_service.add("terceira").memory

    assert memory_service.delete("segunda") is True
    assert memory_service.list() == [first, third]
    assert second is not None


def test_duplicate_content_is_not_created(tmp_path: Path) -> None:
    memory_service = create_memory_service(tmp_path / "memories.json")

    created = memory_service.add("duplicada").memory
    duplicate = memory_service.add("duplicada")

    assert created is not None
    assert duplicate.status is AddMemoryStatus.DUPLICATE
    assert memory_service.list() == [created]


def test_repository_reuses_loaded_memories_without_reading_json_again(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    memory_service = create_memory_service(tmp_path / "memories.json")
    created = memory_service.add("memória em cache").memory
    assert created is not None

    def fail_if_read_again(*args: object, **kwargs: object) -> str:
        del args, kwargs
        raise AssertionError("o JSON foi lido novamente")

    monkeypatch.setattr(Path, "read_text", fail_if_read_again)

    assert memory_service.list() == [created]
    assert memory_service.search("cache") == [created]


def test_atomic_write_preserves_file_and_cache_when_commit_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "memories.json"
    memory_service = create_memory_service(path)
    created = memory_service.add("memória original").memory
    persisted_before = path.read_text(encoding="utf-8")

    def fail_atomic_replace(source: object, destination: object) -> None:
        del source, destination
        raise OSError("falha simulada")

    monkeypatch.setattr("packages.memory.data.json_data_source.os.replace", fail_atomic_replace)

    with pytest.raises(MemoryRepositoryError, match="gravar"):
        memory_service.add("memória não persistida")

    assert path.read_text(encoding="utf-8") == persisted_before
    assert memory_service.list() == [created]
    assert list(tmp_path.glob("*.tmp")) == []
