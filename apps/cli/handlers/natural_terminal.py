from collections.abc import Callable
from dataclasses import dataclass

from apps.cli.confirmation import ConfirmationDecision, parse_confirmation
from capabilities.terminal import (
    ProjectTestTarget,
    RunProjectTestsCapability,
    RunProjectTestsResult,
    RunProjectTestsStatus,
)
from packages.conversation import ConversationService, RunProjectTestsProposal


@dataclass(frozen=True, slots=True)
class _PendingProjectTests:
    target: ProjectTestTarget
    user_message: str


class NaturalProjectTestsHandler:
    def __init__(
        self,
        capability: RunProjectTestsCapability,
        conversation_service: ConversationService,
        output_writer: Callable[[str], None],
    ) -> None:
        self._capability = capability
        self._conversation_service = conversation_service
        self._output_writer = output_writer
        self._pending: _PendingProjectTests | None = None

    def handle(self, user_input: str) -> bool:
        if self._pending is None:
            return False
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
            message = "Execução dos testes cancelada."
            self._conversation_service.record_external_result(
                pending.user_message,
                message,
            )
            self._output_writer(message)
            return True

        result = self._capability.run(pending.target)
        message = _present_result(result)
        self._conversation_service.record_external_result(
            pending.user_message,
            _compact_for_history(message),
        )
        self._output_writer(message)
        return True

    def handle_proposal(
        self,
        proposal: RunProjectTestsProposal,
        user_message: str,
    ) -> bool:
        del proposal
        try:
            target = self._capability.prepare()
        except OSError:
            self._output_writer("Não foi possível validar o workspace para os testes.")
            return True
        self._pending = _PendingProjectTests(target, user_message)
        command = " ".join(self._capability.command)
        self._output_writer(
            "Proposta de execução:\n"
            "Operação: testes do projeto\n"
            f"Comando fixo: {command}\n"
            f"Diretório: {target.workspace_root}\n"
            f"Timeout: {self._capability.timeout_seconds:g} segundos\n"
            "Confirmar execução? Digite 'sim' para confirmar ou 'não' para cancelar."
        )
        return True

    def cancel_pending_for_literal_command(self) -> None:
        if self._pending is not None:
            pending = self._pending
            self._pending = None
            message = "Proposta de execução dos testes anterior cancelada."
            self._conversation_service.record_external_result(
                pending.user_message,
                message,
            )
            self._output_writer(message)


def _present_result(result: RunProjectTestsResult) -> str:
    if result.status is RunProjectTestsStatus.TARGET_CHANGED:
        return "O workspace mudou após a proposta; os testes não foram executados."
    if result.status is RunProjectTestsStatus.TIMED_OUT:
        return "A execução dos testes excedeu o timeout e foi interrompida."
    if result.status is RunProjectTestsStatus.START_FAILED:
        return "Não foi possível iniciar os testes do projeto."

    title = (
        "Testes concluídos com sucesso."
        if result.status is RunProjectTestsStatus.SUCCESS
        else "Os testes foram executados e houve falhas."
    )
    sections = [title, f"Exit code: {result.exit_code}"]
    if result.stdout.strip():
        sections.append(f"stdout:\n{result.stdout.rstrip()}")
    if result.stderr.strip():
        sections.append(f"stderr:\n{result.stderr.rstrip()}")
    if result.output_truncated:
        sections.append("A saída foi truncada no limite seguro configurado.")
    return "\n".join(sections)


def _compact_for_history(message: str, max_chars: int = 4096) -> str:
    if len(message) <= max_chars:
        return message
    side_chars = (max_chars - len("\n... resultado compactado ...\n")) // 2
    return (
        f"{message[:side_chars]}\n"
        "... resultado compactado ...\n"
        f"{message[-side_chars:]}"
    )
