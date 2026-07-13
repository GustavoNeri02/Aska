from pathlib import Path

import pytest

from packages.conversation import ConversationService, ConversationTurn, ModelProviderError
from packages.memory import (
    JsonMemoryDataSource,
    LocalMemoryRepository,
    MemoryService,
)


class RecordingProvider:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def generate(self, prompt: str) -> str:
        self.messages.append(prompt)
        return "resposta"


class FailingProvider:
    def generate(self, prompt: str) -> str:
        del prompt
        raise ModelProviderError("indisponível")


def test_conversation_builds_context_and_records_successful_turns(tmp_path: Path) -> None:
    provider = RecordingProvider()
    memory_service = MemoryService(
        LocalMemoryRepository(JsonMemoryDataSource(tmp_path / "memories.json"))
    )
    memory = memory_service.add("gosto de Python").memory
    assert memory is not None
    conversation = ConversationService(provider, memory_service)

    assert conversation.send("Olá") == "resposta"
    assert conversation.send("Continue") == "resposta"

    assert memory.content in provider.messages[0]
    assert memory.id not in provider.messages[0]
    assert "Histórico da sessão:" in provider.messages[1]
    assert conversation.history == [
        ConversationTurn("Olá", "resposta"),
        ConversationTurn("Continue", "resposta"),
    ]


def test_conversation_does_not_record_failed_generation(tmp_path: Path) -> None:
    memory_service = MemoryService(
        LocalMemoryRepository(JsonMemoryDataSource(tmp_path / "memories.json"))
    )
    conversation = ConversationService(FailingProvider(), memory_service)

    with pytest.raises(ModelProviderError):
        conversation.send("Olá")

    assert conversation.history == []
