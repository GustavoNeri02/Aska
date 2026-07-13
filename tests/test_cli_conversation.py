from pathlib import Path

import pytest

from apps.cli.app import run_conversation_loop
from packages.conversation import ModelRole
from tests.cli_support import (
    FailingProvider,
    FailingThenWorkingProvider,
    FakeProvider,
    create_input_reader,
    create_interrupting_reader,
    create_temp_memory_service,
)


def test_conversation_sends_message_to_provider(tmp_path: Path) -> None:
    output: list[str] = []
    provider = FakeProvider()

    run_conversation_loop(
        provider,
        input_reader=create_input_reader(["Olá", "sair"]),
        output_writer=output.append,
        memory_service=create_temp_memory_service(tmp_path),
    )

    assert [message.role for message in provider.messages[0]] == [
        ModelRole.SYSTEM,
        ModelRole.USER,
    ]
    assert provider.messages[0][-1].content == "Olá"
    assert "Aska > Resposta local" in output


def test_conversation_sends_recent_history_as_context(tmp_path: Path) -> None:
    output: list[str] = []
    provider = FakeProvider()

    run_conversation_loop(
        provider,
        input_reader=create_input_reader(["Olá", "Me conte mais", "sair"]),
        output_writer=output.append,
        memory_service=create_temp_memory_service(tmp_path),
    )

    assert [message.role for message in provider.messages[1]] == [
        ModelRole.SYSTEM,
        ModelRole.USER,
        ModelRole.ASSISTANT,
        ModelRole.USER,
    ]
    assert [message.content for message in provider.messages[1][1:]] == [
        "Olá",
        "Resposta local",
        "Me conte mais",
    ]
    assert "Aska > Resposta local" in output


@pytest.mark.parametrize("command", ["sair", "exit", "quit", " SAIR "])
def test_conversation_stops_when_user_types_exit_command(command: str, tmp_path: Path) -> None:
    output: list[str] = []

    run_conversation_loop(
        FakeProvider(),
        input_reader=create_input_reader([command]),
        output_writer=output.append,
        memory_service=create_temp_memory_service(tmp_path),
    )

    assert "Até mais, Gustavo." in output


def test_conversation_ignores_blank_messages(tmp_path: Path) -> None:
    output: list[str] = []

    run_conversation_loop(
        FakeProvider(),
        input_reader=create_input_reader(["", "   ", "Olá", "sair"]),
        output_writer=output.append,
        memory_service=create_temp_memory_service(tmp_path),
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
        memory_service=create_temp_memory_service(tmp_path),
    )

    assert "\nEncerrando o Aska." in output


def test_conversation_reports_provider_error_and_keeps_running(tmp_path: Path) -> None:
    output: list[str] = []

    run_conversation_loop(
        FailingProvider(),
        input_reader=create_input_reader(["Olá", "sair"]),
        output_writer=output.append,
        memory_service=create_temp_memory_service(tmp_path),
    )

    assert "Aska > Modelo indisponível" in output
    assert "Até mais, Gustavo." in output


def test_conversation_does_not_include_provider_error_in_next_context(tmp_path: Path) -> None:
    output: list[str] = []
    provider = FailingThenWorkingProvider()

    run_conversation_loop(
        provider,
        input_reader=create_input_reader(["Olá", "Como vai", "sair"]),
        output_writer=output.append,
        memory_service=create_temp_memory_service(tmp_path),
    )

    assert [request[-1].content for request in provider.messages] == ["Olá", "Como vai"]
    assert [message.role for message in provider.messages[1]] == [
        ModelRole.SYSTEM,
        ModelRole.USER,
    ]
    assert "Aska > Modelo indisponível" in output
    assert "Aska > Resposta local" in output
