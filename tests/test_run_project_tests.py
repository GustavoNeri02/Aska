import subprocess
import sys
from pathlib import Path

import pytest

from capabilities.terminal import (
    PROJECT_TEST_COMMAND,
    ProjectTestProcessResult,
    ProjectTestRunnerError,
    ProjectTestTimeoutError,
    PythonProjectTestRunner,
    RunProjectTestsCapability,
    RunProjectTestsStatus,
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


def test_project_tests_use_fixed_operation_and_workspace(tmp_path: Path) -> None:
    runner = RecordingRunner(ProjectTestProcessResult(0, "2 passed", ""))
    capability = RunProjectTestsCapability(tmp_path.resolve(), runner, timeout_seconds=30)
    target = capability.prepare()

    result = capability.run(target)

    assert capability.command == PROJECT_TEST_COMMAND
    assert runner.calls == [(tmp_path.resolve(), 30)]
    assert result.status is RunProjectTestsStatus.SUCCESS
    assert result.exit_code == 0
    assert result.stdout == "2 passed"


def test_nonzero_exit_is_a_real_test_failure(tmp_path: Path) -> None:
    capability = RunProjectTestsCapability(
        tmp_path.resolve(),
        RecordingRunner(ProjectTestProcessResult(1, "1 failed", "trace")),
    )

    result = capability.run(capability.prepare())

    assert result.status is RunProjectTestsStatus.TESTS_FAILED
    assert result.exit_code == 1
    assert result.stderr == "trace"


def test_changed_workspace_is_not_executed(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    runner = RecordingRunner(ProjectTestProcessResult(0, "", ""))
    capability = RunProjectTestsCapability(workspace.resolve(), runner)
    target = capability.prepare()
    workspace.rename(tmp_path / "old-workspace")
    workspace.mkdir()

    result = capability.run(target)

    assert result.status is RunProjectTestsStatus.TARGET_CHANGED
    assert runner.calls == []


def test_timeout_and_start_failure_are_distinct(tmp_path: Path) -> None:
    timed_out = RunProjectTestsCapability(
        tmp_path.resolve(), FailingRunner(ProjectTestTimeoutError())
    )
    start_failed = RunProjectTestsCapability(
        tmp_path.resolve(), FailingRunner(ProjectTestRunnerError())
    )

    assert timed_out.run(timed_out.prepare()).status is RunProjectTestsStatus.TIMED_OUT
    assert start_failed.run(start_failed.prepare()).status is RunProjectTestsStatus.START_FAILED


def test_process_output_is_bounded(tmp_path: Path) -> None:
    capability = RunProjectTestsCapability(
        tmp_path.resolve(),
        RecordingRunner(ProjectTestProcessResult(0, "abcdef", "uvwxyz")),
        max_output_chars=4,
    )

    result = capability.run(capability.prepare())

    assert result.stdout == "abcd"
    assert result.stderr == "uvwx"
    assert result.output_truncated is True


def test_python_runner_uses_separate_argv_without_shell(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        captured["command"] = command
        captured.update(kwargs)
        return subprocess.CompletedProcess(command, 0, "passed", "")

    monkeypatch.setattr("capabilities.terminal.subprocess_runner.subprocess.run", fake_run)
    runner = PythonProjectTestRunner(Path(sys.executable).resolve())

    result = runner.run(tmp_path.resolve(), 15)

    assert captured["command"] == [
        str(Path(sys.executable).resolve()),
        "-m",
        "pytest",
        "-q",
    ]
    assert captured["cwd"] == tmp_path.resolve()
    assert captured["shell"] is False
    assert captured["timeout"] == 15
    assert result == ProjectTestProcessResult(0, "passed", "")
