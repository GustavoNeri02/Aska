from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from capabilities.terminal.process import (
    FixedProcessError,
    FixedProcessResult,
    FixedProcessRunner,
    FixedProcessTimeoutError,
    FixedWorkspaceTarget,
    snapshot_workspace,
    truncate_output,
    validate_workspace_root,
    workspace_target_is_current,
)

PROJECT_TEST_COMMAND = ("python", "-m", "pytest", "-q")


ProjectTestTarget = FixedWorkspaceTarget


ProjectTestProcessResult = FixedProcessResult
ProjectTestRunnerError = FixedProcessError
ProjectTestTimeoutError = FixedProcessTimeoutError
ProjectTestRunner = FixedProcessRunner


class RunProjectTestsStatus(StrEnum):
    SUCCESS = "success"
    TESTS_FAILED = "tests_failed"
    TARGET_CHANGED = "target_changed"
    START_FAILED = "start_failed"
    TIMED_OUT = "timed_out"


@dataclass(frozen=True, slots=True)
class RunProjectTestsResult:
    status: RunProjectTestsStatus
    exit_code: int | None = None
    stdout: str = ""
    stderr: str = ""
    output_truncated: bool = False


class RunProjectTestsCapability:
    def __init__(
        self,
        workspace_root: Path,
        runner: ProjectTestRunner,
        *,
        timeout_seconds: float = 120.0,
        max_output_chars: int = 32_768,
    ) -> None:
        validate_workspace_root(workspace_root)
        if timeout_seconds <= 0 or timeout_seconds > 900:
            raise ValueError("timeout_seconds must be between 0 and 900")
        if max_output_chars <= 0 or max_output_chars > 262_144:
            raise ValueError("max_output_chars must be between 1 and 262144")
        self._workspace_root = workspace_root
        self._runner = runner
        self._timeout_seconds = timeout_seconds
        self._max_output_chars = max_output_chars

    @property
    def command(self) -> tuple[str, ...]:
        return PROJECT_TEST_COMMAND

    @property
    def timeout_seconds(self) -> float:
        return self._timeout_seconds

    def prepare(self) -> ProjectTestTarget:
        return snapshot_workspace(self._workspace_root)

    def run(self, target: ProjectTestTarget) -> RunProjectTestsResult:
        try:
            target_is_current = workspace_target_is_current(self._workspace_root, target)
        except OSError:
            return RunProjectTestsResult(RunProjectTestsStatus.TARGET_CHANGED)
        if not target_is_current:
            return RunProjectTestsResult(RunProjectTestsStatus.TARGET_CHANGED)
        try:
            process_result = self._runner.run(
                target.workspace_root,
                self._timeout_seconds,
            )
        except ProjectTestTimeoutError:
            return RunProjectTestsResult(RunProjectTestsStatus.TIMED_OUT)
        except ProjectTestRunnerError:
            return RunProjectTestsResult(RunProjectTestsStatus.START_FAILED)

        stdout, stdout_truncated = truncate_output(process_result.stdout, self._max_output_chars)
        stderr, stderr_truncated = truncate_output(process_result.stderr, self._max_output_chars)
        status = (
            RunProjectTestsStatus.SUCCESS
            if process_result.exit_code == 0
            else RunProjectTestsStatus.TESTS_FAILED
        )
        return RunProjectTestsResult(
            status,
            exit_code=process_result.exit_code,
            stdout=stdout,
            stderr=stderr,
            output_truncated=stdout_truncated or stderr_truncated,
        )
