from collections.abc import Sequence
from datetime import UTC, datetime

import pytest

from packages.conversation import (
    AddMemoryIntent,
    DeleteMemoryIntent,
    EditMemoryIntent,
    ModelMemoryIntentInterpreter,
    ModelMessage,
    NameUpdateIntent,
    detect_memory_add,
    detect_memory_delete,
    detect_name_change,
    find_name_memory_candidates,
    should_interpret_memory_add,
    should_interpret_memory_delete,
    should_interpret_memory_edit,
    should_interpret_memory_intent,
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


@pytest.mark.parametrize(
    ("message", "content"),
    [
        ("Lembre que eu trabalho com Flutter.", "eu trabalho com Flutter."),
        ("Memorize que estou aprendendo Python.", "estou aprendendo Python."),
        ("Guarde que prefiro respostas diretas.", "prefiro respostas diretas."),
        ("Não esqueça que meu projeto principal é o Aska.", "meu projeto principal é o Aska."),
        ("lEmBrE QuE   Uso Flutter.   ", "Uso Flutter."),
    ],
)
def test_detect_memory_add_accepts_exact_patterns_and_preserves_content(
    message: str,
    content: str,
) -> None:
    assert detect_memory_add(message) == AddMemoryIntent(content)


@pytest.mark.parametrize(
    "message",
    [
        "Lembre que",
        "Memorize que   ",
        "Guarde que\nUso Flutter.",
        "Não esqueça que uma coisa.\nOutra coisa.",
    ],
)
def test_memory_add_rejects_empty_or_multiline_messages_before_interpretation(
    message: str,
) -> None:
    assert detect_memory_add(message) is None
    assert should_interpret_memory_add(message) is False


def test_detect_memory_add_leaves_non_exact_paraphrase_for_interpreter() -> None:
    message = "Você pode memorizar que uso Flutter?"

    assert detect_memory_add(message) is None
    assert should_interpret_memory_add(message) is True


@pytest.mark.parametrize(
    ("message", "query"),
    [
        ("Esqueça que eu trabalho com Flutter.", "eu trabalho com Flutter."),
        ("Remova a memória: prefiro respostas diretas.", "prefiro respostas diretas."),
        ("Apague a memória: meu projeto antigo.", "meu projeto antigo."),
        ("eSqUeÇa QuE   Uso Python.   ", "Uso Python."),
    ],
)
def test_detect_memory_delete_accepts_exact_patterns(
    message: str,
    query: str,
) -> None:
    assert detect_memory_delete(message) == DeleteMemoryIntent(query)


@pytest.mark.parametrize(
    "message",
    [
        "Esqueça que",
        "Remova a memória:   ",
        "Apague a memória:\nProjeto antigo.",
        "Esqueça que uma coisa.\nOutra coisa.",
    ],
)
def test_memory_delete_rejects_empty_or_multiline_before_interpretation(
    message: str,
) -> None:
    assert detect_memory_delete(message) is None
    assert should_interpret_memory_delete(message) is False


@pytest.mark.parametrize(
    "message",
    [
        "Remova a memória sobre Flutter.",
        "Não precisa mais lembrar que prefiro respostas diretas.",
        "Apague o que você guardou sobre meu projeto antigo.",
    ],
)
def test_memory_delete_gate_accepts_explicit_paraphrases(message: str) -> None:
    assert should_interpret_memory_delete(message) is True


@pytest.mark.parametrize(
    "message",
    [
        "O que você esqueceu?",
        "Você lembra de Flutter?",
        "Quais memórias podem ser removidas?",
        "Conte o que sabe sobre mim.",
    ],
)
def test_memory_delete_gate_rejects_questions(message: str) -> None:
    assert should_interpret_memory_delete(message) is False


def test_memory_delete_gate_does_not_capture_explicit_memory_add() -> None:
    message = "Não esqueça que prefiro respostas diretas."

    assert should_interpret_memory_add(message) is True
    assert should_interpret_memory_delete(message) is False


@pytest.mark.parametrize(
    "message",
    [
        "Atualize a memória sobre Flutter: agora eu trabalho com Python.",
        "Corrija a memória que diz que prefiro respostas longas; prefiro respostas curtas.",
        "Troque minha preferência por tema claro para tema escuro.",
        "A informação sobre meu projeto antigo mudou: agora o projeto principal é o Aska.",
    ],
)
def test_memory_edit_gate_accepts_explicit_memory_changes(message: str) -> None:
    assert should_interpret_memory_edit(message) is True


@pytest.mark.parametrize(
    "message",
    [
        "Atualize meu aplicativo.",
        "Corrija este código.",
        "Mude de assunto.",
        "O que mudou nas minhas memórias?",
        "Qual é minha preferência atual?",
    ],
)
def test_memory_edit_gate_rejects_common_or_insufficient_requests(message: str) -> None:
    assert should_interpret_memory_edit(message) is False


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
    "message",
    [
        "Lembre que eu trabalho com Flutter.",
        "Quero lembrar que prefiro respostas diretas.",
        "Memorize que estou aprendendo Python.",
        "Você pode memorizar que estou aprendendo Python?",
        "Guarde que prefiro respostas diretas.",
        "Quero guardar que meu projeto principal é o Aska.",
        "Não esqueça que meu projeto principal é o Aska.",
    ],
)
def test_memory_intent_gate_accepts_explicit_memory_requests(message: str) -> None:
    assert should_interpret_memory_intent(message) is True
    assert should_interpret_memory_add(message) is True


