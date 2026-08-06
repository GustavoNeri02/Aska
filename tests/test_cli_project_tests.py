from collections.abc import Sequence
from pathlib import Path

from apps.cli.app import run_conversation_loop
from apps.cli.handlers import NaturalProjectTestsHandler
from capabilities.terminal import (
    ProjectTestProcessResult,
    RunProjectTestsCapability,
)
from packages.conversation import (
    ConversationService,
    ModelMessage,
    ModelRole,
    RunProjectTestsProposal,
)
from tests.cli_support import FakeProvider, create_input_reader, create_temp_memory_service


class RecordingRunner:
    def __init__(self, result: ProjectTestProcessResult) -> None:
        self.result = result
        self.calls: list[tuple[Path, float]] = []

    def run(self, workspace_root: Path, timeout_seconds: float) -> ProjectTestProcessResult:
        self.calls.append((workspace_root, timeout_seconds))
        return self.result


class SequencedProvider:
    def __init__(self, responses: list[str]) -> None:
        self._responses = iter(responses)
        self.messages: list[list[ModelMessage]] = []

    def generate(self, messages: Sequence[ModelMessage]) -> str:
        self.messages.append(list(messages))
        return next(self._responses)


def _create_handler(
    tmp_path: Path,
    result: ProjectTestProcessResult | None = None,
) -> tuple[NaturalProjectTestsHandler, RecordingRunner, list[str]]:
    runner = RecordingRunner(result or ProjectTestProcessResult(0, "2 passed", ""))
    output: list[str] = []
    conversation_service = ConversationService(
        FakeProvider(),
        create_temp_memory_service(tmp_path),
    )
    handler = NaturalProjectTestsHandler(
        RunProjectTestsCapability(tmp_path.resolve(), runner, timeout_seconds=30),
        conversation_service,
        output.append,
    )
    return handler, runner, output


def test_project_tests_require_confirmation_and_show_fixed_operation(
    tmp_path: Path,
) -> None:
    handler, runner, output = _create_handler(tmp_path)

    handler.handle_proposal(RunProjectTestsProposal(), "Rode os testes.")

    assert runner.calls == []
    assert "Comando fixo: python -m pytest -q" in output[-1]
    assert f"Diretório: {tmp_path.resolve()}" in output[-1]

    handler.handle("sim")

    assert runner.calls == [(tmp_path.resolve(), 30)]
    assert "Testes concluídos com sucesso." in output[-1]
    assert "2 passed" in output[-1]


def test_project_tests_can_be_cancelled(tmp_path: Path) -> None:
    handler, runner, output = _create_handler(tmp_path)

    handler.handle_proposal(RunProjectTestsProposal(), "Rode os testes.")
    handler.handle("naum")

    assert runner.calls == []
    assert output[-1] == "Execução dos testes cancelada."


def test_failed_tests_report_real_exit_code_and_output(tmp_path: Path) -> None:
    handler, _, output = _create_handler(
        tmp_path,
        ProjectTestProcessResult(1, "1 failed", "failure detail"),
    )

    handler.handle_proposal(RunProjectTestsProposal(), "Rode os testes.")
    handler.handle("sim")

    assert "houve falhas" in output[-1]
    assert "Exit code: 1" in output[-1]
    assert "failure detail" in output[-1]


def test_large_result_is_compacted_only_in_conversation_history(tmp_path: Path) -> None:
    long_output = f"start-{'x' * 5000}-end"
    runner = RecordingRunner(ProjectTestProcessResult(1, long_output, ""))
    conversation_service = ConversationService(
        FakeProvider(),
        create_temp_memory_service(tmp_path),
    )
    displayed: list[str] = []
    handler = NaturalProjectTestsHandler(
        RunProjectTestsCapability(tmp_path.resolve(), runner, max_output_chars=10_000),
        conversation_service,
        displayed.append,
    )

    handler.handle_proposal(RunProjectTestsProposal(), "Rode os testes.")
    handler.handle("sim")

    assert long_output in displayed[-1]
    history_result = conversation_service.history[-1].assistant_message
    assert len(history_result) <= 4096
    assert "resultado compactado" in history_result
    assert "start-" in history_result
    assert "-end" in history_result


def test_conversation_loop_routes_project_tests_with_one_model_call(
    tmp_path: Path,
) -> None:
    runner = RecordingRunner(ProjectTestProcessResult(0, "504 passed", ""))
    capability = RunProjectTestsCapability(tmp_path.resolve(), runner)
    provider = FakeProvider(
        '{"type":"capability_proposal","action":"run_project_tests"}'
    )
    output: list[str] = []

    run_conversation_loop(
        provider,
        create_temp_memory_service(tmp_path),
        project_tests_capability=capability,
        input_reader=create_input_reader(["Rode os testes.", "sim", "sair"]),
        output_writer=output.append,
    )

    assert len(provider.messages) == 1
    assert len(runner.calls) == 1
    assert any("504 passed" in message for message in output)


def test_follow_up_receives_real_project_test_result_in_history(tmp_path: Path) -> None:
    runner = RecordingRunner(ProjectTestProcessResult(0, "504 passed", ""))
    provider = SequencedProvider(
        [
            '{"type":"capability_proposal","action":"run_project_tests"}',
            '{"type":"reply","content":"Os 504 testes passaram."}',
        ]
    )
    output: list[str] = []

    run_conversation_loop(
        provider,
        create_temp_memory_service(tmp_path),
        project_tests_capability=RunProjectTestsCapability(tmp_path.resolve(), runner),
        input_reader=create_input_reader(
            ["Rode os testes do projeto.", "sim", "O que me retornou?", "sair"]
        ),
        output_writer=output.append,
    )

    follow_up_request = provider.messages[1]
    assert [message.role for message in follow_up_request[1:]] == [
        ModelRole.USER,
        ModelRole.ASSISTANT,
        ModelRole.USER,
    ]
    assert follow_up_request[1].content == "Rode os testes do projeto."
    assert "504 passed" in follow_up_request[2].content
    assert "Aska > Os 504 testes passaram." in output
