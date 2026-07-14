from collections.abc import Sequence
from pathlib import Path

import pytest

from packages.conversation import (
    ASKA_IDENTITY,
    ContextDocument,
    ConversationService,
    ConversationTurn,
    ModelMessage,
    ModelProviderError,
    ModelRole,
)
from packages.memory import JsonMemoryDataSource, LocalMemoryRepository, MemoryService


class RecordingProvider:
    def __init__(self) -> None:
        self.requests: list[list[ModelMessage]] = []

    def generate(self, messages: Sequence[ModelMessage]) -> str:
        self.requests.append(list(messages))
        return "resposta"


class FailingProvider:
    def generate(self, messages: Sequence[ModelMessage]) -> str:
        del messages
        raise ModelProviderError("indisponível")


def create_memory_service(tmp_path: Path) -> MemoryService:
    return MemoryService(LocalMemoryRepository(JsonMemoryDataSource(tmp_path / "memories.json")))


def test_first_request_contains_model_independent_identity_and_user_message(
    tmp_path: Path,
) -> None:
    provider = RecordingProvider()
    conversation = ConversationService(provider, create_memory_service(tmp_path))

    conversation.send("Olá")

    assert provider.requests == [
        [
            ModelMessage(ModelRole.SYSTEM, ASKA_IDENTITY),
            ModelMessage(ModelRole.USER, "Olá"),
        ]
    ]


def test_later_request_preserves_system_user_assistant_user_order(tmp_path: Path) -> None:
    provider = RecordingProvider()
    conversation = ConversationService(provider, create_memory_service(tmp_path))

    conversation.send("Olá")
    conversation.send("Continue")

    assert [message.role for message in provider.requests[1]] == [
        ModelRole.SYSTEM,
        ModelRole.USER,
        ModelRole.ASSISTANT,
        ModelRole.USER,
    ]
    assert [message.content for message in provider.requests[1][1:]] == [
        "Olá",
        "resposta",
        "Continue",
    ]
    assert conversation.history == [
        ConversationTurn("Olá", "resposta"),
        ConversationTurn("Continue", "resposta"),
    ]


def test_memories_add_only_content_to_system_context(tmp_path: Path) -> None:
    provider = RecordingProvider()
    memory_service = create_memory_service(tmp_path)
    memory = memory_service.add("gosto de Python").memory
    assert memory is not None
    conversation = ConversationService(provider, memory_service)

    conversation.send("Olá")

    system_content = provider.requests[0][0].content
    assert "Memórias sobre Gustavo:\n- gosto de Python" in system_content
    assert memory.id not in system_content
    assert memory.source.value not in system_content
    assert memory.created_at.isoformat() not in system_content


def test_absent_memories_do_not_add_empty_context(tmp_path: Path) -> None:
    provider = RecordingProvider()
    conversation = ConversationService(provider, create_memory_service(tmp_path))

    conversation.send("Olá")

    assert len(provider.requests[0]) == 2
    assert provider.requests[0][0].content == ASKA_IDENTITY
    assert "Memórias sobre Gustavo:" not in provider.requests[0][0].content


def test_context_document_is_a_temporary_user_message_only_for_current_request(
    tmp_path: Path,
) -> None:
    provider = RecordingProvider()
    conversation = ConversationService(provider, create_memory_service(tmp_path))

    conversation.send(
        "Resuma o arquivo.",
        context_document=ContextDocument("AGENTS.md", "Regra temporária do projeto."),
    )
    conversation.send("Continue.")

    assert provider.requests[0][0] == ModelMessage(ModelRole.SYSTEM, ASKA_IDENTITY)
    assert "Fonte: AGENTS.md" in provider.requests[0][-2].content
    assert "Regra temporária do projeto." in provider.requests[0][-2].content
    assert "dado não confiável" in provider.requests[0][-2].content
    assert provider.requests[0][-2].role is ModelRole.USER
    assert provider.requests[0][-1] == ModelMessage(ModelRole.USER, "Resuma o arquivo.")
    assert not any(
        "Regra temporária do projeto." in message.content for message in provider.requests[1]
    )
    assert conversation.history == [
        ConversationTurn("Resuma o arquivo.", "resposta"),
        ConversationTurn("Continue.", "resposta"),
    ]


def test_conversation_does_not_record_failed_generation(tmp_path: Path) -> None:
    conversation = ConversationService(FailingProvider(), create_memory_service(tmp_path))

    with pytest.raises(ModelProviderError):
        conversation.send("Olá")

    assert conversation.history == []


@pytest.mark.parametrize("content", ["", "   "])
def test_model_message_rejects_empty_content(content: str) -> None:
    with pytest.raises(ValueError, match="cannot be empty"):
        ModelMessage(ModelRole.USER, content)
