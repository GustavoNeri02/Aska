from collections.abc import Callable, Iterator

import pytest

from apps.cli.app import (
    build_banner,
    run_conversation_loop,
)
from packages.models import ModelProviderError


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


def test_conversation_sends_message_to_provider() -> None:
    output: list[str] = []
    provider = FakeProvider()

    run_conversation_loop(
        provider,
        input_reader=create_input_reader(["Olá", "sair"]),
        output_writer=output.append,
    )

    assert provider.messages == ["Olá"]
    assert "Aska > Resposta local" in output


def test_conversation_sends_recent_history_as_context() -> None:
    output: list[str] = []
    provider = FakeProvider()

    run_conversation_loop(
        provider,
        input_reader=create_input_reader(["Olá", "Me conte mais", "sair"]),
        output_writer=output.append,
    )

    assert provider.messages[0] == "Olá"
    assert "Histórico da sessão" in provider.messages[1]
    assert "Você: Olá" in provider.messages[1]
    assert "Aska: Resposta local" in provider.messages[1]
    assert "Você: Me conte mais" in provider.messages[1]
    assert "Aska > Resposta local" in output


@pytest.mark.parametrize("command", ["sair", "exit", "quit", " SAIR "])
def test_conversation_stops_when_user_types_exit_command(command: str) -> None:
    output: list[str] = []

    run_conversation_loop(
        FakeProvider(),
        input_reader=create_input_reader([command]),
        output_writer=output.append,
    )

    assert "Até mais, Gustavo." in output


def test_conversation_ignores_blank_messages() -> None:
    output: list[str] = []

    run_conversation_loop(
        FakeProvider(),
        input_reader=create_input_reader(["", "   ", "Olá", "sair"]),
        output_writer=output.append,
    )

    responses = [line for line in output if line.startswith("Aska >")]

    assert len(responses) == 1


@pytest.mark.parametrize("error", [EOFError(), KeyboardInterrupt()])
def test_conversation_handles_interruption(error: BaseException) -> None:
    output: list[str] = []

    run_conversation_loop(
        FakeProvider(),
        input_reader=create_interrupting_reader(error),
        output_writer=output.append,
    )

    assert "\nEncerrando o Aska." in output


def test_conversation_reports_provider_error_and_keeps_running() -> None:
    output: list[str] = []

    run_conversation_loop(
        FailingProvider(),
        input_reader=create_input_reader(["Olá", "sair"]),
        output_writer=output.append,
    )

    assert "Aska > Modelo indisponível" in output
    assert "Até mais, Gustavo." in output


def test_conversation_does_not_include_provider_error_in_next_context() -> None:
    output: list[str] = []
    provider = FailingThenWorkingProvider()

    run_conversation_loop(
        provider,
        input_reader=create_input_reader(["Olá", "Como vai", "sair"]),
        output_writer=output.append,
    )

    assert provider.messages == ["Olá", "Como vai"]
    assert "Aska > Modelo indisponível" in output
    assert "Aska > Resposta local" in output
