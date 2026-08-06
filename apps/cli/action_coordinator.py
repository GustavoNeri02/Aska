from dataclasses import dataclass

from apps.cli.confirmation import ConfirmationInterpreter
from apps.cli.handler_result import HandlerResult
from apps.cli.handlers import (
    NaturalOpenLocationHandler,
    NaturalProjectLintHandler,
    NaturalProjectTestsHandler,
)
from capabilities.desktop import OpenWorkspaceLocationCapability
from capabilities.terminal import RunProjectLintCapability, RunProjectTestsCapability
from packages.conversation import (
    CapabilityProposal,
    OpenWorkspaceLocationProposal,
    RunProjectLintProposal,
    RunProjectTestsProposal,
)


@dataclass(slots=True)
class CliActionCoordinator:
    desktop: NaturalOpenLocationHandler | None
    project_tests: NaturalProjectTestsHandler | None
    project_lint: NaturalProjectLintHandler | None

    @classmethod
    def compose(
        cls,
        open_location: OpenWorkspaceLocationCapability | None,
        project_tests: RunProjectTestsCapability | None,
        project_lint: RunProjectLintCapability | None,
        confirmation: ConfirmationInterpreter | None,
    ) -> "CliActionCoordinator":
        return cls(
            NaturalOpenLocationHandler(open_location, confirmation)
            if open_location is not None
            else None,
            NaturalProjectTestsHandler(project_tests, confirmation)
            if project_tests is not None
            else None,
            NaturalProjectLintHandler(project_lint, confirmation)
            if project_lint is not None
            else None,
        )

    @property
    def is_available(self) -> bool:
        return any((self.desktop, self.project_tests, self.project_lint))

    def handle_pending(self, user_message: str) -> HandlerResult | None:
        for handler in (self.desktop, self.project_lint, self.project_tests):
            if handler is not None and (result := handler.handle(user_message)) is not None:
                return result
        return None

    def cancel_pending(self) -> tuple[str, ...]:
        cancelled_operations: list[str] = []
        for handler in (self.desktop, self.project_tests, self.project_lint):
            if handler is None:
                continue
            result = handler.cancel_pending_for_literal_command()
            if result is None:
                continue
            operation = result.facts.get("operation")
            if not isinstance(operation, str):
                raise RuntimeError("cancelled action did not identify its operation")
            cancelled_operations.append(operation)
        return tuple(cancelled_operations)

    def dispatch(
        self,
        proposal: CapabilityProposal,
        user_message: str,
    ) -> HandlerResult:
        if isinstance(proposal, OpenWorkspaceLocationProposal):
            if self.desktop is None:
                return HandlerResult("desktop", "unavailable")
            return self.desktop.handle_proposal(proposal, user_message)
        if isinstance(proposal, RunProjectTestsProposal):
            if self.project_tests is None:
                return HandlerResult("project_tests", "unavailable")
            return self.project_tests.handle_proposal(proposal, user_message)
        if isinstance(proposal, RunProjectLintProposal):
            if self.project_lint is None:
                return HandlerResult("project_lint", "unavailable")
            return self.project_lint.handle_proposal(proposal, user_message)
        raise TypeError("unknown capability proposal")
