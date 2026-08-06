from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Protocol

PROJECT_TEST_COMMAND = ("python", "-m", "pytest", "-q")


@dataclass(frozen=True, slots=True)
class ProjectTestTarget:
    workspace_root: Path
    device: int
    inode: int


@dataclass(frozen=True, slots=True)
class ProjectTestProcessResult:
    exit_code: int
    stdout: str
    stderr: str


class ProjectTestRunnerError(RuntimeError):
    """Raised when the fixed project-test process cannot be started."""


class ProjectTestTimeoutError(RuntimeError):
    """Raised when the fixed project-test process exceeds its timeout."""


class ProjectTestRunner(Protocol):
    def run(self, workspace_root: Path, timeout_seconds: float) -> ProjectTestProcessResult: ...


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
        try:
            resolved_root = workspace_root.resolve(strict=True)
        except OSError as error:
            raise ValueError("workspace_root must exist") from error
        if (
            not workspace_root.is_absolute()
            or workspace_root != resolved_root
            or not workspace_root.is_dir()
        ):
            raise ValueError("workspace_root must be an absolute resolved directory")
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
        stat = self._workspace_root.stat()
        return ProjectTestTarget(self._workspace_root, stat.st_dev, stat.st_ino)

    def run(self, target: ProjectTestTarget) -> RunProjectTestsResult:
        try:
            current = self.prepare()
        except OSError:
            return RunProjectTestsResult(RunProjectTestsStatus.TARGET_CHANGED)
        if current != target:
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

        stdout, stdout_truncated = self._truncate(process_result.stdout)
        stderr, stderr_truncated = self._truncate(process_result.stderr)
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

    def _truncate(self, output: str) -> tuple[str, bool]:
        if len(output) <= self._max_output_chars:
            return output, False
        return output[: self._max_output_chars], True
