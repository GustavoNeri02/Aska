from pathlib import Path

from apps.cli.handlers import NaturalMemoryHandler
from packages.conversation import AddMemoryIntent
from tests.cli_support import FakeMemoryIntentInterpreter, create_temp_memory_service


def test_handler_returns_structured_proposal_and_confirmation_result(tmp_path: Path) -> None:
    service = create_temp_memory_service(tmp_path)
    handler = NaturalMemoryHandler(service, None)

    proposal = handler.handle("Lembre que uso Flutter.")
    result = handler.handle("confirmo")

    assert proposal is not None
    assert proposal.kind == "confirmation_required"
    assert proposal.facts == {"operation": "add", "content": "uso Flutter."}
    assert result is not None
    assert result.kind == "operation_completed"
    assert service.list()[0].content == "uso Flutter."


def test_handler_returns_none_for_common_conversation(tmp_path: Path) -> None:
    handler = NaturalMemoryHandler(create_temp_memory_service(tmp_path), None)

    assert handler.handle("Como vai?") is None


def test_handler_returns_structured_candidate_failure(tmp_path: Path) -> None:
    handler = NaturalMemoryHandler(create_temp_memory_service(tmp_path), None)

    result = handler.handle("Remova a memória: inexistente")

    assert result is not None
    assert result.kind == "candidate_selection_failed"
    assert result.facts["count"] == 0


def test_interpreted_add_returns_same_structured_proposal(tmp_path: Path) -> None:
    interpreter = FakeMemoryIntentInterpreter(AddMemoryIntent("Uso Flutter."))
    handler = NaturalMemoryHandler(create_temp_memory_service(tmp_path), interpreter)

    result = handler.handle("Você pode memorizar que uso Flutter?")

    assert result is not None
    assert result.facts == {"operation": "add", "content": "Uso Flutter."}


def test_pending_state_is_local_to_handler_instance(tmp_path: Path) -> None:
    service = create_temp_memory_service(tmp_path)
    first = NaturalMemoryHandler(service, None)
    second = NaturalMemoryHandler(service, None)

    first.handle("Lembre que uso Flutter.")

    assert second.handle("confirmo") is None
