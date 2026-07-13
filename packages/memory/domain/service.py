from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from uuid import UUID, uuid4

from packages.memory.domain.model import Memory, MemorySource
from packages.memory.domain.repository import MemoryRepository


class AddMemoryStatus(StrEnum):
    ADDED = "added"
    DUPLICATE = "duplicate"
    INVALID = "invalid"


@dataclass(frozen=True, slots=True)
class AddMemoryResult:
    status: AddMemoryStatus
    memory: Memory | None = None


class EditMemoryStatus(StrEnum):
    EDITED = "edited"
    NOT_FOUND = "not_found"
    DUPLICATE = "duplicate"
    INVALID = "invalid"
    UNCHANGED = "unchanged"
    CONFLICT = "conflict"


class DeleteMemoryStatus(StrEnum):
    DELETED = "deleted"
    NOT_FOUND = "not_found"
    INVALID = "invalid"
    CONFLICT = "conflict"


class MemoryService:
    def __init__(
        self,
        repository: MemoryRepository,
        id_factory: Callable[[], str] | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._repository = repository
        self._id_factory = id_factory or (lambda: str(uuid4()))
        self._clock = clock or (lambda: datetime.now(UTC))

    def add(self, content: str) -> AddMemoryResult:
        normalized_content = content.strip()
        if not normalized_content:
            return AddMemoryResult(AddMemoryStatus.INVALID)

        memories = self._repository.list()
        if any(memory.content == normalized_content for memory in memories):
            return AddMemoryResult(AddMemoryStatus.DUPLICATE)

        now = self._clock()
        memory = Memory(
            id=self._id_factory(),
            content=normalized_content,
            source=MemorySource.EXPLICIT_CLI,
            created_at=now,
            updated_at=now,
        )
        self._repository.save_all([*memories, memory])
        return AddMemoryResult(AddMemoryStatus.ADDED, memory)

    def delete(self, content: str) -> bool:
        normalized_content = content.strip()
        if not normalized_content:
            return False

        memories = self._repository.list()
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

        self._repository.save_all([*memories[:index], *memories[index + 1 :]])
        return True

    def delete_by_id(
        self,
        memory_id: str,
        expected_content: str,
    ) -> DeleteMemoryStatus:
        try:
            UUID(memory_id)
        except (ValueError, AttributeError, TypeError):
            return DeleteMemoryStatus.INVALID

        expected_value = expected_content.strip()
        if not expected_value:
            return DeleteMemoryStatus.INVALID

        memories = self._repository.list()
        index = next(
            (index for index, memory in enumerate(memories) if memory.id == memory_id),
            None,
        )
        if index is None:
            return DeleteMemoryStatus.NOT_FOUND
        if memories[index].content != expected_value:
            return DeleteMemoryStatus.CONFLICT

        self._repository.save_all([*memories[:index], *memories[index + 1 :]])
        return DeleteMemoryStatus.DELETED

    def edit(self, current_content: str, new_content: str) -> EditMemoryStatus:
        current_value = current_content.strip()
        new_value = new_content.strip()
        if not current_value or not new_value:
            return EditMemoryStatus.INVALID

        memories = self._repository.list()
        index = next(
            (index for index, memory in enumerate(memories) if memory.content == current_value),
            None,
        )
        if index is None:
            return EditMemoryStatus.NOT_FOUND
        if new_value == current_value:
            return EditMemoryStatus.UNCHANGED
        if any(memory.content == new_value for memory in memories):
            return EditMemoryStatus.DUPLICATE

        updated_at = self._clock()
        if updated_at <= memories[index].updated_at:
            updated_at = memories[index].updated_at + timedelta(microseconds=1)
        updated_memories = list(memories)
        updated_memories[index] = replace(memories[index], content=new_value, updated_at=updated_at)
        self._repository.save_all(updated_memories)
        return EditMemoryStatus.EDITED

    def edit_by_id(
        self,
        memory_id: str,
        expected_content: str,
        new_content: str,
    ) -> EditMemoryStatus:
        try:
            UUID(memory_id)
        except (ValueError, AttributeError, TypeError):
            return EditMemoryStatus.INVALID

        expected_value = expected_content.strip()
        new_value = new_content.strip()
        if not expected_value or not new_value:
            return EditMemoryStatus.INVALID

        memories = self._repository.list()
        index = next(
            (index for index, memory in enumerate(memories) if memory.id == memory_id),
            None,
        )
        if index is None:
            return EditMemoryStatus.NOT_FOUND

        current_memory = memories[index]
        if current_memory.content != expected_value:
            return EditMemoryStatus.CONFLICT
        if new_value == current_memory.content:
            return EditMemoryStatus.UNCHANGED
        if any(memory.content == new_value for memory in memories):
            return EditMemoryStatus.DUPLICATE

        updated_at = self._clock()
        if updated_at <= current_memory.updated_at:
            updated_at = current_memory.updated_at + timedelta(microseconds=1)
        updated_memories = list(memories)
        updated_memories[index] = replace(
            current_memory,
            content=new_value,
            updated_at=updated_at,
        )
        self._repository.save_all(updated_memories)
        return EditMemoryStatus.EDITED

    def search(self, term: str) -> list[Memory]:
        normalized_term = term.strip().casefold()
        if not normalized_term:
            return []
        return [
            memory
            for memory in self._repository.list()
            if normalized_term in memory.content.casefold()
        ]

    def list(self) -> list[Memory]:
        return self._repository.list()
