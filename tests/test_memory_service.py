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


def test_service_rejects_blank_add_delete_and_search_values() -> None:
    repository = InMemoryRepository()
    service = create_service(repository)

    add_result = service.add("   ")

    assert add_result.status is AddMemoryStatus.INVALID
    assert service.delete("   ") is False
    assert service.search("   ") == []
    assert repository.memories == []


def test_service_reports_missing_delete_and_edit_without_changes() -> None:
    repository = InMemoryRepository()
    service = create_service(repository)
    original = service.add("Python").memory

    assert service.delete("Dart") is False
    assert service.edit("Rust", "Dart") is EditMemoryStatus.NOT_FOUND
    assert repository.memories == [original]


def test_service_rejects_invalid_duplicate_and_unchanged_edits() -> None:
    repository = InMemoryRepository()
    service = create_service(repository)
    python = service.add("Python").memory
    service = MemoryService(
        repository,
        id_factory=lambda: "87654321-4321-8765-4321-876543218765",
        clock=lambda: datetime(2026, 7, 12, tzinfo=UTC),
    )
    dart = service.add("Dart").memory

    assert service.edit("   ", "Rust") is EditMemoryStatus.INVALID
    assert service.edit("Python", "   ") is EditMemoryStatus.INVALID
    assert service.edit("Python", "Dart") is EditMemoryStatus.DUPLICATE
    assert service.edit("Python", "Python") is EditMemoryStatus.UNCHANGED
    assert repository.memories == [python, dart]


def test_service_preserves_memory_position_when_editing() -> None:
    repository = InMemoryRepository()
    service = create_service(repository)
    service.add("Python")
    service = MemoryService(
        repository,
        id_factory=lambda: "87654321-4321-8765-4321-876543218765",
        clock=lambda: datetime(2026, 7, 12, tzinfo=UTC),
    )
    service.add("Dart")
    service = MemoryService(
        repository,
        id_factory=lambda: "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        clock=lambda: datetime(2026, 7, 12, tzinfo=UTC),
    )
    service.add("Rust")

    service.edit("Dart", "Go")

    assert [memory.content for memory in repository.memories] == ["Python", "Go", "Rust"]


def test_service_searches_exact_partial_and_accented_content() -> None:
    repository = InMemoryRepository()
    service = create_service(repository)
    service.add("café da manhã")

    assert [memory.content for memory in service.search("CAFÉ")] == ["café da manhã"]
    assert [memory.content for memory in service.search("café da manhã")] == ["café da manhã"]
    assert service.search("almoço") == []
