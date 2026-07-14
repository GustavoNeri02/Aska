from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

DEFAULT_MAX_TEXT_FILE_BYTES = 64 * 1024


class TextFileReadErrorCode(StrEnum):
    INVALID_PATH = "invalid_path"
    OUTSIDE_WORKSPACE = "outside_workspace"
    NOT_FOUND = "not_found"
    NOT_FILE = "not_file"
    TOO_LARGE = "too_large"
    NOT_TEXT = "not_text"
    EMPTY = "empty"
    UNREADABLE = "unreadable"


class TextFileReadError(RuntimeError):
    def __init__(self, code: TextFileReadErrorCode) -> None:
        self.code = code
        super().__init__(code.value)


@dataclass(frozen=True, slots=True)
class TextFileContent:
    relative_path: str
    content: str


class TextFileReader:
    def __init__(
        self,
        workspace_root: str | Path,
        max_bytes: int = DEFAULT_MAX_TEXT_FILE_BYTES,
    ) -> None:
        if max_bytes <= 0:
            raise ValueError("max_bytes must be positive")
        try:
            root = Path(workspace_root).resolve(strict=True)
        except OSError as error:
            raise ValueError("workspace_root must exist") from error
        if not root.is_dir():
            raise ValueError("workspace_root must be a directory")
        self._workspace_root = root
        self._max_bytes = max_bytes

    def read(self, relative_path: str) -> TextFileContent:
        requested_path = relative_path.strip()
        if (
            not requested_path
            or "\0" in requested_path
            or "\n" in requested_path
            or "\r" in requested_path
        ):
            raise TextFileReadError(TextFileReadErrorCode.INVALID_PATH)

        path = Path(requested_path)
        if path.is_absolute():
            raise TextFileReadError(TextFileReadErrorCode.OUTSIDE_WORKSPACE)

        try:
            unresolved_path = (self._workspace_root / path).resolve(strict=False)
        except OSError as error:
            raise TextFileReadError(TextFileReadErrorCode.UNREADABLE) from error
        if not unresolved_path.is_relative_to(self._workspace_root):
            raise TextFileReadError(TextFileReadErrorCode.OUTSIDE_WORKSPACE)

        try:
            resolved_path = (self._workspace_root / path).resolve(strict=True)
        except FileNotFoundError as error:
            raise TextFileReadError(TextFileReadErrorCode.NOT_FOUND) from error
        except OSError as error:
            raise TextFileReadError(TextFileReadErrorCode.UNREADABLE) from error

        if not resolved_path.is_relative_to(self._workspace_root):
            raise TextFileReadError(TextFileReadErrorCode.OUTSIDE_WORKSPACE)
        if not resolved_path.is_file():
            raise TextFileReadError(TextFileReadErrorCode.NOT_FILE)

        try:
            if resolved_path.stat().st_size > self._max_bytes:
                raise TextFileReadError(TextFileReadErrorCode.TOO_LARGE)
            raw_content = resolved_path.read_bytes()
        except TextFileReadError:
            raise
        except OSError as error:
            raise TextFileReadError(TextFileReadErrorCode.UNREADABLE) from error

        if len(raw_content) > self._max_bytes:
            raise TextFileReadError(TextFileReadErrorCode.TOO_LARGE)
        if b"\0" in raw_content:
            raise TextFileReadError(TextFileReadErrorCode.NOT_TEXT)
        try:
            content = raw_content.decode("utf-8")
        except UnicodeDecodeError as error:
            raise TextFileReadError(TextFileReadErrorCode.NOT_TEXT) from error
        if not content.strip():
            raise TextFileReadError(TextFileReadErrorCode.EMPTY)

        return TextFileContent(
            relative_path=resolved_path.relative_to(self._workspace_root).as_posix(),
            content=content,
        )
