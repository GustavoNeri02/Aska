from collections.abc import Sequence
from datetime import UTC, datetime

import pytest

from packages.conversation import (
    ModelMemoryIntentInterpreter,
    ModelMessage,
    NameUpdateIntent,
    detect_name_change,
    find_name_memory_candidates,
    should_interpret_name_change,
)
from packages.memory import Memory, MemorySource


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
        "Meu nome agora é Gustavo Neri",
        "Mude meu nome para Gustavo Neri",
        "MEU NOME AGORA É Gustavo Neri",
        "mUdE mEu NoMe PaRa Gustavo Neri",
    ],
)
def test_detect_name_change_accepts_supported_patterns_and_case_variations(
    message: str,
) -> None:
    assert detect_name_change(message) == "Meu nome é Gustavo Neri."


@pytest.mark.parametrize(
    "message",
    [
        "Meu nome agora é",
        "Mude meu nome para   ",
        "Meu nome agora é Gustavo Neri, e moro em São Paulo",
        "Meu nome agora é Gustavo Neri porque casei",
        "Qual é o meu nome?",
    ],
)
def test_detect_name_change_rejects_empty_ambiguous_or_unrelated_messages(
    message: str,
) -> None:
    assert detect_name_change(message) is None


def test_find_name_memory_candidates_uses_restricted_text_patterns() -> None:
    now = datetime(2026, 7, 13, tzinfo=UTC)
    memories = [
        Memory(
            id="11111111-1111-1111-1111-111111111111",
            content="Meu nome é Gustavo.",
            source=MemorySource.EXPLICIT_CLI,
            created_at=now,
            updated_at=now,
        ),
        Memory(
            id="22222222-2222-2222-2222-222222222222",
            content="EU ME CHAMO Gustavo Souza.",
            source=MemorySource.EXPLICIT_CLI,
            created_at=now,
            updated_at=now,
        ),
        Memory(
            id="33333333-3333-3333-3333-333333333333",
            content="Gustavo gosta de Python.",
            source=MemorySource.EXPLICIT_CLI,
            created_at=now,
            updated_at=now,
        ),
    ]

    assert find_name_memory_candidates(memories) == memories[:2]


@pytest.mark.parametrize(
    "message",
    [
        "Pode atualizar meu nome para Gustavo Neri?",
        "Quero que você passe a me chamar de Gustavo Neri.",
        "Meu nome mudou para Gustavo Neri.",
        "De agora em diante me chame de Gustavo Neri.",
    ],
)
def test_name_change_gate_accepts_explicit_name_change_language(message: str) -> None:
    assert should_interpret_name_change(message) is True


@pytest.mark.parametrize("message", ["Olá", "Como vai?", "Como devo te chamar?"])
def test_name_change_gate_rejects_common_messages(message: str) -> None:
    assert should_interpret_name_change(message) is False


def test_model_interpreter_returns_typed_name_update() -> None:
    provider = StaticProvider('{"action":"update_name","new_name":"Gustavo Neri"}')
    interpreter = ModelMemoryIntentInterpreter(provider)

    result = interpreter.interpret("Pode atualizar meu nome para Gustavo Neri?")

    assert result == NameUpdateIntent("Gustavo Neri")
    assert len(provider.requests) == 1
    assert provider.requests[0][-1].content == "Pode atualizar meu nome para Gustavo Neri?"


@pytest.mark.parametrize(
    "response",
    [
        '{"action":"none"}',
        '```json\n{"action":"none"}\n```',
        'Texto {"action":"none"}',
        '{"action":"none","extra":true}',
        '{"action":"delete_name","new_name":"Gustavo Neri"}',
        '{"action":"update_name","new_name":""}',
        '{"action":"update_name","new_name":"Gustavo Neri","extra":true}',
        '[{"action":"none"}]',
        "not-json",
    ],
)
def test_model_interpreter_rejects_none_or_invalid_responses(response: str) -> None:
    interpreter = ModelMemoryIntentInterpreter(StaticProvider(response))

    assert interpreter.interpret("Meu nome mudou") is None
