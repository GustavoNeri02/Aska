from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from capabilities.terminal.process import (
    FixedProcessError,
    FixedProcessRunner,
    FixedProcessTimeoutError,
)
from capabilities.terminal.project_tests import ProjectTestTarget

PROJECT_LINT_COMMAND = ("python", "-m", "ruff", "check", ".")


class RunProjectLintStatus(StrEnum):
    SUCCESS = "success"
    ISSUES_FOUND = "issues_found"
    TARGET_CHANGED = "target_changed"
    START_FAILED = "start_failed"
    TIMED_OUT = "timed_out"


@dataclass(frozen=True, slots=True)
class RunProjectLintResult:
    status: RunProjectLintStatus
    exit_code: int | None = None
    stdout: str = ""
    stderr: str = ""
    output_truncated: bool = False


class RunProjectLintCapability:
    def __init__(
        self,
        workspace_root: Path,
        runner: FixedProcessRunner,
        *,
        timeout_seconds: float = 120.0,
        max_output_chars: int = 32_768,
    ) -> None:
        resolved_root = workspace_root.resolve(strict=True)
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
        return PROJECT_LINT_COMMAND

    @property
    def timeout_seconds(self) -> float:
        return self._timeout_seconds

    def prepare(self) -> ProjectTestTarget:
        stat = self._workspace_root.stat()
        return ProjectTestTarget(self._workspace_root, stat.st_dev, stat.st_ino)

    def run(self, target: ProjectTestTarget) -> RunProjectLintResult:
        try:
            current = self.prepare()
        except OSError:
            return RunProjectLintResult(RunProjectLintStatus.TARGET_CHANGED)
        if current != target:
            return RunProjectLintResult(RunProjectLintStatus.TARGET_CHANGED)
        try:
            process = self._runner.run(target.workspace_root, self._timeout_seconds)
        except FixedProcessTimeoutError:
            return RunProjectLintResult(RunProjectLintStatus.TIMED_OUT)
        except FixedProcessError:
            return RunProjectLintResult(RunProjectLintStatus.START_FAILED)
        stdout = process.stdout[: self._max_output_chars]
        stderr = process.stderr[: self._max_output_chars]
        return RunProjectLintResult(
            RunProjectLintStatus.SUCCESS
            if process.exit_code == 0
            else RunProjectLintStatus.ISSUES_FOUND,
            process.exit_code,
            stdout,
            stderr,
            len(stdout) < len(process.stdout) or len(stderr) < len(process.stderr),
        )
