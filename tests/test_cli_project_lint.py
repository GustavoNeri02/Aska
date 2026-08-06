from pathlib import Path

from apps.cli.app import run_conversation_loop
from apps.cli.handlers import NaturalProjectLintHandler
from capabilities.terminal import ProjectTestProcessResult, RunProjectLintCapability
from packages.conversation import RunProjectLintProposal
from tests.cli_support import FakeProvider, create_input_reader, create_temp_memory_service


class Runner:
    def __init__(self) -> None:
        self.calls = 0

    def run(self, workspace_root: Path, timeout_seconds: float) -> ProjectTestProcessResult:
        del workspace_root, timeout_seconds
        self.calls += 1
        return ProjectTestProcessResult(0, "All checks passed!", "")


def test_lint_requires_confirmation_and_preserves_request(tmp_path: Path) -> None:
    runner = Runner()
    handler = NaturalProjectLintHandler(RunProjectLintCapability(tmp_path.resolve(), runner))

    proposal = handler.handle_proposal(RunProjectLintProposal(), "rode o Ruff")
    result = handler.handle("sim")

    assert proposal.facts["command"] == ("python", "-m", "ruff", "check", ".")
    assert runner.calls == 1
    assert result is not None
    assert result.facts["status"] == "success"
    assert result.original_request == "rode o Ruff"


def test_explicit_lint_request_bypasses_model_decision(tmp_path: Path) -> None:
    runner = Runner()
    provider = FakeProvider('{"type":"reply","content":"Posso executar. Confirma?"}')

    run_conversation_loop(
        provider,
        create_temp_memory_service(tmp_path),
        project_lint_capability=RunProjectLintCapability(tmp_path.resolve(), runner),
        input_reader=create_input_reader(["rode o Ruff no projeto", "sair"]),
        output_writer=lambda _: None,
    )

    assert len(provider.messages) == 1
    assert '"kind": "confirmation_required"' in provider.messages[0][-1].content
    assert runner.calls == 0
