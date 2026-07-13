import pytest

from apps.cli.command_parser import parse_input
from apps.cli.commands import (
    ChatMessage,
    EditMemoryCommand,
    ExitCommand,
    ForgetMemoryCommand,
    InvalidCommand,
    ListMemoriesCommand,
    RememberMemoryCommand,
    SearchMemoryCommand,
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
    assert parse_input("editar memória: sem seta") == InvalidCommand(
        "Use: editar memória: <atual> -> <novo>"
    )


@pytest.mark.parametrize(
    ("user_input", "usage"),
    [
        ("lembrar:   ", "Use: lembrar: <conteúdo>"),
        ("esquecer:   ", "Use: esquecer: <conteúdo>"),
        ("buscar memória:   ", "Use: buscar memória: <termo>"),
        (
            "editar memória: atual ->   ",
            "Informe a memória atual e o novo conteúdo.",
        ),
    ],
)
def test_parser_returns_guidance_for_invalid_commands(user_input: str, usage: str) -> None:
    assert parse_input(user_input) == InvalidCommand(usage)


def test_parser_preserves_regular_chat_message() -> None:
    assert parse_input("Olá, Aska") == ChatMessage("Olá, Aska")
