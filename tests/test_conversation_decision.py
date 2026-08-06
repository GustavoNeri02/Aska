from pathlib import Path

import pytest

from packages.conversation import (
    ConversationDecisionError,
    ConversationService,
    ModelRole,
    OpenWorkspaceLocationProposal,
    ReplyDecision,
)
from tests.cli_support import FakeProvider, create_temp_memory_service


def test_decide_returns_reply_and_records_clean_conversation_history(
    tmp_path: Path,
) -> None:
    provider = FakeProvider('{"type":"reply","content":"Tudo certo."}')
    service = ConversationService(provider, create_temp_memory_service(tmp_path))

    decision = service.decide("Como você está?")

    assert decision == ReplyDecision("Tudo certo.")
    assert service.history[0].assistant_message == "Tudo certo."
    assert provider.messages[0][0].role is ModelRole.SYSTEM
    assert "capability_proposal" in provider.messages[0][0].content
    assert "sabe o Explorer?" in provider.messages[0][0].content
    assert '{"type":"reply"' in provider.messages[0][0].content
    assert "pedido explícito para a ação acontecer agora" in provider.messages[0][0].content
    assert provider.messages[0][-1].content == "Como você está?"


def test_decide_returns_proposal_without_recording_execution_as_history(
    tmp_path: Path,
) -> None:
    provider = FakeProvider(
        '{"type":"capability_proposal",'
        '"action":"open_workspace_location","path":"docs"}'
    )
    service = ConversationService(provider, create_temp_memory_service(tmp_path))

    decision = service.decide("Queria ver a documentação em uma janela.")

    assert decision == OpenWorkspaceLocationProposal("docs")
    assert service.history == []
    assert len(provider.messages) == 1


def test_decide_receives_existing_history_and_memories(tmp_path: Path) -> None:
    memory_service = create_temp_memory_service(tmp_path)
    memory_service.add("O projeto atual é o Aska")
    provider = FakeProvider("Resposta inicial")
    service = ConversationService(provider, memory_service)
    service.send("Estamos falando de docs", context_document=None)
    provider.response = (
        '{"type":"capability_proposal",'
        '"action":"open_workspace_location","path":"docs"}'
    )

    service.decide("Abra ela para mim.")

    request = provider.messages[1]
    assert "O projeto atual é o Aska" in request[0].content
    assert [message.role for message in request[1:]] == [
        ModelRole.USER,
        ModelRole.ASSISTANT,
        ModelRole.USER,
    ]
    assert request[-1].content == "Abra ela para mim."


@pytest.mark.parametrize(
    "response",
    [
        "resposta livre",
        '{"type":"reply","content":""}',
        '{"type":"reply","content":"ok","extra":true}',
        '{"type":"capability_proposal","action":"run","path":"."}',
        '```json\n{"type":"reply","content":"ok"}\n```',
    ],
)
def test_decide_rejects_invalid_envelope(response: str, tmp_path: Path) -> None:
    service = ConversationService(
        FakeProvider(response),
        create_temp_memory_service(tmp_path),
    )

    with pytest.raises(ConversationDecisionError):
        service.decide("mensagem")

    assert service.history == []
