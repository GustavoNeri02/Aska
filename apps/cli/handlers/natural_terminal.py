from dataclasses import dataclass

from apps.cli.confirmation import (
    ConfirmationDecision,
    ConfirmationInterpreter,
    parse_confirmation,
)
from apps.cli.handler_result import HandlerResult
from capabilities.terminal import (
    ProjectTestTarget,
    RunProjectTestsCapability,
    RunProjectTestsResult,
)
from packages.conversation import RunProjectTestsProposal


@dataclass(frozen=True, slots=True)
class _PendingProjectTests:
    target: ProjectTestTarget
    user_message: str


class NaturalProjectTestsHandler:
    def __init__(
        self,
        capability: RunProjectTestsCapability,
        confirmation_interpreter: ConfirmationInterpreter | None = None,
    ) -> None:
        self._capability = capability
        self._confirmation_interpreter = confirmation_interpreter
        self._pending: _PendingProjectTests | None = None

    def handle(self, user_input: str) -> HandlerResult | None:
        if self._pending is None:
            return None
        decision = (
            self._confirmation_interpreter.interpret(
                user_input,
                "executar a suíte inteira de testes do projeto",
            )
            if self._confirmation_interpreter is not None
            else parse_confirmation(user_input)
        )
        if decision is ConfirmationDecision.UNKNOWN:
            return HandlerResult(
                "project_tests",
                "confirmation_unknown",
                {"pending_action": "run_project_tests"},
            )

        pending = self._pending
        self._pending = None
        if pending is None:
            raise RuntimeError("confirmed project test proposal has no target")
        if decision is ConfirmationDecision.CANCEL:
            return HandlerResult(
                "project_tests",
                "cancelled",
                original_request=pending.user_message,
            )

        result = self._capability.run(pending.target)
        return HandlerResult(
            "project_tests",
            "completed",
            _event_facts(result),
            original_request=pending.user_message,
        )

    def handle_proposal(
        self,
        proposal: RunProjectTestsProposal,
        user_message: str,
    ) -> HandlerResult:
        del proposal
        try:
            target = self._capability.prepare()
        except OSError:
            return HandlerResult("project_tests", "workspace_invalid")
        self._pending = _PendingProjectTests(target, user_message)
        return HandlerResult(
            "project_tests",
            "confirmation_required",
            {
                "operation": "run_project_tests",
                "command": tuple(self._capability.command),
                "directory": str(target.workspace_root),
                "timeout_seconds": self._capability.timeout_seconds,
            },
        )

    def cancel_pending_for_literal_command(self) -> HandlerResult | None:
        if self._pending is not None:
            self._pending = None
            return HandlerResult("project_tests", "cancelled", {"operation": "run_project_tests"})
        return None


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
    return f"{message[:side_chars]}\n... resultado compactado ...\n{message[-side_chars:]}"
