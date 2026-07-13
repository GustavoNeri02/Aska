import pytest

from apps.cli.parser import (
    ChatMessage,
    EditMemoryCommand,
    ExitCommand,
    ForgetMemoryCommand,
    ListMemoriesCommand,
    RememberMemoryCommand,
    SearchMemoryCommand,
    parse_input,
)


@pytest.mark.parametrize("value", ["sair", "exit", "quit", "SAIR"])
def test_parser_recognizes_exit_commands(value: str) -> None:
    assert parse_input(value) == ExitCommand()


def test_parser_returns_typed_memory_commands() -> None:
    assert parse_input("memórias") == ListMemoriesCommand()
    assert parse_input("lembrar: gosto de Python") == RememberMemoryCommand("gosto de Python")
    assert parse_input("esquecer: gosto de Python") == ForgetMemoryCommand("gosto de Python")
    assert parse_input("buscar memória: Python") == SearchMemoryCommand("Python")
    assert parse_input("editar memória: Python -> Dart") == EditMemoryCommand("Python", "Dart")


def test_parser_marks_malformed_edit_command() -> None:
    assert parse_input("editar memória: sem seta") == EditMemoryCommand("", "", is_malformed=True)


def test_parser_preserves_regular_chat_message() -> None:
    assert parse_input("Olá, Aska") == ChatMessage("Olá, Aska")
