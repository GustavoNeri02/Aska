from collections.abc import Sequence
from pathlib import Path

from apps.cli.app import run_conversation_loop
from capabilities.terminal import ProjectTestProcessResult, RunProjectLintCapability
from packages.conversation import AddMemoryIntent, EditMemoryIntent, ModelMessage
from tests.cli_support import (
    FakeMemoryIntentInterpreter,
    FakeProvider,
    create_input_reader,
    create_temp_memory_service,
)


class SequencedProvider:
    def __init__(self, responses: list[str]) -> None:
        self._responses = iter(responses)
        self.messages: list[list[ModelMessage]] = []

    def generate(self, messages: Sequence[ModelMessage]) -> str:
        self.messages.append(list(messages))
        return next(self._responses)


def test_literal_memory_result_is_presented_by_model(tmp_path: Path) -> None:
    provider = FakeProvider('{"type":"reply","content":"Guardei essa memória."}')
    output: list[str] = []
    service = create_temp_memory_service(tmp_path)

    run_conversation_loop(
        provider,
        service,
        input_reader=create_input_reader(["lembrar: gosto de Python", "sair"]),
        output_writer=output.append,
    )

    assert service.list()[0].content == "gosto de Python"
    assert "Aska > Guardei essa memória." in output
    assert '"status": "added"' in provider.messages[0][-1].content


def test_memory_listing_is_sent_as_structured_facts(tmp_path: Path) -> None:
    service = create_temp_memory_service(tmp_path)
    service.add("Uso Flutter")
    provider = FakeProvider('{"type":"reply","content":"Você usa Flutter."}')

    run_conversation_loop(
        provider,
        service,
        input_reader=create_input_reader(["memórias", "sair"]),
        output_writer=lambda _: None,
    )

    assert '"memories": ["Uso Flutter"]' in provider.messages[0][-1].content


def test_natural_add_requires_confirmation_and_executes_once(tmp_path: Path) -> None:
    service = create_temp_memory_service(tmp_path)
    interpreter = FakeMemoryIntentInterpreter(AddMemoryIntent("Uso Flutter"))
    provider = SequencedProvider(
        [
            '{"type":"event_reply","acknowledged_domain":"memory",'
            '"acknowledged_kind":"confirmation_required","content":"Confirma?"}',
            '{"type":"reply","content":"Tudo certo."}',
        ]
    )

    run_conversation_loop(
        provider,
        service,
        memory_intent_interpreter=interpreter,
        input_reader=create_input_reader(["Guarde que uso Flutter", "sim", "sair"]),
        output_writer=lambda _: None,
    )

    assert [memory.content for memory in service.list()] == ["uso Flutter"]
    assert '"kind": "confirmation_required"' in provider.messages[0][-1].content
    assert '"kind": "operation_completed"' in provider.messages[1][-1].content
    assert "Pedido original: Guarde que uso Flutter" in provider.messages[1][-1].content


def test_natural_memory_cancellation_has_no_effect(tmp_path: Path) -> None:
    service = create_temp_memory_service(tmp_path)
    interpreter = FakeMemoryIntentInterpreter(AddMemoryIntent("Uso Flutter"))
    provider = SequencedProvider(
        [
            '{"type":"event_reply","acknowledged_domain":"memory",'
            '"acknowledged_kind":"confirmation_required","content":"Confirma?"}',
            '{"type":"reply","content":"Cancelei."}',
        ]
    )

    run_conversation_loop(
        provider,
        service,
        memory_intent_interpreter=interpreter,
        input_reader=create_input_reader(["Guarde que uso Flutter", "não", "sair"]),
        output_writer=lambda _: None,
    )

    assert service.list() == []
    assert '"kind": "proposal_cancelled"' in provider.messages[1][-1].content


def test_memory_edit_snapshot_conflict_is_reported_as_fact(tmp_path: Path) -> None:
    service = create_temp_memory_service(tmp_path)
    original = service.add("Uso Flutter").memory
    assert original is not None
    interpreter = FakeMemoryIntentInterpreter(EditMemoryIntent("Flutter", "Uso Python"))
    provider = SequencedProvider(
        [
            '{"type":"event_reply","acknowledged_domain":"memory",'
            '"acknowledged_kind":"confirmation_required","content":"Confirma?"}',
            '{"type":"reply","content":"A memória mudou."}',
        ]
    )
    messages = iter(["Atualize a memória", "sim", "sair"])

    def input_reader(_: str) -> str:
        message = next(messages)
        if message == "sim":
            service.edit(original.content, "Uso Dart")
        return message

    run_conversation_loop(
        provider,
        service,
        memory_intent_interpreter=interpreter,
        input_reader=input_reader,
        output_writer=lambda _: None,
    )

    assert service.list()[0].content == "Uso Dart"
    assert '"status": "conflict"' in provider.messages[1][-1].content


def test_literal_memory_command_records_cancelled_pending_action(tmp_path: Path) -> None:
    class Runner:
        def run(self, workspace_root: Path, timeout_seconds: float) -> ProjectTestProcessResult:
            del workspace_root, timeout_seconds
            return ProjectTestProcessResult(0, "", "")

    provider = SequencedProvider(
        [
            '{"type":"event_reply","acknowledged_domain":"project_lint",'
            '"acknowledged_kind":"confirmation_required","content":"Confirma?"}',
            "Listei.",
        ]
    )

    run_conversation_loop(
        provider,
        create_temp_memory_service(tmp_path),
        project_lint_capability=RunProjectLintCapability(tmp_path.resolve(), Runner()),
        input_reader=create_input_reader(["rode o Ruff", "memórias", "sair"]),
        output_writer=lambda _: None,
    )

    assert '"cancelled_operations": ["run_project_lint"]' in provider.messages[1][-1].content
