from dataclasses import dataclass

from apps.cli.confirmation import ConfirmationDecision, ConfirmationInterpreter, parse_confirmation
from apps.cli.handler_result import HandlerResult
from capabilities.terminal import (
    FixedWorkspaceTarget,
    RunProjectLintCapability,
    RunProjectLintResult,
)
from packages.conversation import RunProjectLintProposal


@dataclass(frozen=True, slots=True)
class _PendingProjectLint:
    target: FixedWorkspaceTarget
    user_message: str


class NaturalProjectLintHandler:
    def __init__(
        self,
        capability: RunProjectLintCapability,
        confirmation_interpreter: ConfirmationInterpreter | None = None,
    ) -> None:
        self._capability = capability
        self._confirmation_interpreter = confirmation_interpreter
        self._pending: _PendingProjectLint | None = None

    def handle(self, user_input: str) -> HandlerResult | None:
        if self._pending is None:
            return None
        decision = (
            self._confirmation_interpreter.interpret(user_input, "executar Ruff check no projeto")
            if self._confirmation_interpreter
            else parse_confirmation(user_input)
        )
        if decision is ConfirmationDecision.UNKNOWN:
            return HandlerResult(
                "project_lint", "confirmation_unknown", {"pending_action": "run_project_lint"}
            )
        pending = self._pending
        self._pending = None
        if decision is ConfirmationDecision.CANCEL:
            return HandlerResult("project_lint", "cancelled", original_request=pending.user_message)
        result = self._capability.run(pending.target)
        return HandlerResult(
            "project_lint", "completed", _event_facts(result), original_request=pending.user_message
        )

    def handle_proposal(self, proposal: RunProjectLintProposal, user_message: str) -> HandlerResult:
        del proposal
        try:
            target = self._capability.prepare()
        except OSError:
            return HandlerResult("project_lint", "workspace_invalid")
        self._pending = _PendingProjectLint(target, user_message)
        return HandlerResult(
            "project_lint",
            "confirmation_required",
            {
                "operation": "run_project_lint",
                "command": self._capability.command,
                "directory": str(target.workspace_root),
                "timeout_seconds": self._capability.timeout_seconds,
            },
        )

    def cancel_pending_for_literal_command(self) -> HandlerResult | None:
        if self._pending is None:
            return None
        self._pending = None
        return HandlerResult("project_lint", "cancelled", {"operation": "run_project_lint"})


def _event_facts(result: RunProjectLintResult) -> dict[str, object]:
    return {
        "status": result.status.value,
        "exit_code": result.exit_code,
        "stdout": result.stdout[:3072],
        "stderr": result.stderr[:1024],
        "output_truncated": result.output_truncated,
    }
