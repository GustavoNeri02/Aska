from packages.memory.data.local_data_source import (
    MemoryLocalDataSource,
    MemoryLocalDataSourceError,
)
from packages.memory.domain.model import Memory
from packages.memory.domain.repository import MemoryRepositoryError


class LocalMemoryRepository:
    def __init__(self, data_source: MemoryLocalDataSource) -> None:
        self._data_source = data_source

    def list(self) -> list[Memory]:
        try:
            return self._data_source.load()
        except MemoryLocalDataSourceError as error:
            raise MemoryRepositoryError(str(error)) from error

    def save_all(self, memories: list[Memory]) -> None:
        try:
            self._data_source.save_all(memories)
        except MemoryLocalDataSourceError as error:
            raise MemoryRepositoryError(str(error)) from error
