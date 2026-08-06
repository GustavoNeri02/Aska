from dataclasses import dataclass

from apps.cli.confirmation import (
    ConfirmationDecision,
    ConfirmationInterpreter,
    parse_confirmation,
)
from apps.cli.handler_result import HandlerResult
from capabilities.desktop import (
    OpenWorkspaceLocationCapability,
    ResolveLocationStatus,
    WorkspaceLocationTarget,
)
from packages.conversation import OpenWorkspaceLocationProposal, detect_explicit_open_location


@dataclass(frozen=True, slots=True)
class _PendingOpenLocation:
    target: WorkspaceLocationTarget
    user_message: str


class NaturalOpenLocationHandler:
    def __init__(
        self,
        capability: OpenWorkspaceLocationCapability,
        confirmation_interpreter: ConfirmationInterpreter | None = None,
    ) -> None:
        self._capability = capability
        self._confirmation_interpreter = confirmation_interpreter
        self._pending: _PendingOpenLocation | None = None

    def handle(self, user_input: str) -> HandlerResult | None:
        if self._pending is not None:
            return self._handle_confirmation(user_input)

        proposal = detect_explicit_open_location(user_input)
        if proposal is None:
            return None
        return self.handle_proposal(proposal, user_input)

    def handle_proposal(
        self,
        proposal: OpenWorkspaceLocationProposal,
        user_message: str,
    ) -> HandlerResult:
        result = self._capability.prepare(proposal.path)
        if result.status is not ResolveLocationStatus.SUCCESS:
            return HandlerResult(
                "desktop",
                "open_location_refused",
                {"path": proposal.path, "status": result.status.value},
            )
        if result.target is None:
            raise RuntimeError("successful location resolution returned no target")

        self._pending = _PendingOpenLocation(result.target, user_message)
        return HandlerResult(
            "desktop",
            "confirmation_required",
            {
                "application": "Windows File Explorer",
                "path": str(result.target.resolved_path),
            },
        )

    def cancel_pending_for_literal_command(self) -> HandlerResult | None:
        if self._pending is not None:
            self._pending = None
            return HandlerResult(
                "desktop",
                "open_location_cancelled",
                {"operation": "open_workspace_location", "reason": "literal_command"},
            )
        return None

    def _handle_confirmation(self, user_input: str) -> HandlerResult:
        decision = (
            self._confirmation_interpreter.interpret(
                user_input,
                "abrir a pasta proposta no Explorador de Arquivos",
            )
            if self._confirmation_interpreter is not None
            else parse_confirmation(user_input)
        )
        if decision is ConfirmationDecision.UNKNOWN:
            return HandlerResult(
                "desktop",
                "confirmation_unknown",
                {"pending_action": "open_workspace_location"},
            )

        pending = self._pending
        self._pending = None
        if decision is ConfirmationDecision.CANCEL:
            if pending is None:
                raise RuntimeError("cancelled location proposal has no target")
            return HandlerResult(
                "desktop",
                "open_location_cancelled",
                original_request=pending.user_message,
            )
        if pending is None:
            raise RuntimeError("confirmed location proposal has no target")

        result = self._capability.open(pending.target)
        return HandlerResult(
            "desktop",
            "open_location_completed",
            {
                "path": pending.target.relative_path,
                "status": result.status.value,
            },
            original_request=pending.user_message,
        )
