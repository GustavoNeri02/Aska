from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from capabilities.filesystem.lister import (
    DEFAULT_MAX_LIST_DEPTH,
    ListFilesCapability,
    ListFilesStatus,
)
from capabilities.filesystem.reader import (
    DEFAULT_MAX_TEXT_FILE_BYTES,
    ReadTextFileCapability,
    ReadTextFileStatus,
)

DEFAULT_MAX_SEARCH_FILES = 200
DEFAULT_MAX_SEARCH_MATCHES = 50
DEFAULT_MAX_SEARCH_QUERY_LENGTH = 256
DEFAULT_MAX_SEARCH_SNIPPET_LENGTH = 240


class SearchTextStatus(StrEnum):
    SUCCESS = "success"
    INVALID_QUERY = "invalid_query"
    INVALID_PATH = "invalid_path"
    OUTSIDE_WORKSPACE = "outside_workspace"
    NOT_FOUND = "not_found"
    NOT_DIRECTORY = "not_directory"
    LIMIT_REACHED = "limit_reached"
    SEARCH_FAILED = "search_failed"


@dataclass(frozen=True, slots=True)
class TextSearchMatch:
    relative_path: str
    line_number: int
    snippet: str

    def __post_init__(self) -> None:
        if not self.relative_path or self.line_number <= 0 or not self.snippet:
            raise ValueError("text search match requires path, positive line and snippet")


@dataclass(frozen=True, slots=True)
class SearchTextResult:
    status: SearchTextStatus
    matches: tuple[TextSearchMatch, ...] = ()

    def __post_init__(self) -> None:
        if (
            self.status
            not in {
                SearchTextStatus.SUCCESS,
                SearchTextStatus.LIMIT_REACHED,
            }
            and self.matches
        ):
            raise ValueError("failed search result cannot expose matches")


class SearchTextCapability:
    def __init__(
        self,
        workspace_root: Path,
        *,
        max_files: int = DEFAULT_MAX_SEARCH_FILES,
        max_depth: int = DEFAULT_MAX_LIST_DEPTH,
        max_file_bytes: int = DEFAULT_MAX_TEXT_FILE_BYTES,
        max_matches: int = DEFAULT_MAX_SEARCH_MATCHES,
        max_query_length: int = DEFAULT_MAX_SEARCH_QUERY_LENGTH,
        max_snippet_length: int = DEFAULT_MAX_SEARCH_SNIPPET_LENGTH,
    ) -> None:
        if max_matches <= 0 or max_query_length <= 0 or max_snippet_length <= 0:
            raise ValueError("search limits must be positive")
        self._file_lister = ListFilesCapability(
            workspace_root,
            max_results=max_files,
            max_depth=max_depth,
        )
        self._file_reader = ReadTextFileCapability(
            workspace_root,
            max_bytes=max_file_bytes,
        )
        self._max_matches = max_matches
        self._max_query_length = max_query_length
        self._max_snippet_length = max_snippet_length

    def search(
        self,
        query: str,
        *,
        directory: str = ".",
        extension: str | None = None,
    ) -> SearchTextResult:
        normalized_query = query.strip()
        if (
            not normalized_query
            or len(normalized_query) > self._max_query_length
            or any(marker in normalized_query for marker in ("\0", "\n", "\r"))
        ):
            return SearchTextResult(SearchTextStatus.INVALID_QUERY)

        listing = self._file_lister.list(directory, extension=extension)
        mapped_error = _map_listing_error(listing.status)
        if mapped_error is not None:
            return SearchTextResult(mapped_error)

        matches: list[TextSearchMatch] = []
        folded_query = normalized_query.casefold()
        for relative_path in listing.paths:
            read_result = self._file_reader.read(relative_path)
            if read_result.status is not ReadTextFileStatus.SUCCESS:
                continue
            if read_result.content is None:
                raise RuntimeError("successful text read returned no content")
            for line_number, line in enumerate(read_result.content.splitlines(), start=1):
                match_index = line.casefold().find(folded_query)
                if match_index < 0:
                    continue
                matches.append(
                    TextSearchMatch(
                        relative_path,
                        line_number,
                        _snippet(
                            line,
                            match_index,
                            len(normalized_query),
                            self._max_snippet_length,
                        ),
                    )
                )
                if len(matches) == self._max_matches:
                    return SearchTextResult(SearchTextStatus.LIMIT_REACHED, tuple(matches))

        status = (
            SearchTextStatus.LIMIT_REACHED
            if listing.status is ListFilesStatus.LIMIT_REACHED
            else SearchTextStatus.SUCCESS
        )
        return SearchTextResult(status, tuple(matches))


def _map_listing_error(status: ListFilesStatus) -> SearchTextStatus | None:
    return {
        ListFilesStatus.INVALID_PATH: SearchTextStatus.INVALID_PATH,
        ListFilesStatus.OUTSIDE_WORKSPACE: SearchTextStatus.OUTSIDE_WORKSPACE,
        ListFilesStatus.NOT_FOUND: SearchTextStatus.NOT_FOUND,
        ListFilesStatus.NOT_DIRECTORY: SearchTextStatus.NOT_DIRECTORY,
        ListFilesStatus.READ_FAILED: SearchTextStatus.SEARCH_FAILED,
    }.get(status)


def _snippet(line: str, match_index: int, query_length: int, limit: int) -> str:
    stripped_line = line.strip()
    if len(stripped_line) <= limit:
        return stripped_line
    start = max(0, match_index - limit // 3)
    end = min(len(line), max(start + limit, match_index + query_length))
    snippet = line[start:end].strip()
    return f"{'…' if start else ''}{snippet}{'…' if end < len(line) else ''}"
