from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Protocol

_BLOCKED_EXTENSIONS = frozenset(
    {
        ".bat",
        ".ahk",
        ".appref-ms",
        ".cmd",
        ".com",
        ".cpl",
        ".exe",
        ".jar",
        ".js",
        ".jse",
        ".lnk",
        ".msi",
        ".msh",
        ".msh1",
        ".msh2",
        ".ps1",
        ".pif",
        ".py",
        ".pyw",
        ".reg",
        ".scr",
        ".sh",
        ".sct",
        ".vbs",
        ".vbe",
        ".wsc",
        ".wsf",
    }
)


class FileLauncher(Protocol):
    def open(self, path: Path) -> None: ...


class ResolveFileStatus(StrEnum):
    SUCCESS = "success"
    INVALID_PATH = "invalid_path"
    OUTSIDE_WORKSPACE = "outside_workspace"
    NOT_FOUND = "not_found"
    NOT_FILE = "not_file"
    BLOCKED_TYPE = "blocked_type"
    RESOLVE_FAILED = "resolve_failed"


class OpenFileStatus(StrEnum):
    SUCCESS = "success"
    TARGET_CHANGED = "target_changed"
    OPEN_FAILED = "open_failed"


@dataclass(frozen=True, slots=True)
class WorkspaceFileTarget:
    relative_path: str
    resolved_path: Path
    device: int
    inode: int
    size: int
    modified_ns: int


@dataclass(frozen=True, slots=True)
class ResolveFileResult:
    status: ResolveFileStatus
    target: WorkspaceFileTarget | None = None

    def __post_init__(self) -> None:
        if (self.status is ResolveFileStatus.SUCCESS) != (self.target is not None):
            raise ValueError("only successful resolution can expose a target")


@dataclass(frozen=True, slots=True)
class OpenFileResult:
    status: OpenFileStatus


class OpenWorkspaceFileCapability:
    def __init__(self, workspace_root: Path, launcher: FileLauncher) -> None:
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
        self._workspace_root = workspace_root
        self._launcher = launcher

    def prepare(self, relative_path: str) -> ResolveFileResult:
        requested_path = _strip_matching_quotes(relative_path.strip())
        if (
            not requested_path
            or any(marker in requested_path for marker in ("\0", "\n", "\r"))
            or requested_path.casefold().startswith("file://")
        ):
            return ResolveFileResult(ResolveFileStatus.INVALID_PATH)
        path = Path(requested_path)
        is_absolute = (
            path.is_absolute()
            or PurePosixPath(requested_path).is_absolute()
            or PureWindowsPath(requested_path).is_absolute()
            or bool(PureWindowsPath(requested_path).drive)
        )
        candidate = path if is_absolute else self._workspace_root / path
        if not is_absolute:
            try:
                unresolved = candidate.resolve(strict=False)
            except OSError:
                return ResolveFileResult(ResolveFileStatus.RESOLVE_FAILED)
            if not unresolved.is_relative_to(self._workspace_root):
                return ResolveFileResult(ResolveFileStatus.OUTSIDE_WORKSPACE)
        try:
            resolved = candidate.resolve(strict=True)
        except FileNotFoundError:
            return ResolveFileResult(ResolveFileStatus.NOT_FOUND)
        except OSError:
            return ResolveFileResult(ResolveFileStatus.RESOLVE_FAILED)
        if not is_absolute and not resolved.is_relative_to(self._workspace_root):
            return ResolveFileResult(ResolveFileStatus.OUTSIDE_WORKSPACE)
        if not resolved.is_file():
            return ResolveFileResult(ResolveFileStatus.NOT_FILE)
        if resolved.suffix.casefold() in _BLOCKED_EXTENSIONS:
            return ResolveFileResult(ResolveFileStatus.BLOCKED_TYPE)
        try:
            with resolved.open("rb") as file:
                if file.read(2) == b"MZ":
                    return ResolveFileResult(ResolveFileStatus.BLOCKED_TYPE)
            stat = resolved.stat()
        except OSError:
            return ResolveFileResult(ResolveFileStatus.RESOLVE_FAILED)
        return ResolveFileResult(
            ResolveFileStatus.SUCCESS,
            WorkspaceFileTarget(
                (
                    str(resolved)
                    if is_absolute
                    else resolved.relative_to(self._workspace_root).as_posix()
                ),
                resolved,
                stat.st_dev,
                stat.st_ino,
                stat.st_size,
                stat.st_mtime_ns,
            ),
        )

    def open(self, target: WorkspaceFileTarget) -> OpenFileResult:
        current = self.prepare(target.relative_path)
        if current.target != target:
            return OpenFileResult(OpenFileStatus.TARGET_CHANGED)
        try:
            self._launcher.open(target.resolved_path)
        except OSError:
            return OpenFileResult(OpenFileStatus.OPEN_FAILED)
        return OpenFileResult(OpenFileStatus.SUCCESS)


def _strip_matching_quotes(path: str) -> str:
    if len(path) >= 2 and path[0] == path[-1] and path[0] in {'"', "'"}:
        return path[1:-1].strip()
    return path
