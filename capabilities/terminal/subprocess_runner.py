import subprocess
import sys
from pathlib import Path

from capabilities.terminal.project_tests import (
    PROJECT_TEST_COMMAND,
    ProjectTestProcessResult,
    ProjectTestRunnerError,
    ProjectTestTimeoutError,
)


class PythonProjectTestRunner:
    def __init__(self, executable: Path | None = None) -> None:
        candidate = executable or Path(sys.executable)
        try:
            resolved_executable = candidate.resolve(strict=True)
        except OSError as error:
            raise ValueError("Python executable must exist") from error
        if not resolved_executable.is_file():
            raise ValueError("Python executable must be a file")
        self._executable = resolved_executable

    def run(
        self,
        workspace_root: Path,
        timeout_seconds: float,
    ) -> ProjectTestProcessResult:
        command = [str(self._executable), *PROJECT_TEST_COMMAND[1:]]
        try:
            completed = subprocess.run(
                command,
                cwd=workspace_root,
                shell=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired as error:
            raise ProjectTestTimeoutError("project tests timed out") from error
        except OSError as error:
            raise ProjectTestRunnerError("project tests could not start") from error
        return ProjectTestProcessResult(
            completed.returncode,
            completed.stdout,
            completed.stderr,
        )
