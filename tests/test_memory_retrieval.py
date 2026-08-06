from datetime import UTC, datetime

import pytest

from packages.conversation import TextMemoryRetriever, is_memory_usage_question
from packages.memory import Memory, MemorySource


class Source:
    def __init__(self, memories: list[Memory]) -> None:
        self.memories = memories

    def list(self) -> list[Memory]:
        return list(self.memories)


def _memory(identifier: str, content: str) -> Memory:
    now = datetime(2026, 8, 6, tzinfo=UTC)
    memory_id = f"00000000-0000-0000-0000-{int(identifier):012d}"
    return Memory(memory_id, content, MemorySource.EXPLICIT_CLI, now, now)


def test_retriever_ranks_overlap_and_preserves_source_order_on_ties() -> None:
    memories = [
        _memory("1", "Gosto de Python e automação"),
        _memory("2", "Trabalho profissionalmente com Flutter"),
        _memory("3", "Gosto de Flutter para aplicativos"),
    ]

    selection = TextMemoryRetriever(Source(memories)).retrieve("O que eu gosto em Flutter?")

    assert [memory.content for memory in selection.memories] == [
        "Gosto de Flutter para aplicativos",
        "Gosto de Python e automação",
        "Trabalho profissionalmente com Flutter",
    ]
    assert "flutter" in selection.query_terms


def test_retriever_returns_empty_for_unrelated_or_meaningless_query() -> None:
    retriever = TextMemoryRetriever(Source([_memory("1", "Prefiro respostas diretas")]))

    assert retriever.retrieve("Olá").memories == ()
    assert retriever.retrieve("de e para").memories == ()


def test_retriever_limits_results() -> None:
    memories = [_memory(str(index), f"Projeto Aska item {index}") for index in range(5)]

    selection = TextMemoryRetriever(Source(memories), max_results=2).retrieve("projeto Aska")

    assert [memory.content for memory in selection.memories] == [
        "Projeto Aska item 0",
        "Projeto Aska item 1",
    ]


def test_retriever_explains_exact_plural_and_related_matches() -> None:
    memories = [
        _memory("1", "Prefiro aplicativos em Flutter"),
        _memory("2", "Gosto de trabalhar com Dart"),
    ]

    selection = TextMemoryRetriever(Source(memories)).retrieve(
        "Quais aplicativo uso para trabalhos?"
    )

    assert [match.memory.content for match in selection.matches] == [
        "Prefiro aplicativos em Flutter",
        "Gosto de trabalhar com Dart",
    ]
    assert selection.matches[0].matched_terms == ("aplicativo",)
    assert selection.matches[0].match_kinds == ("plural",)
    assert selection.matches[0].score == 2
    assert selection.matches[1].matched_terms == ("trabalhos",)
    assert selection.matches[1].match_kinds == ("related",)
    assert selection.matches[1].score == 1


def test_retriever_does_not_use_short_or_distant_prefixes() -> None:
    retriever = TextMemoryRetriever(Source([_memory("1", "Uso cartão diariamente")]))

    assert retriever.retrieve("Gosto de carros").memories == ()


@pytest.mark.parametrize(
    "message",
    [
        "Quais memórias você usou?",
        "Que memória foi utilizada?",
        "Memórias consideradas",
        "Por que você usou essa memória?",
        "Qual o motivo dessa memória?",
    ],
)
def test_detects_memory_usage_questions(message: str) -> None:
    assert is_memory_usage_question(message) is True
