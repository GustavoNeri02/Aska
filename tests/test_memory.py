import json
from datetime import UTC
from pathlib import Path
from uuid import UUID

import pytest

from packages.memory import JsonMemoryStore as MemoryStore
from packages.memory import MemoryStoreError, ReplaceResult


def test_creation_has_unique_stable_ids_and_utc_metadata(tmp_path: Path) -> None:
    path = tmp_path / "memories.json"
    store = MemoryStore(path)

    first = store.add("gosto de Python")
    second = store.add("gosto de Dart")

    assert first is not None
    assert second is not None
    assert first.id != second.id
    assert UUID(first.id)
    assert first.source == "explicit_cli"
    assert first.created_at == first.updated_at
    assert first.created_at.tzinfo is UTC
    assert [memory.id for memory in store.list()] == [first.id, second.id]
    assert [memory.id for memory in MemoryStore(path).search("gosto")] == [
        first.id,
        second.id,
    ]


def test_edit_preserves_identity_and_creation_metadata(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path / "memories.json")
    original = store.add("gosto de Python")
    assert original is not None

    result = store.replace("gosto de Python", "gosto de Dart")
    edited = store.list()[0]

    assert result is ReplaceResult.REPLACED
    assert edited.content == "gosto de Dart"
    assert edited.id == original.id
    assert edited.source == original.source
    assert edited.created_at == original.created_at
    assert edited.updated_at > original.updated_at


def test_serialization_round_trip_uses_structured_objects(tmp_path: Path) -> None:
    path = tmp_path / "memories.json"
    created = MemoryStore(path).add("conteúdo persistido")
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
    assert MemoryStore(path).list() == [created]


def test_string_list_is_rejected_without_being_overwritten(tmp_path: Path) -> None:
    path = tmp_path / "memories.json"
    string_list = json.dumps(["primeira", "segunda"], ensure_ascii=False)
    path.write_text(string_list, encoding="utf-8")
    store = MemoryStore(path)

    assert store.list() == []
    with pytest.raises(MemoryStoreError):
        store.add("nova memória")
    assert path.read_text(encoding="utf-8") == string_list


def test_invalid_json_is_not_silently_overwritten(tmp_path: Path) -> None:
    path = tmp_path / "memories.json"
    invalid_json = "{not valid json"
    path.write_text(invalid_json, encoding="utf-8")
    store = MemoryStore(path)

    assert store.list() == []
    with pytest.raises(MemoryStoreError):
        store.add("não pode sobrescrever")
    assert path.read_text(encoding="utf-8") == invalid_json


def test_remove_deletes_only_selected_memory(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path / "memories.json")
    first = store.add("primeira")
    second = store.add("segunda")
    third = store.add("terceira")

    assert store.remove("segunda") is True
    assert store.list() == [first, third]
    assert second is not None


def test_duplicate_content_is_not_created(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path / "memories.json")

    created = store.add("duplicada")
    duplicate = store.add("duplicada")

    assert created is not None
    assert duplicate is None
    assert store.list() == [created]


def test_store_reuses_loaded_memories_without_reading_json_again(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = MemoryStore(tmp_path / "memories.json")
    created = store.add("memória em cache")
    assert created is not None

    def fail_if_read_again(*args: object, **kwargs: object) -> str:
        del args, kwargs
        raise AssertionError("o JSON foi lido novamente")

    monkeypatch.setattr(Path, "read_text", fail_if_read_again)

    assert store.list() == [created]
    assert store.search("cache") == [created]
