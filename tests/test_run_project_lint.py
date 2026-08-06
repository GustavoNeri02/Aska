from pathlib import Path

from capabilities.terminal import (
    PROJECT_LINT_COMMAND,
    ProjectTestProcessResult,
    ProjectTestRunnerError,
    ProjectTestTimeoutError,
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


class FailingRunner:
    def __init__(self, error: Exception) -> None:
        self.error = error

    def run(self, workspace_root: Path, timeout_seconds: float) -> ProjectTestProcessResult:
        del workspace_root, timeout_seconds
        raise self.error


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


def test_lint_timeout_and_start_failure_are_distinct(tmp_path: Path) -> None:
    timed_out = RunProjectLintCapability(
        tmp_path.resolve(), FailingRunner(ProjectTestTimeoutError())
    )
    start_failed = RunProjectLintCapability(
        tmp_path.resolve(), FailingRunner(ProjectTestRunnerError())
    )

    assert timed_out.run(timed_out.prepare()).status is RunProjectLintStatus.TIMED_OUT
    assert start_failed.run(start_failed.prepare()).status is RunProjectLintStatus.START_FAILED


def test_lint_output_is_bounded(tmp_path: Path) -> None:
    capability = RunProjectLintCapability(
        tmp_path.resolve(),
        RecordingRunner(ProjectTestProcessResult(0, "abcdef", "uvwxyz")),
        max_output_chars=4,
    )

    result = capability.run(capability.prepare())

    assert result.stdout == "abcd"
    assert result.stderr == "uvwx"
    assert result.output_truncated is True
