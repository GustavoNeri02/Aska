from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True, slots=True)
class FixedProcessResult:
    exit_code: int
    stdout: str
    stderr: str


class FixedProcessError(RuntimeError):
    """Raised when an approved fixed process cannot be started."""


class FixedProcessTimeoutError(RuntimeError):
    """Raised when an approved fixed process exceeds its timeout."""


class FixedProcessRunner(Protocol):
    def run(self, workspace_root: Path, timeout_seconds: float) -> FixedProcessResult: ...
