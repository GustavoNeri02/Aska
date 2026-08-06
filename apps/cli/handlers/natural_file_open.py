from dataclasses import dataclass
from pathlib import PurePosixPath

from apps.cli.confirmation import ConfirmationDecision, ConfirmationInterpreter, parse_confirmation
from apps.cli.handler_result import HandlerResult
from capabilities.desktop import (
    OpenWorkspaceFileCapability,
    ResolveFileStatus,
    WorkspaceFileTarget,
)
from capabilities.filesystem import (
    ListFilesCapability,
    ListFilesStatus,
    suggest_similar_file_paths,
)
from packages.conversation import OpenWorkspaceFileProposal, detect_explicit_open_file


@dataclass(frozen=True, slots=True)
class _PendingFileOpen:
    target: WorkspaceFileTarget
    user_message: str


class NaturalOpenFileHandler:
    def __init__(
        self,
        capability: OpenWorkspaceFileCapability,
        file_lister: ListFilesCapability,
        confirmation_interpreter: ConfirmationInterpreter | None = None,
    ) -> None:
        self._capability = capability
        self._file_lister = file_lister
        self._confirmation_interpreter = confirmation_interpreter
        self._pending: _PendingFileOpen | None = None

    def handle(self, user_input: str) -> HandlerResult | None:
        if self._pending is not None:
            return self._handle_confirmation(user_input)
        proposal = detect_explicit_open_file(user_input)
        return self.handle_proposal(proposal, user_input) if proposal is not None else None

    def handle_proposal(
        self, proposal: OpenWorkspaceFileProposal, user_message: str
    ) -> HandlerResult:
        path = proposal.path
        prepared = self._capability.prepare(path)
        if prepared.status is ResolveFileStatus.NOT_FOUND and _is_bare_name(path):
            discovered = self._discover(path)
            if isinstance(discovered, HandlerResult):
                return discovered
            if discovered is not None:
                prepared = self._capability.prepare(discovered)
        if prepared.status is not ResolveFileStatus.SUCCESS:
            return HandlerResult(
                "desktop", "open_file_refused", {"path": path, "status": prepared.status.value}
            )
        if prepared.target is None:
            raise RuntimeError("successful file resolution returned no target")
        self._pending = _PendingFileOpen(prepared.target, user_message)
        return HandlerResult(
            "desktop",
            "confirmation_required",
            {
                "operation": "open_workspace_file",
                "application": "aplicativo padrão do sistema",
                "path": prepared.target.relative_path,
            },
        )

    def cancel_pending_for_literal_command(self) -> HandlerResult | None:
        if self._pending is None:
            return None
        self._pending = None
        return HandlerResult("desktop", "open_file_cancelled", {"operation": "open_workspace_file"})

    def _discover(self, requested_name: str) -> str | HandlerResult | None:
        listing = self._file_lister.list(name_contains=requested_name)
        if listing.status not in {ListFilesStatus.SUCCESS, ListFilesStatus.LIMIT_REACHED}:
            return HandlerResult("desktop", "open_file_discovery", {"status": listing.status.value})
        requested = requested_name.casefold()
        matches = tuple(
            path
            for path in listing.paths
            if PurePosixPath(path).name.casefold() == requested
            or PurePosixPath(path).stem.casefold() == requested
        )
        if listing.status is ListFilesStatus.SUCCESS and len(matches) == 1:
            return matches[0]
        if not matches and listing.status is ListFilesStatus.SUCCESS:
            extension = PurePosixPath(requested_name).suffix
            if extension:
                candidates = self._file_lister.list(extension=extension)
                if candidates.status is ListFilesStatus.SUCCESS:
                    suggestions = suggest_similar_file_paths(requested_name, candidates.paths)
                    if suggestions:
                        return HandlerResult(
                            "desktop", "open_file_not_found", {"suggestions": suggestions}
                        )
            return HandlerResult("desktop", "open_file_not_found")
        return HandlerResult(
            "desktop",
            "open_file_ambiguous",
            {"matches": matches, "limit_reached": listing.status is ListFilesStatus.LIMIT_REACHED},
        )

    def _handle_confirmation(self, user_input: str) -> HandlerResult:
        decision = (
            self._confirmation_interpreter.interpret(
                user_input, "abrir o arquivo proposto no aplicativo padrão"
            )
            if self._confirmation_interpreter is not None
            else parse_confirmation(user_input)
        )
        if decision is ConfirmationDecision.UNKNOWN:
            return HandlerResult(
                "desktop", "confirmation_unknown", {"pending_action": "open_workspace_file"}
            )
        pending = self._pending
        self._pending = None
        if pending is None:
            raise RuntimeError("file proposal disappeared")
        if decision is ConfirmationDecision.CANCEL:
            return HandlerResult(
                "desktop", "open_file_cancelled", original_request=pending.user_message
            )
        result = self._capability.open(pending.target)
        return HandlerResult(
            "desktop",
            "open_file_completed",
            {"path": pending.target.relative_path, "status": result.status.value},
            original_request=pending.user_message,
        )


def _is_bare_name(path: str) -> bool:
    return "/" not in path and "\\" not in path
