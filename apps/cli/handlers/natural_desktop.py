from collections.abc import Callable

from apps.cli.confirmation import ConfirmationDecision, parse_confirmation
from capabilities.desktop import (
    OpenLocationStatus,
    OpenWorkspaceLocationCapability,
    ResolveLocationStatus,
    WorkspaceLocationTarget,
)
from packages.conversation import (
    OpenWorkspaceLocationProposal,
    detect_explicit_open_location,
)


class NaturalOpenLocationHandler:
    def __init__(
        self,
        capability: OpenWorkspaceLocationCapability,
        output_writer: Callable[[str], None],
    ) -> None:
        self._capability = capability
        self._output_writer = output_writer
        self._pending: WorkspaceLocationTarget | None = None

    def handle(self, user_input: str) -> bool:
        if self._pending is not None:
            return self._handle_confirmation(user_input)

        proposal = detect_explicit_open_location(user_input)
        if proposal is None:
            return False
        return self.handle_proposal(proposal)

    def handle_proposal(self, proposal: OpenWorkspaceLocationProposal) -> bool:
        result = self._capability.prepare(proposal.path)
        if result.status is not ResolveLocationStatus.SUCCESS:
            self._output_writer(_resolve_error_message(result.status))
            return True
        if result.target is None:
            raise RuntimeError("successful location resolution returned no target")

        self._pending = result.target
        self._output_writer(
            "Proposta de abertura:\n"
            "Aplicativo: Explorador de Arquivos\n"
            f"Pasta: {result.target.resolved_path}\n"
            "Confirmar abertura? Digite 'sim' para confirmar ou 'não' para cancelar."
        )
        return True

    def cancel_pending_for_literal_command(self) -> None:
        if self._pending is not None:
            self._pending = None
            self._output_writer("Proposta de abertura anterior cancelada.")

    def _handle_confirmation(self, user_input: str) -> bool:
        decision = parse_confirmation(user_input)
        if decision is ConfirmationDecision.UNKNOWN:
            self._output_writer(
                "Confirmação não reconhecida. Digite 'sim' para confirmar ou 'não' "
                "para cancelar."
            )
            return True

        target = self._pending
        self._pending = None
        if decision is ConfirmationDecision.CANCEL:
            self._output_writer("Abertura cancelada.")
            return True
        if target is None:
            raise RuntimeError("confirmed location proposal has no target")

        result = self._capability.open(target)
        messages = {
            OpenLocationStatus.SUCCESS: "Pasta aberta no Explorador de Arquivos.",
            OpenLocationStatus.TARGET_CHANGED: (
                "A pasta mudou após a proposta e não foi aberta. Faça um novo pedido."
            ),
            OpenLocationStatus.OPEN_FAILED: (
                "Não foi possível abrir a pasta no Explorador de Arquivos."
            ),
        }
        self._output_writer(messages[result.status])
        return True


def _resolve_error_message(status: ResolveLocationStatus) -> str:
    messages = {
        ResolveLocationStatus.INVALID_PATH: (
            "O caminho informado não é válido. Use uma pasta relativa ao workspace."
        ),
        ResolveLocationStatus.OUTSIDE_WORKSPACE: (
            "Acesso negado: a pasta deve estar dentro do workspace permitido."
        ),
        ResolveLocationStatus.NOT_FOUND: "A pasta informada não foi encontrada.",
        ResolveLocationStatus.NOT_DIRECTORY: (
            "O caminho informado não aponta para uma pasta."
        ),
        ResolveLocationStatus.RESOLVE_FAILED: (
            "Não foi possível validar a pasta informada."
        ),
    }
    return messages[status]
