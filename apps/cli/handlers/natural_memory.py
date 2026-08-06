from apps.cli.confirmation import ConfirmationDecision, ConfirmationInterpreter, parse_confirmation
from apps.cli.handler_result import HandlerResult
from packages.conversation import (
    AddMemoryIntent,
    DeleteMemoryIntent,
    EditMemoryIntent,
    MemoryIntentInterpreter,
    NameUpdateIntent,
    PendingMemoryAdd,
    PendingMemoryDelete,
    PendingMemoryEdit,
    canonical_name_memory,
    detect_memory_add,
    detect_memory_delete,
    detect_name_change,
    find_name_memory_candidates,
    should_interpret_memory_add,
    should_interpret_memory_delete,
    should_interpret_memory_edit,
    should_interpret_name_change,
)
from packages.memory import Memory, MemoryService

PendingMemory = PendingMemoryAdd | PendingMemoryDelete | PendingMemoryEdit


class NaturalMemoryHandler:
    def __init__(
        self,
        memory_service: MemoryService,
        memory_intent_interpreter: MemoryIntentInterpreter | None,
        confirmation_interpreter: ConfirmationInterpreter | None = None,
    ) -> None:
        self._memory_service = memory_service
        self._memory_intent_interpreter = memory_intent_interpreter
        self._confirmation_interpreter = confirmation_interpreter
        self._pending: PendingMemory | None = None
        self._pending_user_message: str | None = None

    def handle(self, user_input: str) -> HandlerResult | None:
        if self._pending is not None:
            return self._handle_pending(user_input)
        new_content = detect_name_change(user_input)
        name_gate = should_interpret_name_change(user_input)
        delete_gate = should_interpret_memory_delete(user_input)
        edit_gate = should_interpret_memory_edit(user_input)
        add_gate = should_interpret_memory_add(user_input)
        deterministic_delete = detect_memory_delete(user_input)
        deterministic_add = detect_memory_add(user_input)
        if new_content is None and not name_gate and deterministic_delete is not None:
            return self._propose_delete(deterministic_delete.query, user_input)
        if (
            new_content is None
            and not name_gate
            and not delete_gate
            and not edit_gate
            and deterministic_add is not None
        ):
            return self._set_pending(PendingMemoryAdd(deterministic_add.content), user_input)
        if (
            new_content is None
            and self._memory_intent_interpreter is not None
            and (name_gate or delete_gate or edit_gate or add_gate)
        ):
            intent = self._memory_intent_interpreter.interpret(user_input)
            if name_gate and isinstance(intent, NameUpdateIntent):
                new_content = canonical_name_memory(intent.new_name)
            elif not name_gate and delete_gate and isinstance(intent, DeleteMemoryIntent):
                return self._propose_delete(intent.query, user_input)
            elif (
                not name_gate
                and not delete_gate
                and edit_gate
                and isinstance(intent, EditMemoryIntent)
            ):
                return self._propose_edit(intent.query, intent.new_content, user_input)
            elif (
                not name_gate
                and not delete_gate
                and not edit_gate
                and add_gate
                and isinstance(intent, AddMemoryIntent)
            ):
                return self._set_pending(PendingMemoryAdd(intent.content), user_input)
        if new_content is not None:
            return self._propose_name_edit(new_content, user_input)
        return None

    def cancel_pending_for_literal_command(self) -> HandlerResult | None:
        if self._pending is None:
            return None
        kind = _pending_kind(self._pending)
        self._pending = None
        self._pending_user_message = None
        return HandlerResult(
            "memory", "proposal_cancelled", {"operation": kind, "reason": "literal_command"}
        )

    def _handle_pending(self, user_input: str) -> HandlerResult:
        decision = (
            self._confirmation_interpreter.interpret(user_input, "alteração de memória")
            if self._confirmation_interpreter is not None
            else parse_confirmation(user_input)
        )
        if decision is ConfirmationDecision.UNKNOWN:
            return HandlerResult(
                "memory", "confirmation_unknown", {"operation": _pending_kind(self._pending)}
            )
        pending = self._pending
        pending_user_message = self._pending_user_message
        self._pending = None
        self._pending_user_message = None
        if pending is None:
            raise RuntimeError("pending memory proposal disappeared")
        operation = _pending_kind(pending)
        if decision is ConfirmationDecision.CANCEL:
            return HandlerResult(
                "memory",
                "proposal_cancelled",
                {"operation": operation},
                original_request=pending_user_message,
            )
        if isinstance(pending, PendingMemoryEdit):
            status = self._memory_service.edit_by_id(
                pending.memory_id, pending.expected_content, pending.new_content
            )
        elif isinstance(pending, PendingMemoryDelete):
            status = self._memory_service.delete_by_id(pending.memory_id, pending.expected_content)
        else:
            status = self._memory_service.add(pending.content).status
        return HandlerResult(
            "memory",
            "operation_completed",
            {"operation": operation, "status": status.value},
            original_request=pending_user_message,
        )

    def _set_pending(self, pending: PendingMemory, user_message: str) -> HandlerResult:
        self._pending = pending
        self._pending_user_message = user_message
        facts: dict[str, object] = {"operation": _pending_kind(pending)}
        if isinstance(pending, PendingMemoryAdd):
            facts["content"] = pending.content
        else:
            facts["current_content"] = pending.expected_content
        if isinstance(pending, PendingMemoryEdit):
            facts["new_content"] = pending.new_content
        return HandlerResult("memory", "confirmation_required", facts)

    def _propose_name_edit(self, new_content: str, user_message: str) -> HandlerResult:
        candidates = find_name_memory_candidates(self._memory_service.list())
        if len(candidates) != 1:
            return HandlerResult(
                "memory",
                "candidate_selection_failed",
                {"count": len(candidates), "operation": "edit", "subject": "name"},
            )
        candidate = candidates[0]
        return self._set_pending(
            PendingMemoryEdit(candidate.id, candidate.content, new_content), user_message
        )

    def _propose_delete(self, query: str, user_message: str) -> HandlerResult:
        candidates = self._find_candidates(query)
        if len(candidates) != 1:
            return HandlerResult(
                "memory",
                "candidate_selection_failed",
                {"count": len(candidates), "operation": "delete"},
            )
        candidate = candidates[0]
        return self._set_pending(PendingMemoryDelete(candidate.id, candidate.content), user_message)

    def _propose_edit(self, query: str, new_content: str, user_message: str) -> HandlerResult:
        candidates = self._find_candidates(query)
        if len(candidates) != 1:
            return HandlerResult(
                "memory",
                "candidate_selection_failed",
                {"count": len(candidates), "operation": "edit"},
            )
        candidate = candidates[0]
        return self._set_pending(
            PendingMemoryEdit(candidate.id, candidate.content, new_content), user_message
        )

    def _find_candidates(self, query: str) -> list[Memory]:
        exact = [m for m in self._memory_service.list() if m.content.casefold() == query.casefold()]
        return exact or self._memory_service.search(query)


def _pending_kind(pending: PendingMemory | None) -> str:
    if isinstance(pending, PendingMemoryAdd):
        return "add"
    if isinstance(pending, PendingMemoryDelete):
        return "delete"
    if isinstance(pending, PendingMemoryEdit):
        return "edit"
    return "unknown"
