from pathlib import Path

import pytest

from apps.cli.handlers import NaturalMemoryHandler
from packages.conversation import AddMemoryIntent, NameUpdateIntent
from tests.cli_support import FakeMemoryIntentInterpreter, create_temp_memory_service


def create_handler(
    tmp_path: Path,
    output: list[str],
    interpreter: FakeMemoryIntentInterpreter | None = None,
) -> NaturalMemoryHandler:
    return NaturalMemoryHandler(
        create_temp_memory_service(tmp_path),
        interpreter,
        output.append,
    )


def test_handle_consumes_proposal_confirmation_and_cancellation(tmp_path: Path) -> None:
    output: list[str] = []
    service = create_temp_memory_service(tmp_path)
    handler = NaturalMemoryHandler(service, None, output.append)

    assert handler.handle("Lembre que uso Flutter.") is True
    assert handler.handle("não") is True
    assert service.list() == []
    assert handler.handle("Lembre que uso Dart.") is True
    assert handler.handle("sim") is True
    assert [memory.content for memory in service.list()] == ["uso Dart."]


def test_handle_consumes_candidate_selection_error(tmp_path: Path) -> None:
    output: list[str] = []
    handler = create_handler(tmp_path, output)

    assert handler.handle("Remova a memória: inexistente") is True
    assert "Nenhuma memória correspondente foi encontrada." in output


def test_handle_returns_false_for_common_conversation(tmp_path: Path) -> None:
    assert create_handler(tmp_path, []).handle("Como vai?") is False


@pytest.mark.parametrize(
    "interpreter",
    [
        FakeMemoryIntentInterpreter(None),
        FakeMemoryIntentInterpreter(NameUpdateIntent("Gustavo Neri")),
    ],
)
def test_handle_returns_false_for_invalid_or_incompatible_interpretation(
    interpreter: FakeMemoryIntentInterpreter,
    tmp_path: Path,
) -> None:
    handler = create_handler(tmp_path, [], interpreter)

    assert handler.handle("Você pode memorizar que uso Flutter?") is False


def test_cancel_pending_for_literal_command_consumes_proposal(tmp_path: Path) -> None:
    output: list[str] = []
    service = create_temp_memory_service(tmp_path)
    handler = NaturalMemoryHandler(service, None, output.append)

    assert handler.handle("Guarde que uso Flutter.") is True
    assert handler.cancel_pending_for_literal_command() is True
    assert handler.cancel_pending_for_literal_command() is False
    assert handler.handle("sim") is False
    assert service.list() == []
    assert "Proposta de inclusão anterior cancelada." in output


def test_pending_proposal_executes_only_once(tmp_path: Path) -> None:
    service = create_temp_memory_service(tmp_path)
    handler = NaturalMemoryHandler(service, None, lambda message: None)

    assert handler.handle("Lembre que uso Flutter.") is True
    assert handler.handle("confirmo") is True
    assert handler.handle("confirmo") is False
    assert [memory.content for memory in service.list()] == ["uso Flutter."]


def test_handler_instances_do_not_share_pending_state(tmp_path: Path) -> None:
    service = create_temp_memory_service(tmp_path)
    first = NaturalMemoryHandler(service, None, lambda message: None)
    second = NaturalMemoryHandler(service, None, lambda message: None)

    assert first.handle("Lembre que uso Flutter.") is True
    assert second.handle("sim") is False
    assert service.list() == []
    assert first.handle("sim") is True
    assert [memory.content for memory in service.list()] == ["uso Flutter."]


def test_compatible_interpretation_is_consumed(tmp_path: Path) -> None:
    interpreter = FakeMemoryIntentInterpreter(AddMemoryIntent("Uso Flutter."))
    handler = create_handler(tmp_path, [], interpreter)

    assert handler.handle("Você pode memorizar que uso Flutter?") is True
