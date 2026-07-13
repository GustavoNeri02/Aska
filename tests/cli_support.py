from collections.abc import Callable, Iterator, Sequence
from pathlib import Path

from packages.conversation import ModelMessage, ModelProviderError, NameUpdateIntent
from packages.memory import JsonMemoryDataSource, LocalMemoryRepository, MemoryService


def create_memory_service(path: str | Path) -> MemoryService:
    return MemoryService(LocalMemoryRepository(JsonMemoryDataSource(path)))


def create_temp_memory_service(tmp_path: Path) -> MemoryService:
    return create_memory_service(path=tmp_path / "memories.json")


class FakeProvider:
    def __init__(self, response: str = "Resposta local") -> None:
        self.response = response
        self.messages: list[list[ModelMessage]] = []

    def generate(self, messages: Sequence[ModelMessage]) -> str:
        self.messages.append(list(messages))
        return self.response


class FailingProvider:
    def generate(self, messages: Sequence[ModelMessage]) -> str:
        del messages
        raise ModelProviderError("Modelo indisponível")


class FailingThenWorkingProvider:
    def __init__(self, response: str = "Resposta local") -> None:
        self.response = response
        self.messages: list[list[ModelMessage]] = []
        self._should_fail = True

    def generate(self, messages: Sequence[ModelMessage]) -> str:
        self.messages.append(list(messages))
        if self._should_fail:
            self._should_fail = False
            raise ModelProviderError("Modelo indisponível")
        return self.response


class FakeMemoryIntentInterpreter:
    def __init__(self, result: NameUpdateIntent | None) -> None:
        self.result = result
        self.inputs: list[str] = []

    def interpret(self, user_input: str) -> NameUpdateIntent | None:
        self.inputs.append(user_input)
        return self.result


def create_input_reader(messages: list[str]) -> Callable[[str], str]:
    iterator: Iterator[str] = iter(messages)

    def read_input(_: str) -> str:
        return next(iterator)

    return read_input


def create_interrupting_reader(error: BaseException) -> Callable[[str], str]:
    def read_input(_: str) -> str:
        raise error

    return read_input
