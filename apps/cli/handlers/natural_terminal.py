from collections.abc import Callable
from dataclasses import dataclass

from apps.cli.confirmation import ConfirmationDecision, parse_confirmation
from capabilities.terminal import (
    ProjectTestTarget,
    RunProjectTestsCapability,
    RunProjectTestsResult,
)
from packages.conversation import (
    ConversationService,
    ExternalActionEvent,
    RunProjectTestsProposal,
)


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
            fact_message = "Estado local da ação: cancelled"
            self._output_writer(fact_message)
            response = self._conversation_service.respond_to_external_event(
                pending.user_message,
                ExternalActionEvent(
                    action="run_project_tests",
                    event="cancelled",
                    facts={},
                ),
            )
            self._output_writer(f"Aska > {response}")
            return True

        result = self._capability.run(pending.target)
        fact_message = _present_facts(result)
        self._output_writer(fact_message)
        response = self._conversation_service.respond_to_external_event(
            pending.user_message,
            ExternalActionEvent(
                action="run_project_tests",
                event="completed",
                facts=_event_facts(result),
            ),
        )
        self._output_writer(f"Aska > {response}")
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
            del pending
            self._output_writer("Estado local da ação: cancelled")


def _present_facts(result: RunProjectTestsResult) -> str:
    sections = ["Resultado local da ação:", f"Status: {result.status.value}"]
    if result.exit_code is not None:
        sections.append(f"Exit code: {result.exit_code}")
    if result.stdout.strip():
        sections.append(f"stdout:\n{result.stdout.rstrip()}")
    if result.stderr.strip():
        sections.append(f"stderr:\n{result.stderr.rstrip()}")
    if result.output_truncated:
        sections.append("A saída foi truncada no limite seguro configurado.")
    return "\n".join(sections)


def _event_facts(result: RunProjectTestsResult) -> dict[str, object]:
    return {
        "status": result.status.value,
        "exit_code": result.exit_code,
        "stdout": _compact_for_history(result.stdout, 3072),
        "stderr": _compact_for_history(result.stderr, 1024),
        "output_truncated": result.output_truncated,
    }


def _compact_for_history(message: str, max_chars: int = 4096) -> str:
    if len(message) <= max_chars:
        return message
    side_chars = (max_chars - len("\n... resultado compactado ...\n")) // 2
    return (
        f"{message[:side_chars]}\n"
        "... resultado compactado ...\n"
        f"{message[-side_chars:]}"
    )
