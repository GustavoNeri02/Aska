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


@pytest.mark.parametrize(
    "message",
    ["Quais memórias você usou?", "Que memória foi utilizada?", "Memórias consideradas"],
)
def test_detects_memory_usage_questions(message: str) -> None:
    assert is_memory_usage_question(message) is True
