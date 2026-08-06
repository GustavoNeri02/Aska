from pathlib import PurePosixPath

from apps.cli.handler_result import HandlerResult
from capabilities.filesystem import (
    ListFilesCapability,
    ListFilesStatus,
    ReadTextFileCapability,
    ReadTextFileStatus,
    suggest_similar_file_paths,
)
from packages.conversation import (
    ContextDocument,
    FileIntentInterpreter,
    ListFilesIntent,
    ReadTextFileIntent,
    detect_explicit_file_location,
    detect_explicit_file_read,
    detect_known_document_query,
    should_interpret_file_read,
)


class NaturalFileReadHandler:
    def __init__(
        self,
        file_reader: ReadTextFileCapability,
        file_intent_interpreter: FileIntentInterpreter,
        file_lister: ListFilesCapability | None = None,
    ) -> None:
        self._file_reader = file_reader
        self._file_intent_interpreter = file_intent_interpreter
        self._file_lister = file_lister

    def handle(self, user_input: str) -> HandlerResult | None:
        intent = detect_explicit_file_read(user_input)
        if intent is None:
            intent = detect_explicit_file_location(user_input)
        if intent is None:
            intent = detect_known_document_query(user_input)
        if intent is None:
            if not should_interpret_file_read(user_input):
                return None
            intent = self._file_intent_interpreter.interpret(user_input)
        if isinstance(intent, ReadTextFileIntent):
            return self._handle_read(user_input, intent)
        if isinstance(intent, ListFilesIntent) and self._file_lister is not None:
            return self._handle_list(user_input, intent)
        return None

    def _handle_read(self, user_input: str, intent: ReadTextFileIntent) -> HandlerResult:
        result = self._file_reader.read(intent.path)
        if (
            result.status is ReadTextFileStatus.NOT_FOUND
            and self._file_lister is not None
            and _is_bare_filename(intent.path)
        ):
            discovered_path = self._discover_file_by_name(intent.path)
            if isinstance(discovered_path, HandlerResult):
                return discovered_path
            if isinstance(discovered_path, str):
                result = self._file_reader.read(discovered_path)
        if result.status is not ReadTextFileStatus.SUCCESS:
            return HandlerResult("filesystem", "file_read", {"status": result.status.value})

        if result.relative_path is None or result.content is None:
            raise RuntimeError("successful file read returned no content")
        return HandlerResult(
            "filesystem",
            "file_read",
            {"status": result.status.value, "path": result.relative_path},
            ContextDocument(source=result.relative_path, content=result.content),
        )

    def _discover_file_by_name(self, filename: str) -> str | HandlerResult | None:
        if self._file_lister is None:
            return None
        listing = self._file_lister.list(name_contains=filename)
        if listing.status not in {
            ListFilesStatus.SUCCESS,
            ListFilesStatus.LIMIT_REACHED,
        }:
            return HandlerResult("filesystem", "file_discovery", {"status": listing.status.value})

        normalized_filename = filename.casefold()
        matches = tuple(
            path
            for path in listing.paths
            if PurePosixPath(path).name.casefold() == normalized_filename
        )
        if listing.status is ListFilesStatus.SUCCESS and len(matches) == 1:
            return matches[0]
        if not matches and listing.status is ListFilesStatus.SUCCESS:
            return None

        return HandlerResult(
            "filesystem",
            "file_discovery_ambiguous",
            {"matches": matches, "limit_reached": listing.status is ListFilesStatus.LIMIT_REACHED},
        )

    def _handle_list(self, user_input: str, intent: ListFilesIntent) -> HandlerResult:
        if self._file_lister is None:
            return HandlerResult("filesystem", "file_list", {"status": "unavailable"})
        result = self._file_lister.list(
            intent.directory,
            name_contains=intent.name_contains,
            extension=intent.extension,
        )
        if result.status not in {
            ListFilesStatus.SUCCESS,
            ListFilesStatus.LIMIT_REACHED,
        }:
            return HandlerResult("filesystem", "file_list", {"status": result.status.value})
        if not result.paths:
            suggestions = self._suggest_similar_file_paths(intent)
            if suggestions:
                return HandlerResult("filesystem", "file_list_empty", {"suggestions": suggestions})
            return HandlerResult("filesystem", "file_list_empty")

        listing = "\n".join(f"- {path}" for path in result.paths)
        if result.status is ListFilesStatus.LIMIT_REACHED:
            listing = f"{listing}\n- Resultado truncado no limite seguro configurado."
        return HandlerResult(
            "filesystem",
            "file_list",
            {"status": result.status.value, "paths": result.paths},
            ContextDocument(source="listagem segura de arquivos do workspace", content=listing),
        )

    def _suggest_similar_file_paths(self, intent: ListFilesIntent) -> tuple[str, ...]:
        if self._file_lister is None or intent.name_contains is None:
            return ()
        requested_filename = intent.name_contains.strip()
        if not _is_bare_filename(requested_filename):
            return ()
        extension = PurePosixPath(requested_filename).suffix
        if not extension:
            return ()
        candidates = self._file_lister.list(intent.directory, extension=extension)
        if candidates.status is not ListFilesStatus.SUCCESS:
            return ()
        return suggest_similar_file_paths(requested_filename, candidates.paths)


def _is_bare_filename(path: str) -> bool:
    return "/" not in path and "\\" not in path
