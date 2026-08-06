from collections.abc import Sequence
from pathlib import Path

from apps.cli.app import run_conversation_loop
from apps.cli.handlers import NaturalProjectTestsHandler
from capabilities.terminal import (
    ProjectTestProcessResult,
    RunProjectTestsCapability,
)
from packages.conversation import ModelMessage, ModelRole, RunProjectTestsProposal
from tests.cli_support import create_input_reader, create_temp_memory_service


class SequencedProvider:
    def __init__(self, responses: list[str]) -> None:
        self._responses = iter(responses)
        self.messages: list[list[ModelMessage]] = []

    def generate(self, messages: Sequence[ModelMessage]) -> str:
        self.messages.append(list(messages))
        return next(self._responses)


class RecordingRunner:
    def __init__(self, result: ProjectTestProcessResult | None = None) -> None:
        self.result = result or ProjectTestProcessResult(0, "2 passed", "")
        self.calls: list[tuple[Path, float]] = []

    def run(self, workspace_root: Path, timeout_seconds: float) -> ProjectTestProcessResult:
        self.calls.append((workspace_root, timeout_seconds))
        return self.result


def _handler(tmp_path: Path, runner: RecordingRunner) -> NaturalProjectTestsHandler:
    capability = RunProjectTestsCapability(tmp_path.resolve(), runner, timeout_seconds=30)
    return NaturalProjectTestsHandler(capability)


def test_project_tests_return_fixed_structured_proposal(tmp_path: Path) -> None:
    runner = RecordingRunner()
    handler = _handler(tmp_path, runner)

    result = handler.handle_proposal(RunProjectTestsProposal(), "rode os testes")

    assert result.kind == "confirmation_required"
    assert result.facts["command"] == ("python", "-m", "pytest", "-q")
    assert result.facts["directory"] == str(tmp_path.resolve())
    assert runner.calls == []


def test_project_tests_execute_only_after_confirmation(tmp_path: Path) -> None:
    runner = RecordingRunner()
    handler = _handler(tmp_path, runner)
    handler.handle_proposal(RunProjectTestsProposal(), "rode os testes")

    result = handler.handle("sim")

    assert result is not None
    assert result.kind == "completed"
    assert result.facts["status"] == "success"
    assert result.facts["stdout"] == "2 passed"
    assert result.original_request == "rode os testes"
    assert runner.calls == [(tmp_path.resolve(), 30)]


def test_project_tests_can_be_cancelled(tmp_path: Path) -> None:
    runner = RecordingRunner()
    handler = _handler(tmp_path, runner)
    handler.handle_proposal(RunProjectTestsProposal(), "rode os testes")

    result = handler.handle("não")

    assert result is not None
    assert result.kind == "cancelled"
    assert runner.calls == []


def test_project_test_failure_keeps_real_process_facts(tmp_path: Path) -> None:
    runner = RecordingRunner(ProjectTestProcessResult(1, "1 failed", "detail"))
    handler = _handler(tmp_path, runner)
    handler.handle_proposal(RunProjectTestsProposal(), "rode os testes")

    result = handler.handle("sim")

    assert result is not None
    assert result.facts["status"] == "tests_failed"
    assert result.facts["exit_code"] == 1
    assert result.facts["stderr"] == "detail"


def test_confirmation_and_original_request_are_preserved_in_history(tmp_path: Path) -> None:
    runner = RecordingRunner(ProjectTestProcessResult(0, "504 passed", ""))
    provider = SequencedProvider(
        [
            '{"type":"capability_proposal","action":"run_project_tests"}',
            '{"type":"event_reply","acknowledged_domain":"project_tests",'
            '"acknowledged_kind":"confirmation_required",'
            '"content":"Posso rodar a suíte inteira. Confirma?"}',
            '{"type":"event_reply","acknowledged_domain":"project_tests",'
            '"acknowledged_kind":"completed","acknowledged_status":"success",'
            '"content":"A suíte terminou: 504 passaram."}',
            '{"type":"reply","content":"Os 504 testes passaram."}',
        ]
    )

    run_conversation_loop(
        provider,
        create_temp_memory_service(tmp_path),
        project_tests_capability=RunProjectTestsCapability(tmp_path.resolve(), runner),
        input_reader=create_input_reader(
            ["Rode os testes do projeto.", "sim", "O que me retornou?", "sair"]
        ),
        output_writer=lambda _: None,
    )

    completion_event = provider.messages[2][-1].content
    assert "Pedido original: Rode os testes do projeto." in completion_event
    follow_up = provider.messages[3]
    assert [message.role for message in follow_up[1:]] == [
        ModelRole.USER,
        ModelRole.ASSISTANT,
        ModelRole.USER,
        ModelRole.ASSISTANT,
        ModelRole.USER,
    ]
    assert [message.content for message in follow_up[1::2]] == [
        "Rode os testes do projeto.",
        "sim",
        "O que me retornou?",
    ]
    assert "504 passed" in follow_up[4].content
