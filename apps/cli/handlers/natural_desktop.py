from collections.abc import Callable
from dataclasses import dataclass

from apps.cli.confirmation import ConfirmationDecision, parse_confirmation
from capabilities.desktop import (
    OpenWorkspaceLocationCapability,
    ResolveLocationStatus,
    WorkspaceLocationTarget,
)
from packages.conversation import (
    ConversationEvent,
    ConversationService,
    OpenWorkspaceLocationProposal,
    detect_explicit_open_location,
)


@dataclass(frozen=True, slots=True)
class _PendingOpenLocation:
    target: WorkspaceLocationTarget
    user_message: str


class NaturalOpenLocationHandler:
    def __init__(
        self,
        capability: OpenWorkspaceLocationCapability,
        conversation_service: ConversationService,
        output_writer: Callable[[str], None],
    ) -> None:
        self._capability = capability
        self._conversation_service = conversation_service
        self._output_writer = output_writer
        self._pending: _PendingOpenLocation | None = None

    def handle(self, user_input: str) -> bool:
        if self._pending is not None:
            return self._handle_confirmation(user_input)

        proposal = detect_explicit_open_location(user_input)
        if proposal is None:
            return False
        return self.handle_proposal(proposal, user_input)

    def handle_proposal(
        self,
        proposal: OpenWorkspaceLocationProposal,
        user_message: str,
    ) -> bool:
        result = self._capability.prepare(proposal.path)
        if result.status is not ResolveLocationStatus.SUCCESS:
            self._output_writer(
                f"Sistema > open_workspace_location: {result.status.value}"
            )
            response = self._conversation_service.present_event(
                user_message,
                ConversationEvent(
                    domain="desktop",
                    kind="open_location_refused",
                    facts={"path": proposal.path, "status": result.status.value},
                ),
            )
            self._output_writer(f"Aska > {response}")
            return True
        if result.target is None:
            raise RuntimeError("successful location resolution returned no target")

        self._pending = _PendingOpenLocation(result.target, user_message)
        self._output_writer(
            "Sistema > Proposta de abertura:\n"
            "Aplicativo: Explorador de Arquivos\n"
            f"Pasta: {result.target.resolved_path}\n"
            "Confirmar abertura? Digite 'sim' para confirmar ou 'não' para cancelar."
        )
        return True

    def cancel_pending_for_literal_command(self) -> None:
        if self._pending is not None:
            pending = self._pending
            self._pending = None
            self._output_writer("Sistema > open_workspace_location: cancelled")
            response = self._conversation_service.present_event(
                pending.user_message,
                ConversationEvent(
                    domain="desktop",
                    kind="open_location_cancelled",
                    facts={"reason": "literal_command"},
                ),
            )
            self._output_writer(f"Aska > {response}")

    def _handle_confirmation(self, user_input: str) -> bool:
        decision = parse_confirmation(user_input)
        if decision is ConfirmationDecision.UNKNOWN:
            self._output_writer(
                "Confirmação não reconhecida. Digite 'sim' para confirmar ou 'não' "
                "para cancelar."
            )
            return True

        pending = self._pending
        self._pending = None
        if decision is ConfirmationDecision.CANCEL:
            if pending is None:
                raise RuntimeError("cancelled location proposal has no target")
            self._output_writer("Sistema > open_workspace_location: cancelled")
            response = self._conversation_service.present_event(
                pending.user_message,
                ConversationEvent(
                    domain="desktop",
                    kind="open_location_cancelled",
                    facts={},
                ),
            )
            self._output_writer(f"Aska > {response}")
            return True
        if pending is None:
            raise RuntimeError("confirmed location proposal has no target")

        result = self._capability.open(pending.target)
        self._output_writer(f"Sistema > open_workspace_location: {result.status.value}")
        response = self._conversation_service.present_event(
            pending.user_message,
            ConversationEvent(
                domain="desktop",
                kind="open_location_completed",
                facts={
                    "path": pending.target.relative_path,
                    "status": result.status.value,
                },
            ),
        )
        self._output_writer(f"Aska > {response}")
        return True
