from pathlib import Path

import pytest

from packages.conversation import (
    ConversationDecisionError,
    ConversationEvent,
    ConversationService,
    ModelRole,
    OpenWorkspaceLocationProposal,
    ReplyDecision,
    RunProjectTestsProposal,
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
    assert "rode o primeiro teste do projeto" in provider.messages[0][0].content
    assert "só pode executar a suíte inteira" in provider.messages[0][0].content
    assert provider.messages[0][-1].content == "Como você está?"


def test_decide_returns_proposal_without_recording_execution_as_history(
    tmp_path: Path,
) -> None:
    provider = FakeProvider(
        '{"type":"capability_proposal","action":"open_workspace_location","path":"docs"}'
    )
    service = ConversationService(provider, create_temp_memory_service(tmp_path))

    decision = service.decide("Queria ver a documentação em uma janela.")

    assert decision == OpenWorkspaceLocationProposal("docs")
    assert service.history == []
    assert len(provider.messages) == 1


def test_decide_returns_fixed_project_tests_proposal(tmp_path: Path) -> None:
    provider = FakeProvider('{"type":"capability_proposal","action":"run_project_tests"}')
    service = ConversationService(provider, create_temp_memory_service(tmp_path))

    decision = service.decide("Rode os testes do projeto.")

    assert decision == RunProjectTestsProposal()
    assert service.history == []


def test_reply_can_keep_a_typed_offer_for_the_next_turn(tmp_path: Path) -> None:
    provider = FakeProvider(
        '{"type":"reply","content":"Posso executar a suíte inteira.",'
        '"offer":{"action":"run_project_tests"}}'
    )
    service = ConversationService(provider, create_temp_memory_service(tmp_path))

    first = service.decide("Rode apenas o primeiro teste.")
    provider.response = '{"type":"capability_proposal","action":"run_project_tests"}'
    second = service.decide("Pode ser.")

    assert first == ReplyDecision("Posso executar a suíte inteira.", RunProjectTestsProposal())
    assert second == RunProjectTestsProposal()
    assert "Oferta tipada pendente" in provider.messages[1][0].content
    assert '"action": "run_project_tests"' in provider.messages[1][0].content


def test_external_event_is_presented_by_model_and_recorded_as_aska_reply(
    tmp_path: Path,
) -> None:
    provider = FakeProvider('{"type":"reply","content":"Tudo certo: os 507 testes passaram."}')
    service = ConversationService(provider, create_temp_memory_service(tmp_path))

    response = service.present_event(
        "Rode os testes.",
        ConversationEvent(
            domain="project_tests",
            kind="completed",
            facts={"exit_code": 0, "stdout": "507 passed", "stderr": ""},
        ),
    )

    assert response == "Tudo certo: os 507 testes passaram."
    assert service.history[0].assistant_message == response
    assert "evento local autoritativo" in provider.messages[0][0].content
    assert '"exit_code": 0' in provider.messages[0][-1].content


def test_external_event_discards_text_before_valid_reply_envelope(tmp_path: Path) -> None:
    provider = FakeProvider(
        "Vou pedir a confirmação novamente.\n\n"
        '{"type":"reply","content":"Por favor, confirme digitando sim."}'
    )
    service = ConversationService(provider, create_temp_memory_service(tmp_path))

    response = service.present_event(
        "siiiim",
        ConversationEvent(
            domain="project_tests",
            kind="confirmation_not_recognized",
            facts={},
        ),
    )

    assert response == "Por favor, confirme digitando sim."
    assert '{"type"' not in response


def test_decide_receives_existing_history_and_memories(tmp_path: Path) -> None:
    memory_service = create_temp_memory_service(tmp_path)
    memory_service.add("O projeto atual é o Aska")
    provider = FakeProvider("Resposta inicial")
    service = ConversationService(provider, memory_service)
    service.send("Estamos falando de docs", context_document=None)
    provider.response = (
        '{"type":"capability_proposal","action":"open_workspace_location","path":"docs"}'
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
