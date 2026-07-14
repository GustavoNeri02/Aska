from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path, PurePosixPath, PureWindowsPath

DEFAULT_MAX_TEXT_FILE_BYTES = 64 * 1024


class ReadTextFileStatus(StrEnum):
    SUCCESS = "success"
    INVALID_PATH = "invalid_path"
    OUTSIDE_WORKSPACE = "outside_workspace"
    NOT_FOUND = "not_found"
    NOT_FILE = "not_file"
    TOO_LARGE = "too_large"
    NOT_TEXT = "not_text"
    EMPTY = "empty"
    READ_FAILED = "read_failed"


@dataclass(frozen=True, slots=True)
class ReadTextFileResult:
    status: ReadTextFileStatus
    relative_path: str | None = None
    content: str | None = None

    def __post_init__(self) -> None:
        has_content = self.relative_path is not None and self.content is not None
        if self.status is ReadTextFileStatus.SUCCESS and not has_content:
            raise ValueError("successful result requires path and content")
        if self.status is not ReadTextFileStatus.SUCCESS and (
            self.relative_path is not None or self.content is not None
        ):
            raise ValueError("failed result cannot expose path or content")


class ReadTextFileCapability:
    def __init__(
        self,
        workspace_root: Path,
        max_bytes: int = DEFAULT_MAX_TEXT_FILE_BYTES,
    ) -> None:
        if max_bytes <= 0:
            raise ValueError("max_bytes must be positive")
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
        self._max_bytes = max_bytes

    def read(self, relative_path: str) -> ReadTextFileResult:
        requested_path = relative_path.strip()
        if (
            not requested_path
            or "\0" in requested_path
            or "\n" in requested_path
            or "\r" in requested_path
            or requested_path.casefold().startswith("file://")
        ):
            return ReadTextFileResult(ReadTextFileStatus.INVALID_PATH)

        path = Path(requested_path)
        if (
            path.is_absolute()
            or PurePosixPath(requested_path).is_absolute()
            or PureWindowsPath(requested_path).is_absolute()
            or bool(PureWindowsPath(requested_path).drive)
        ):
            return ReadTextFileResult(ReadTextFileStatus.OUTSIDE_WORKSPACE)

        try:
            unresolved_path = (self._workspace_root / path).resolve(strict=False)
        except OSError:
            return ReadTextFileResult(ReadTextFileStatus.READ_FAILED)
        if not unresolved_path.is_relative_to(self._workspace_root):
            return ReadTextFileResult(ReadTextFileStatus.OUTSIDE_WORKSPACE)

        try:
            resolved_path = (self._workspace_root / path).resolve(strict=True)
        except FileNotFoundError:
            return ReadTextFileResult(ReadTextFileStatus.NOT_FOUND)
        except OSError:
            return ReadTextFileResult(ReadTextFileStatus.READ_FAILED)

        if not resolved_path.is_relative_to(self._workspace_root):
            return ReadTextFileResult(ReadTextFileStatus.OUTSIDE_WORKSPACE)
        if not resolved_path.is_file():
            return ReadTextFileResult(ReadTextFileStatus.NOT_FILE)

        try:
            if resolved_path.stat().st_size > self._max_bytes:
                return ReadTextFileResult(ReadTextFileStatus.TOO_LARGE)
            with resolved_path.open("rb") as file:
                raw_content = file.read(self._max_bytes + 1)
        except OSError:
            return ReadTextFileResult(ReadTextFileStatus.READ_FAILED)

        if len(raw_content) > self._max_bytes:
            return ReadTextFileResult(ReadTextFileStatus.TOO_LARGE)
        if b"\0" in raw_content:
            return ReadTextFileResult(ReadTextFileStatus.NOT_TEXT)
        try:
            content = raw_content.decode("utf-8")
        except UnicodeDecodeError:
            return ReadTextFileResult(ReadTextFileStatus.NOT_TEXT)
        if not content.strip():
            return ReadTextFileResult(ReadTextFileStatus.EMPTY)

        return ReadTextFileResult(
            status=ReadTextFileStatus.SUCCESS,
            relative_path=resolved_path.relative_to(self._workspace_root).as_posix(),
            content=content,
        )
