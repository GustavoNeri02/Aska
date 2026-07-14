from collections import deque
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path, PurePosixPath, PureWindowsPath

DEFAULT_MAX_FILE_RESULTS = 200
DEFAULT_MAX_LIST_DEPTH = 4

_IGNORED_DIRECTORY_NAMES = frozenset(
    {
        ".git",
        ".pytest_cache",
        ".ruff_cache",
        ".venv",
        "__pycache__",
        "node_modules",
        "pycache",
        "venv",
    }
)


class ListFilesStatus(StrEnum):
    SUCCESS = "success"
    INVALID_PATH = "invalid_path"
    OUTSIDE_WORKSPACE = "outside_workspace"
    NOT_FOUND = "not_found"
    NOT_DIRECTORY = "not_directory"
    LIMIT_REACHED = "limit_reached"
    READ_FAILED = "read_failed"


@dataclass(frozen=True, slots=True)
class ListFilesResult:
    status: ListFilesStatus
    paths: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if (
            self.status
            not in {
                ListFilesStatus.SUCCESS,
                ListFilesStatus.LIMIT_REACHED,
            }
            and self.paths
        ):
            raise ValueError("failed result cannot expose paths")


class ListFilesCapability:
    def __init__(
        self,
        workspace_root: Path,
        max_results: int = DEFAULT_MAX_FILE_RESULTS,
        max_depth: int = DEFAULT_MAX_LIST_DEPTH,
    ) -> None:
        if max_results <= 0:
            raise ValueError("max_results must be positive")
        if max_depth < 0:
            raise ValueError("max_depth cannot be negative")
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
        self._max_results = max_results
        self._max_depth = max_depth

    def list(
        self,
        directory: str = ".",
        *,
        name_contains: str | None = None,
        extension: str | None = None,
    ) -> ListFilesResult:
        requested_directory = directory.strip()
        normalized_name = _normalize_filter(name_contains)
        normalized_extension = _normalize_extension(extension)
        if (
            not _is_valid_relative_path(requested_directory)
            or normalized_name is False
            or normalized_extension is False
        ):
            return ListFilesResult(ListFilesStatus.INVALID_PATH)

        path = Path(requested_directory)
        if (
            path.is_absolute()
            or PurePosixPath(requested_directory).is_absolute()
            or PureWindowsPath(requested_directory).is_absolute()
            or bool(PureWindowsPath(requested_directory).drive)
        ):
            return ListFilesResult(ListFilesStatus.OUTSIDE_WORKSPACE)

        try:
            unresolved_path = (self._workspace_root / path).resolve(strict=False)
        except OSError:
            return ListFilesResult(ListFilesStatus.READ_FAILED)
        if not unresolved_path.is_relative_to(self._workspace_root):
            return ListFilesResult(ListFilesStatus.OUTSIDE_WORKSPACE)

        try:
            resolved_directory = (self._workspace_root / path).resolve(strict=True)
        except FileNotFoundError:
            return ListFilesResult(ListFilesStatus.NOT_FOUND)
        except OSError:
            return ListFilesResult(ListFilesStatus.READ_FAILED)

        if not resolved_directory.is_relative_to(self._workspace_root):
            return ListFilesResult(ListFilesStatus.OUTSIDE_WORKSPACE)
        if not resolved_directory.is_dir():
            return ListFilesResult(ListFilesStatus.NOT_DIRECTORY)

        paths: list[str] = []
        directories: deque[tuple[Path, int]] = deque([(resolved_directory, 0)])
        while directories:
            current_directory, depth = directories.popleft()
            try:
                entries = sorted(
                    current_directory.iterdir(), key=lambda entry: entry.name.casefold()
                )
                for entry in entries:
                    if entry.is_symlink():
                        continue
                    if entry.is_dir():
                        if (
                            depth < self._max_depth
                            and entry.name.casefold() not in _IGNORED_DIRECTORY_NAMES
                        ):
                            directories.append((entry, depth + 1))
                        continue
                    if not entry.is_file() or not _matches_filters(
                        entry, normalized_name, normalized_extension
                    ):
                        continue
                    if len(paths) == self._max_results:
                        return ListFilesResult(
                            ListFilesStatus.LIMIT_REACHED,
                            tuple(paths),
                        )
                    paths.append(entry.relative_to(self._workspace_root).as_posix())
            except OSError:
                return ListFilesResult(ListFilesStatus.READ_FAILED)

        return ListFilesResult(ListFilesStatus.SUCCESS, tuple(paths))


def _is_valid_relative_path(path: str) -> bool:
    return (
        bool(path)
        and not any(marker in path for marker in ("\0", "\n", "\r"))
        and not path.casefold().startswith("file://")
    )


def _normalize_filter(value: str | None) -> str | None | bool:
    if value is None:
        return None
    normalized = value.strip().casefold()
    if not normalized or any(marker in normalized for marker in ("\0", "\n", "\r")):
        return False
    return normalized


def _normalize_extension(value: str | None) -> str | None | bool:
    normalized = _normalize_filter(value)
    if not isinstance(normalized, str):
        return normalized
    return normalized if normalized.startswith(".") else f".{normalized}"


def _matches_filters(
    path: Path,
    name_contains: str | None | bool,
    extension: str | None | bool,
) -> bool:
    if isinstance(name_contains, str) and name_contains not in path.name.casefold():
        return False
    return not isinstance(extension, str) or path.suffix.casefold() == extension
