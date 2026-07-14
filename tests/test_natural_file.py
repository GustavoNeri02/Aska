from collections.abc import Sequence

import pytest

from packages.conversation import (
    ModelFileIntentInterpreter,
    ModelMessage,
    ReadTextFileIntent,
    should_interpret_file_read,
)


class StaticProvider:
    def __init__(self, response: str) -> None:
        self.response = response
        self.requests: list[list[ModelMessage]] = []

    def generate(self, messages: Sequence[ModelMessage]) -> str:
        self.requests.append(list(messages))
        return self.response


@pytest.mark.parametrize(
    "message",
    [
        "Leia AGENTS.md e resuma as instruções principais.",
        "Quero ler AGENTS.md.",
        "Abra o arquivo docs/README.md e explique.",
        "Pode abrir pyproject.toml?",
        "Consulte pyproject.toml para responder.",
        "Quero consultar docs/README.md.",
        "Veja o arquivo AGENTS.md.",
    ],
)
def test_file_read_gate_accepts_explicit_requests(message: str) -> None:
    assert should_interpret_file_read(message) is True


@pytest.mark.parametrize(
    "message",
    [
        "Como arquivos funcionam em Python?",
        "Leia isso para mim.",
        "Leia minha mensagem.",
        "Abra sua mente.",
        "Consulte sua memória.",
        "Veja o arquivo.",
        "O AGENTS.md é importante?",
        "Leia AGENTS.md\ne README.md.",
    ],
)
def test_file_read_gate_rejects_common_or_ambiguous_messages(message: str) -> None:
    assert should_interpret_file_read(message) is False


def test_model_file_interpreter_returns_typed_intent() -> None:
    provider = StaticProvider('{"action":"read_text_file","path":"AGENTS.md"}')
    interpreter = ModelFileIntentInterpreter(provider)

    result = interpreter.interpret("Leia AGENTS.md e resuma.")

    assert result == ReadTextFileIntent("AGENTS.md")
    assert len(provider.requests) == 1
    assert "não leia arquivos" in provider.requests[0][0].content
    assert provider.requests[0][-1].content == "Leia AGENTS.md e resuma."


@pytest.mark.parametrize(
    "response",
    [
        '{"action":"none"}',
        '```json\n{"action":"read_text_file","path":"AGENTS.md"}\n```',
        'Texto {"action":"read_text_file","path":"AGENTS.md"}',
        '{"action":"read_text_file","path":"AGENTS.md","extra":true}',
        '{"action":"read_text_file","path":""}',
        '{"action":"read_text_file","path":42}',
        '{"action":"read_text_file","path":"AGENTS.md\nREADME.md"}',
        '{"action":"delete_file","path":"AGENTS.md"}',
        "not-json",
    ],
)
def test_model_file_interpreter_rejects_none_or_invalid_json(response: str) -> None:
    interpreter = ModelFileIntentInterpreter(StaticProvider(response))

    assert interpreter.interpret("Leia AGENTS.md.") is None
