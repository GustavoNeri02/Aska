from collections.abc import Callable, Iterator
from pathlib import Path

from packages.conversation import ModelProviderError
from packages.memory import JsonMemoryDataSource, LocalMemoryRepository, MemoryService


def create_memory_service(path: str | Path) -> MemoryService:
    return MemoryService(LocalMemoryRepository(JsonMemoryDataSource(path)))


def create_temp_memory_service(tmp_path: Path) -> MemoryService:
    return create_memory_service(path=tmp_path / "memories.json")


class FakeProvider:
    def __init__(self, response: str = "Resposta local") -> None:
        self.response = response
        self.messages: list[str] = []

    def generate(self, prompt: str) -> str:
        self.messages.append(prompt)
        return self.response


class FailingProvider:
    def generate(self, prompt: str) -> str:
        del prompt
        raise ModelProviderError("Modelo indisponível")


class FailingThenWorkingProvider:
    def __init__(self, response: str = "Resposta local") -> None:
        self.response = response
        self.messages: list[str] = []
        self._should_fail = True

    def generate(self, prompt: str) -> str:
        self.messages.append(prompt)
        if self._should_fail:
            self._should_fail = False
            raise ModelProviderError("Modelo indisponível")
        return self.response


def create_input_reader(messages: list[str]) -> Callable[[str], str]:
    iterator: Iterator[str] = iter(messages)

    def read_input(_: str) -> str:
        return next(iterator)

    return read_input


def create_interrupting_reader(error: BaseException) -> Callable[[str], str]:
    def read_input(_: str) -> str:
        raise error

    return read_input
