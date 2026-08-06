from collections.abc import Sequence

import pytest

from packages.conversation import (
    ModelMessage,
    ModelTextSearchIntentInterpreter,
    SearchTextIntent,
    detect_explicit_text_search,
    should_interpret_text_search,
)


class StaticProvider:
    def __init__(self, response: str) -> None:
        self.response = response
        self.requests: list[list[ModelMessage]] = []

    def generate(self, messages: Sequence[ModelMessage]) -> str:
        self.requests.append(list(messages))
        return self.response


def test_quoted_text_search_is_detected_deterministically() -> None:
    result = detect_explicit_text_search('Busque "MemoryService" nos arquivos Python.')

    assert result == SearchTextIntent("MemoryService", extension=".py")


@pytest.mark.parametrize(
    "message",
    [
        "Procure referências a SQLite nos documentos.",
        "Onde o projeto fala sobre busca vetorial?",
        "Quais arquivos mencionam tool calling?",
    ],
)
def test_text_search_gate_accepts_clear_requests(message: str) -> None:
    assert should_interpret_text_search(message) is True


@pytest.mark.parametrize(
    "message",
    [
        "O que é SQLite?",
        "Como funciona a busca em Python?",
        "Procure melhorar esta resposta.",
        "Quais arquivos existem no projeto?",
    ],
)
def test_text_search_gate_rejects_common_or_listing_requests(message: str) -> None:
    assert should_interpret_text_search(message) is False


def test_model_text_search_interpreter_returns_strict_intent() -> None:
    provider = StaticProvider(
        '{"action":"search_text","query":"busca vetorial","directory":"docs","extension":".md"}'
    )

    result = ModelTextSearchIntentInterpreter(provider).interpret(
        "Onde a documentação fala sobre busca vetorial?"
    )

    assert result == SearchTextIntent("busca vetorial", "docs", ".md")
    assert "não acesse o filesystem" in provider.requests[0][0].content


@pytest.mark.parametrize(
    "response",
    [
        '{"action":"none"}',
        '{"action":"search_text","query":"","directory":".","extension":null}',
        '{"action":"search_text","query":"x","directory":"."}',
        '{"action":"search_text","query":"x","directory":".","extension":null,"extra":1}',
        '```json\n{"action":"none"}\n```',
        "not-json",
    ],
)
def test_model_text_search_interpreter_rejects_none_or_invalid_json(response: str) -> None:
    assert ModelTextSearchIntentInterpreter(StaticProvider(response)).interpret("busque") is None
