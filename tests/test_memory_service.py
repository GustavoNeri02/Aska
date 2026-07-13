from datetime import UTC, datetime

from packages.memory import AddMemoryStatus, EditMemoryStatus, Memory, MemoryService


class InMemoryRepository:
    def __init__(self) -> None:
        self.memories: list[Memory] = []

    def list(self) -> list[Memory]:
        return list(self.memories)

    def save_all(self, memories: list[Memory]) -> None:
        self.memories = list(memories)


def create_service(repository: InMemoryRepository) -> MemoryService:
    return MemoryService(
        repository,
        id_factory=lambda: "12345678-1234-5678-1234-567812345678",
        clock=lambda: datetime(2026, 7, 12, tzinfo=UTC),
    )


def test_service_owns_creation_and_duplicate_rules() -> None:
    repository = InMemoryRepository()
    service = create_service(repository)

    created = service.add("  gosto de Python  ")
    duplicate = service.add("gosto de Python")

    assert created.status is AddMemoryStatus.ADDED
    assert created.memory is not None
    assert created.memory.content == "gosto de Python"
    assert created.memory.id == "12345678-1234-5678-1234-567812345678"
    assert duplicate.status is AddMemoryStatus.DUPLICATE
    assert repository.memories == [created.memory]


def test_service_owns_editing_and_preserves_identity() -> None:
    repository = InMemoryRepository()
    service = create_service(repository)
    original = service.add("Python").memory
    assert original is not None

    status = service.edit("Python", "Dart")
    edited = repository.memories[0]

    assert status is EditMemoryStatus.EDITED
    assert edited.id == original.id
    assert edited.created_at == original.created_at
    assert edited.updated_at > original.updated_at
    assert edited.content == "Dart"


def test_service_owns_search_order_and_removal() -> None:
    repository = InMemoryRepository()
    service = create_service(repository)
    service.add("gosto de Python")
    service = MemoryService(
        repository,
        id_factory=lambda: "87654321-4321-8765-4321-876543218765",
        clock=lambda: datetime(2026, 7, 12, tzinfo=UTC),
    )
    service.add("gosto de Dart")

    assert [memory.content for memory in service.search("GOSTO")] == [
        "gosto de Python",
        "gosto de Dart",
    ]
    assert service.delete("gosto de Python") is True
    assert [memory.content for memory in repository.memories] == ["gosto de Dart"]
