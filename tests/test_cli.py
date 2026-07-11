from collections.abc import Callable, Iterator

import pytest

from apps.cli.app import (
    build_banner,
    build_placeholder_response,
    run_conversation_loop,
)


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


def test_placeholder_response_explains_missing_model() -> None:
    response = build_placeholder_response("Olá")

    assert "modelo" in response.casefold()


@pytest.mark.parametrize("command", ["sair", "exit", "quit", " SAIR "])
def test_conversation_stops_when_user_types_exit_command(command: str) -> None:
    output: list[str] = []

    run_conversation_loop(
        input_reader=create_input_reader([command]),
        output_writer=output.append,
    )

    assert "Até mais, Gustavo." in output


def test_conversation_ignores_blank_messages() -> None:
    output: list[str] = []

    run_conversation_loop(
        input_reader=create_input_reader(["", "   ", "Olá", "sair"]),
        output_writer=output.append,
    )

    responses = [line for line in output if line.startswith("Aska >")]

    assert len(responses) == 1


@pytest.mark.parametrize("error", [EOFError(), KeyboardInterrupt()])
def test_conversation_handles_interruption(error: BaseException) -> None:
    output: list[str] = []

    run_conversation_loop(
        input_reader=create_interrupting_reader(error),
        output_writer=output.append,
    )

    assert "\nEncerrando o Aska." in output