@pytest.mark.parametrize(
    "message",
    [
        "O que você lembra sobre mim?",
        "Quais são minhas memórias?",
        "Como vai?",
        "Você esqueceu meu nome?",
        "Conte o que sabe sobre Flutter.",
    ],
)
def test_memory_intent_gate_rejects_questions_and_common_messages(message: str) -> None:
    assert should_interpret_memory_intent(message) is False
    assert should_interpret_memory_add(message) is False


def test_model_interpreter_returns_typed_memory_add() -> None:
    provider = StaticProvider('{"action":"add_memory","content":"Eu trabalho com Flutter."}')
    interpreter = ModelMemoryIntentInterpreter(provider)

    result = interpreter.interpret("Lembre que eu trabalho com Flutter.")

    assert result == AddMemoryIntent("Eu trabalho com Flutter.")


def test_model_interpreter_returns_typed_memory_delete() -> None:
    provider = StaticProvider('{"action":"delete_memory","query":"trabalho com Flutter"}')
    interpreter = ModelMemoryIntentInterpreter(provider)

    result = interpreter.interpret("Remova a memória sobre Flutter.")

    assert result == DeleteMemoryIntent("trabalho com Flutter")


def test_model_interpreter_returns_typed_memory_edit() -> None:
    provider = StaticProvider(
        '{"action":"edit_memory","query":"trabalho com Flutter",'
        '"new_content":"Eu trabalho com Python."}'
    )
    interpreter = ModelMemoryIntentInterpreter(provider)

    result = interpreter.interpret(
        "Atualize a memória sobre Flutter: agora eu trabalho com Python."
    )

    assert result == EditMemoryIntent("trabalho com Flutter", "Eu trabalho com Python.")


@pytest.mark.parametrize(
    "response",
    [
        '```json\n{"action":"add_memory","content":"Gosto de Flutter."}\n```',
        '{"action":"add_memory","content":"Gosto de Flutter.","extra":true}',
        '{"action":"add_memory","content":""}',
        '{"action":"add_memory","content":42}',
        '{"action":"add_memory","content":"Uma memória.\nOutra memória."}',
        '{"action":"unknown","content":"Gosto de Flutter."}',
    ],
)
def test_model_interpreter_rejects_invalid_memory_add(response: str) -> None:
    interpreter = ModelMemoryIntentInterpreter(StaticProvider(response))

    assert interpreter.interpret("Lembre que gosto de Flutter.") is None


@pytest.mark.parametrize(
    "response",
    [
        '```json\n{"action":"delete_memory","query":"Flutter"}\n```',
        '{"action":"delete_memory","query":"Flutter","extra":true}',
        '{"action":"delete_memory","query":""}',
        '{"action":"delete_memory","query":42}',
        '{"action":"delete_memory","query":"Flutter\nPython"}',
        '{"action":"remove_memory","query":"Flutter"}',
    ],
)
def test_model_interpreter_rejects_invalid_memory_delete(response: str) -> None:
    interpreter = ModelMemoryIntentInterpreter(StaticProvider(response))

    assert interpreter.interpret("Remova a memória sobre Flutter.") is None


@pytest.mark.parametrize(
    "response",
    [
        '```json\n{"action":"edit_memory","query":"Flutter","new_content":"Python"}\n```',
        '{"action":"edit_memory","query":"Flutter","new_content":"Python","extra":true}',
        '{"action":"edit_memory","query":"","new_content":"Python"}',
        '{"action":"edit_memory","query":"Flutter","new_content":""}',
        '{"action":"edit_memory","query":42,"new_content":"Python"}',
        '{"action":"edit_memory","query":"Flutter","new_content":42}',
        '{"action":"edit_memory","query":"Flutter\nDart","new_content":"Python"}',
        '{"action":"edit_memory","query":"Flutter","new_content":"Python\nDart"}',
        '{"action":"edit_memory","query":" Flutter ","new_content":"flutter"}',
        '{"action":"unknown","query":"Flutter","new_content":"Python"}',
        "not-json",
    ],
)
def test_model_interpreter_rejects_invalid_memory_edit(response: str) -> None:
    interpreter = ModelMemoryIntentInterpreter(StaticProvider(response))

    assert interpreter.interpret("Atualize a memória sobre Flutter.") is None


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
