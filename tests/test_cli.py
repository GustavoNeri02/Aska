from collections.abc import Callable, Iterator
from pathlib import Path

import pytest

from apps.cli.app import (
    build_banner,
    run_conversation_loop,
)
from packages.models import ModelProviderError
from packages.runtime.memory import MemoryStore


def create_memory_store(tmp_path: Path) -> MemoryStore:
    return MemoryStore(path=tmp_path / "memories.json")


class FakeProvider:
    def __init__(self, response: str = "Resposta local") -> None:
        self.response = response
        self.messages: list[str] = []

    def generate(self, message: str) -> str:
        self.messages.append(message)
        return self.response


class FailingProvider:
    def generate(self, message: str) -> str:
        del message
        raise ModelProviderError("Modelo indisponível")


class FailingThenWorkingProvider:
    def __init__(self, response: str = "Resposta local") -> None:
        self.response = response
        self.messages: list[str] = []
        self._should_fail = True

    def generate(self, message: str) -> str:
        self.messages.append(message)
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


def test_build_banner_contains_application_name() -> None:
    banner = build_banner()

    assert "Aska" in banner


def test_conversation_sends_message_to_provider(tmp_path: Path) -> None:
    output: list[str] = []
    provider = FakeProvider()

    run_conversation_loop(
        provider,
        input_reader=create_input_reader(["Olá", "sair"]),
        output_writer=output.append,
        memory_store=create_memory_store(tmp_path),
    )

    assert provider.messages == ["Olá"]
    assert "Aska > Resposta local" in output


def test_conversation_sends_recent_history_as_context(tmp_path: Path) -> None:
    output: list[str] = []
    provider = FakeProvider()

    run_conversation_loop(
        provider,
        input_reader=create_input_reader(["Olá", "Me conte mais", "sair"]),
        output_writer=output.append,
        memory_store=create_memory_store(tmp_path),
    )

    assert provider.messages[0] == "Olá"
    assert "Histórico da sessão" in provider.messages[1]
    assert "Você: Olá" in provider.messages[1]
    assert "Aska: Resposta local" in provider.messages[1]
    assert "Você: Me conte mais" in provider.messages[1]
    assert "Aska > Resposta local" in output


@pytest.mark.parametrize("command", ["sair", "exit", "quit", " SAIR "])
def test_conversation_stops_when_user_types_exit_command(command: str, tmp_path: Path) -> None:
    output: list[str] = []

    run_conversation_loop(
        FakeProvider(),
        input_reader=create_input_reader([command]),
        output_writer=output.append,
        memory_store=create_memory_store(tmp_path),
    )

    assert "Até mais, Gustavo." in output


def test_conversation_ignores_blank_messages(tmp_path: Path) -> None:
    output: list[str] = []

    run_conversation_loop(
        FakeProvider(),
        input_reader=create_input_reader(["", "   ", "Olá", "sair"]),
        output_writer=output.append,
        memory_store=create_memory_store(tmp_path),
    )

    responses = [line for line in output if line.startswith("Aska >")]

    assert len(responses) == 1


@pytest.mark.parametrize("error", [EOFError(), KeyboardInterrupt()])
def test_conversation_handles_interruption(error: BaseException, tmp_path: Path) -> None:
    output: list[str] = []

    run_conversation_loop(
        FakeProvider(),
        input_reader=create_interrupting_reader(error),
        output_writer=output.append,
        memory_store=create_memory_store(tmp_path),
    )

    assert "\nEncerrando o Aska." in output


def test_conversation_reports_provider_error_and_keeps_running(tmp_path: Path) -> None:
    output: list[str] = []

    run_conversation_loop(
        FailingProvider(),
        input_reader=create_input_reader(["Olá", "sair"]),
        output_writer=output.append,
        memory_store=create_memory_store(tmp_path),
    )

    assert "Aska > Modelo indisponível" in output
    assert "Até mais, Gustavo." in output


def test_memory_store_persists_memories_to_disk(tmp_path: Path) -> None:
    store = MemoryStore(path=tmp_path / "memories.json")

    store.add("gosto de python")

    assert store.list() == ["gosto de python"]
    assert (tmp_path / "memories.json").exists()


def test_memory_store_ignores_blank_entries(tmp_path: Path) -> None:
    store = MemoryStore(path=tmp_path / "memories.json")

    store.add("   ")

    assert store.list() == []


def test_memory_store_does_not_store_duplicates(tmp_path: Path) -> None:
    store = MemoryStore(path=tmp_path / "memories.json")

    store.add("gosto de python")
    store.add("gosto de python")

    assert store.list() == ["gosto de python"]


def test_memory_store_persists_between_instances(tmp_path: Path) -> None:
    path = tmp_path / "memories.json"
    first_store = MemoryStore(path=path)
    first_store.add("gosto de python")

    second_store = MemoryStore(path=path)

    assert second_store.list() == ["gosto de python"]


def test_conversation_handles_invalid_json_without_broken_flow(tmp_path: Path) -> None:
    output: list[str] = []
    path = tmp_path / "memories.json"
    path.write_text("{not valid json", encoding="utf-8")
    store = MemoryStore(path=path)

    run_conversation_loop(
        FakeProvider(),
        input_reader=create_input_reader(["memórias", "sair"]),
        output_writer=output.append,
        memory_store=store,
    )

    assert "(nenhuma memória registrada)" in output


def test_run_conversation_loop_uses_injected_store_without_touching_real_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    output: list[str] = []

    run_conversation_loop(
        FakeProvider(),
        input_reader=create_input_reader(["lembrar: gosto de python", "sair"]),
        output_writer=output.append,
        memory_store=create_memory_store(tmp_path),
    )

    assert not (tmp_path / "data" / "memory" / "memories.json").exists()


def test_conversation_can_store_and_list_memories(tmp_path: Path) -> None:
    output: list[str] = []
    store = MemoryStore(path=tmp_path / "memories.json")

    run_conversation_loop(
        FakeProvider(),
        input_reader=create_input_reader(["lembrar: gosto de python", "memórias", "sair"]),
        output_writer=output.append,
        memory_store=store,
    )

    assert "Memória registrada localmente." in output
    assert "gosto de python" in output


def test_conversation_includes_saved_memories_in_model_context(tmp_path: Path) -> None:
    provider = FakeProvider()
    store = MemoryStore(path=tmp_path / "memories.json")

    run_conversation_loop(
        provider,
        input_reader=create_input_reader(["lembrar: gosto de python", "Olá", "sair"]),
        output_writer=lambda message: None,
        memory_store=store,
    )

    assert len(provider.messages) == 1
    assert "Memórias salvas:" in provider.messages[0]
    assert "- gosto de python" in provider.messages[0]
    assert "Você: Olá" in provider.messages[0]


def test_conversation_does_not_include_provider_error_in_next_context(tmp_path: Path) -> None:
    output: list[str] = []
    provider = FailingThenWorkingProvider()

    run_conversation_loop(
        provider,
        input_reader=create_input_reader(["Olá", "Como vai", "sair"]),
        output_writer=output.append,
        memory_store=create_memory_store(tmp_path),
    )

    assert provider.messages == ["Olá", "Como vai"]
    assert "Aska > Modelo indisponível" in output
    assert "Aska > Resposta local" in output
