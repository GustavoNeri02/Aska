from collections.abc import Sequence

import pytest

from packages.conversation import (
    ModelMessage,
    ModelOpenLocationIntentInterpreter,
    OpenWorkspaceLocationIntent,
    detect_explicit_open_location,
    should_interpret_open_location,
)


class StaticProvider:
    def __init__(self, response: str) -> None:
        self.response = response
        self.requests: list[list[ModelMessage]] = []

    def generate(self, messages: Sequence[ModelMessage]) -> str:
        self.requests.append(list(messages))
        return self.response


@pytest.mark.parametrize(
    ("message", "path"),
    [
        ("Abra a pasta docs no Explorador.", "docs"),
        ("Abra o diretório docs/project no Explorer", "docs/project"),
        ("Abra o Explorador.", "."),
        ("abra o explorer", "."),
        ("abre o programa explorer", "."),
        ("abra o programa Explorador de Arquivos", "."),
        ("abra o explorer em docs", "docs"),
        ("abra o explorer em c:/", "c:/"),
    ],
)
def test_explicit_open_location_is_detected_deterministically(
    message: str,
    path: str,
) -> None:
    assert detect_explicit_open_location(message) == OpenWorkspaceLocationIntent(path)


@pytest.mark.parametrize(
    "message",
    [
        "Mostre a pasta docs no Explorador.",
        "Pode abrir o diretório de documentação no Explorer?",
        "Você poderia abrir o Explorador para mim?",
        "Inicia o Explorer aí, por favor.",
        "Abre aí o Explorador.",
    ],
)
def test_open_location_gate_accepts_clear_requests(message: str) -> None:
    assert should_interpret_open_location(message) is True


@pytest.mark.parametrize(
    "message",
    [
        "Abra sua mente.",
        "Onde fica a pasta docs?",
        "Explique o Windows Explorer.",
        "O Explorer está aberto?",
        "Gosto do Explorador de Arquivos.",
        "Abra README.md.",
    ],
)
def test_open_location_gate_rejects_ambiguous_or_file_requests(message: str) -> None:
    assert should_interpret_open_location(message) is False


def test_model_open_location_interpreter_returns_strict_intent() -> None:
    provider = StaticProvider('{"action":"open_workspace_location","path":"docs"}')

    result = ModelOpenLocationIntentInterpreter(provider).interpret(
        "Pode abrir o diretório de documentação no Explorer?"
    )

    assert result == OpenWorkspaceLocationIntent("docs")
    assert "não abra aplicativos" in provider.requests[0][0].content


@pytest.mark.parametrize(
    "response",
    [
        '{"action":"none"}',
        '{"action":"open_workspace_location","path":""}',
        '{"action":"open_workspace_location","path":"docs","extra":true}',
        '{"action":"open_workspace_location"}',
        '```json\n{"action":"none"}\n```',
        "not-json",
    ],
)
def test_model_open_location_interpreter_rejects_none_or_invalid_json(response: str) -> None:
    interpreter = ModelOpenLocationIntentInterpreter(StaticProvider(response))

    assert interpreter.interpret("abra a pasta") is None
