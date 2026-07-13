from datetime import UTC, datetime

import pytest

from packages.memory import (
    LocalMemoryRepository,
    Memory,
    MemoryLocalDataSourceError,
    MemoryRepositoryError,
    MemorySource,
)


class FakeMemoryLocalDataSource:
    def __init__(self, memories: list[Memory] | None = None) -> None:
        self.memories = list(memories or [])

    def load(self) -> list[Memory]:
        return list(self.memories)

    def save_all(self, memories: list[Memory]) -> None:
        self.memories = list(memories)


class FailingMemoryLocalDataSource:
    def load(self) -> list[Memory]:
        raise MemoryLocalDataSourceError("falha local")

    def save_all(self, memories: list[Memory]) -> None:
        del memories
        raise MemoryLocalDataSourceError("falha local")


def test_local_repository_delegates_to_local_data_source() -> None:
    memory = Memory(
        id="12345678-1234-5678-1234-567812345678",
        content="gosto de Python",
        source=MemorySource.EXPLICIT_CLI,
        created_at=datetime(2026, 7, 12, tzinfo=UTC),
        updated_at=datetime(2026, 7, 12, tzinfo=UTC),
    )
    data_source = FakeMemoryLocalDataSource()
    repository = LocalMemoryRepository(data_source)

    repository.save_all([memory])

    assert repository.list() == [memory]
    assert data_source.memories == [memory]


def test_local_repository_translates_data_source_errors() -> None:
    repository = LocalMemoryRepository(FailingMemoryLocalDataSource())

    with pytest.raises(MemoryRepositoryError, match="falha local"):
        repository.list()
    with pytest.raises(MemoryRepositoryError, match="falha local"):
        repository.save_all([])
