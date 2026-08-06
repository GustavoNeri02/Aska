from pathlib import Path

from capabilities.terminal import (
    PROJECT_LINT_COMMAND,
    ProjectTestProcessResult,
    RunProjectLintCapability,
    RunProjectLintStatus,
)


class RecordingRunner:
    def __init__(self, result: ProjectTestProcessResult) -> None:
        self.result = result
        self.calls: list[tuple[Path, float]] = []

    def run(self, workspace_root: Path, timeout_seconds: float) -> ProjectTestProcessResult:
        self.calls.append((workspace_root, timeout_seconds))
        return self.result


def test_lint_uses_fixed_command_and_reports_issues(tmp_path: Path) -> None:
    runner = RecordingRunner(ProjectTestProcessResult(1, "E501", ""))
    capability = RunProjectLintCapability(tmp_path.resolve(), runner, timeout_seconds=30)

    result = capability.run(capability.prepare())

    assert capability.command == PROJECT_LINT_COMMAND
    assert runner.calls == [(tmp_path.resolve(), 30)]
    assert result.status is RunProjectLintStatus.ISSUES_FOUND
    assert result.stdout == "E501"


def test_lint_rejects_changed_workspace(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    runner = RecordingRunner(ProjectTestProcessResult(0, "", ""))
    capability = RunProjectLintCapability(workspace.resolve(), runner)
    target = capability.prepare()
    workspace.rename(tmp_path / "old")
    workspace.mkdir()

    assert capability.run(target).status is RunProjectLintStatus.TARGET_CHANGED
    assert runner.calls == []
