import subprocess
import sys
from pathlib import Path

from capabilities.terminal.process import (
    FixedProcessError,
    FixedProcessResult,
    FixedProcessTimeoutError,
)
from capabilities.terminal.project_tests import (
    PROJECT_TEST_COMMAND,
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
    ) -> FixedProcessResult:
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
            raise FixedProcessTimeoutError("project tests timed out") from error
        except OSError as error:
            raise FixedProcessError("project tests could not start") from error
        return FixedProcessResult(
            completed.returncode,
            completed.stdout,
            completed.stderr,
        )


class PythonModuleRunner:
    def __init__(
        self, module: str, arguments: tuple[str, ...], executable: Path | None = None
    ) -> None:
        if not module or not module.isidentifier():
            raise ValueError("module must be a Python identifier")
        candidate = executable or Path(sys.executable)
        try:
            self._executable = candidate.resolve(strict=True)
        except OSError as error:
            raise ValueError("Python executable must exist") from error
        if not self._executable.is_file():
            raise ValueError("Python executable must be a file")
        self._command = (str(self._executable), "-m", module, *arguments)

    def run(self, workspace_root: Path, timeout_seconds: float) -> FixedProcessResult:
        try:
            completed = subprocess.run(
                self._command,
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
            raise FixedProcessTimeoutError("fixed Python module timed out") from error
        except OSError as error:
            raise FixedProcessError("fixed Python module could not start") from error
        return FixedProcessResult(completed.returncode, completed.stdout, completed.stderr)
