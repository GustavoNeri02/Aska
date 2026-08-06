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


@dataclass(frozen=True, slots=True)
class FixedWorkspaceTarget:
    workspace_root: Path
    device: int
    inode: int


def validate_workspace_root(workspace_root: Path) -> Path:
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
    return workspace_root


def snapshot_workspace(workspace_root: Path) -> FixedWorkspaceTarget:
    stat = workspace_root.stat()
    return FixedWorkspaceTarget(workspace_root, stat.st_dev, stat.st_ino)


def workspace_target_is_current(workspace_root: Path, target: FixedWorkspaceTarget) -> bool:
    return snapshot_workspace(workspace_root) == target


def truncate_output(output: str, max_output_chars: int) -> tuple[str, bool]:
    if len(output) <= max_output_chars:
        return output, False
    return output[:max_output_chars], True
