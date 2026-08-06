from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Protocol


class LocationLauncher(Protocol):
    def open(self, path: Path) -> None: ...


class ResolveLocationStatus(StrEnum):
    SUCCESS = "success"
    INVALID_PATH = "invalid_path"
    OUTSIDE_WORKSPACE = "outside_workspace"
    NOT_FOUND = "not_found"
    NOT_DIRECTORY = "not_directory"
    RESOLVE_FAILED = "resolve_failed"


class OpenLocationStatus(StrEnum):
    SUCCESS = "success"
    TARGET_CHANGED = "target_changed"
    OPEN_FAILED = "open_failed"


@dataclass(frozen=True, slots=True)
class WorkspaceLocationTarget:
    relative_path: str
    resolved_path: Path
    device: int
    inode: int


@dataclass(frozen=True, slots=True)
class ResolveLocationResult:
    status: ResolveLocationStatus
    target: WorkspaceLocationTarget | None = None

    def __post_init__(self) -> None:
        if (self.status is ResolveLocationStatus.SUCCESS) != (self.target is not None):
            raise ValueError("only successful resolution can expose a target")


@dataclass(frozen=True, slots=True)
class OpenLocationResult:
    status: OpenLocationStatus


class OpenWorkspaceLocationCapability:
    def __init__(self, workspace_root: Path, launcher: LocationLauncher) -> None:
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

    def prepare(self, relative_path: str) -> ResolveLocationResult:
        requested_path = relative_path.strip()
        if (
            not requested_path
            or any(marker in requested_path for marker in ("\0", "\n", "\r"))
            or requested_path.casefold().startswith("file://")
        ):
            return ResolveLocationResult(ResolveLocationStatus.INVALID_PATH)

        path = Path(requested_path)
        if (
            path.is_absolute()
            or PurePosixPath(requested_path).is_absolute()
            or PureWindowsPath(requested_path).is_absolute()
            or bool(PureWindowsPath(requested_path).drive)
        ):
            return ResolveLocationResult(ResolveLocationStatus.OUTSIDE_WORKSPACE)

        try:
            unresolved_path = (self._workspace_root / path).resolve(strict=False)
        except OSError:
            return ResolveLocationResult(ResolveLocationStatus.RESOLVE_FAILED)
        if not unresolved_path.is_relative_to(self._workspace_root):
            return ResolveLocationResult(ResolveLocationStatus.OUTSIDE_WORKSPACE)

        try:
            resolved_path = (self._workspace_root / path).resolve(strict=True)
        except FileNotFoundError:
            return ResolveLocationResult(ResolveLocationStatus.NOT_FOUND)
        except OSError:
            return ResolveLocationResult(ResolveLocationStatus.RESOLVE_FAILED)
        if not resolved_path.is_relative_to(self._workspace_root):
            return ResolveLocationResult(ResolveLocationStatus.OUTSIDE_WORKSPACE)
        if not resolved_path.is_dir():
            return ResolveLocationResult(ResolveLocationStatus.NOT_DIRECTORY)

        try:
            stat = resolved_path.stat()
        except OSError:
            return ResolveLocationResult(ResolveLocationStatus.RESOLVE_FAILED)
        return ResolveLocationResult(
            ResolveLocationStatus.SUCCESS,
            WorkspaceLocationTarget(
                relative_path=resolved_path.relative_to(self._workspace_root).as_posix() or ".",
                resolved_path=resolved_path,
                device=stat.st_dev,
                inode=stat.st_ino,
            ),
        )

    def open(self, target: WorkspaceLocationTarget) -> OpenLocationResult:
        current = self.prepare(target.relative_path)
        if current.target != target:
            return OpenLocationResult(OpenLocationStatus.TARGET_CHANGED)
        try:
            self._launcher.open(target.resolved_path)
        except OSError:
            return OpenLocationResult(OpenLocationStatus.OPEN_FAILED)
        return OpenLocationResult(OpenLocationStatus.SUCCESS)
