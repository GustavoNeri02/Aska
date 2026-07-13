from collections.abc import Callable

from packages.conversation import (
    AddMemoryIntent,
    DeleteMemoryIntent,
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
    should_interpret_name_change,
)
from packages.memory import (
    AddMemoryResult,
    AddMemoryStatus,
    DeleteMemoryStatus,
    EditMemoryStatus,
    MemoryService,
)


class NaturalMemoryHandler:
    def __init__(
        self,
        memory_service: MemoryService,
        memory_intent_interpreter: MemoryIntentInterpreter | None,
        output_writer: Callable[[str], None],
    ) -> None:
        self._memory_service = memory_service
        self._memory_intent_interpreter = memory_intent_interpreter
        self._output_writer = output_writer
        self._pending: PendingMemoryAdd | PendingMemoryDelete | PendingMemoryEdit | None = None

    def handle(self, user_input: str) -> bool:
        if self._pending is not None:
            self._handle_pending(user_input)
            return True

        new_content = detect_name_change(user_input)
        name_gate = should_interpret_name_change(user_input)
        delete_gate = should_interpret_memory_delete(user_input)
        add_gate = should_interpret_memory_add(user_input)
        deterministic_delete = detect_memory_delete(user_input)
        deterministic_add = detect_memory_add(user_input)

        if new_content is None and not name_gate and deterministic_delete is not None:
            self._propose_delete(deterministic_delete.query)
            return True
        if (
            new_content is None
            and not name_gate
            and not delete_gate
            and deterministic_add is not None
        ):
            self._pending = PendingMemoryAdd(deterministic_add.content)
            present_memory_add_proposal(self._pending, self._output_writer)
            return True

        if (
            new_content is None
            and self._memory_intent_interpreter is not None
            and (name_gate or delete_gate or add_gate)
        ):
            intent = self._memory_intent_interpreter.interpret(user_input)
            if name_gate and isinstance(intent, NameUpdateIntent):
                new_content = canonical_name_memory(intent.new_name)
            elif not name_gate and delete_gate and isinstance(intent, DeleteMemoryIntent):
                self._propose_delete(intent.query)
                return True
            elif (
                not name_gate
                and not delete_gate
                and add_gate
                and isinstance(intent, AddMemoryIntent)
            ):
                self._pending = PendingMemoryAdd(intent.content)
                present_memory_add_proposal(self._pending, self._output_writer)
                return True

        if new_content is not None:
            self._propose_name_edit(new_content)
            return True
        return False

    def cancel_pending_for_literal_command(self) -> bool:
        if self._pending is None:
            return False
        cancelled = self._pending
        self._pending = None
        if isinstance(cancelled, PendingMemoryEdit):
            self._output_writer("Proposta de edição anterior cancelada.")
        elif isinstance(cancelled, PendingMemoryDelete):
            self._output_writer("Proposta de exclusão anterior cancelada.")
        else:
            self._output_writer("Proposta de inclusão anterior cancelada.")
        return True

    def _handle_pending(self, user_input: str) -> None:
        normalized_input = user_input.casefold()
        if normalized_input in {"sim", "confirmar", "confirmo"}:
            confirmed = self._pending
            self._pending = None
            if isinstance(confirmed, PendingMemoryEdit):
                status = self._memory_service.edit_by_id(
                    confirmed.memory_id,
                    confirmed.expected_content,
                    confirmed.new_content,
                )
                present_memory_edit_result(status, self._output_writer)
            elif isinstance(confirmed, PendingMemoryDelete):
                status = self._memory_service.delete_by_id(
                    confirmed.memory_id,
                    confirmed.expected_content,
                )
                present_memory_delete_result(status, self._output_writer)
            elif isinstance(confirmed, PendingMemoryAdd):
                result = self._memory_service.add(confirmed.content)
                present_memory_add_result(result, self._output_writer)
            return

        if normalized_input in {"não", "nao", "cancelar", "cancela"}:
            cancelled = self._pending
            self._pending = None
            if isinstance(cancelled, PendingMemoryEdit):
                self._output_writer("Edição de memória cancelada.")
            elif isinstance(cancelled, PendingMemoryDelete):
                self._output_writer("Exclusão de memória cancelada.")
            else:
                self._output_writer("Inclusão de memória cancelada.")
            return

        self._output_writer(
            "Confirmação não reconhecida. Digite 'sim' para confirmar ou 'não' para cancelar."
        )

    def _propose_name_edit(self, new_content: str) -> None:
        candidates = find_name_memory_candidates(self._memory_service.list())
        if not candidates:
            self._output_writer("Não encontrei uma memória de nome para atualizar.")
            return
        if len(candidates) > 1:
            self._output_writer(
                "Encontrei mais de uma memória de nome. Nenhuma foi escolhida automaticamente."
            )
            return

        candidate = candidates[0]
        self._pending = PendingMemoryEdit(
            memory_id=candidate.id,
            expected_content=candidate.content,
            new_content=new_content,
        )
        present_memory_edit_proposal(self._pending, self._output_writer)

    def _propose_delete(self, query: str) -> None:
        exact_candidates = [
            memory
            for memory in self._memory_service.list()
            if memory.content.casefold() == query.casefold()
        ]
        candidates = exact_candidates or self._memory_service.search(query)
        if not candidates:
            self._output_writer("Nenhuma memória correspondente foi encontrada.")
            return
        if len(candidates) > 1:
            self._output_writer(
                "Encontrei mais de uma memória correspondente. "
                "Nenhuma foi escolhida automaticamente."
            )
            return

        candidate = candidates[0]
        self._pending = PendingMemoryDelete(
            memory_id=candidate.id,
            expected_content=candidate.content,
        )
        present_memory_delete_proposal(self._pending, self._output_writer)


def present_memory_add_proposal(
    pending_add: PendingMemoryAdd,
    output_writer: Callable[[str], None],
) -> None:
    output_writer("Ação proposta: adicionar memória")
    output_writer(f"Conteúdo: {pending_add.content}")
    output_writer("Confirmar inclusão? Digite 'sim' para confirmar ou 'não' para cancelar.")


def present_memory_add_result(
    result: AddMemoryResult,
    output_writer: Callable[[str], None],
) -> None:
    messages = {
        AddMemoryStatus.ADDED: "Memória registrada localmente.",
        AddMemoryStatus.DUPLICATE: "Já existe uma memória com esse conteúdo.",
        AddMemoryStatus.INVALID: "O conteúdo proposto não é válido.",
    }
    output_writer(messages[result.status])


def present_memory_delete_proposal(
    pending_delete: PendingMemoryDelete,
    output_writer: Callable[[str], None],
) -> None:
    output_writer("Ação proposta: excluir memória")
    output_writer(f"Conteúdo: {pending_delete.expected_content}")
    output_writer("Confirmar exclusão? Digite 'sim' para confirmar ou 'não' para cancelar.")


def present_memory_delete_result(
    status: DeleteMemoryStatus,
    output_writer: Callable[[str], None],
) -> None:
    messages = {
        DeleteMemoryStatus.DELETED: "Memória removida localmente.",
        DeleteMemoryStatus.NOT_FOUND: "A memória proposta não foi encontrada.",
        DeleteMemoryStatus.INVALID: "A proposta de exclusão não é mais válida.",
        DeleteMemoryStatus.CONFLICT: (
            "A memória mudou desde a proposta. Nenhuma exclusão foi feita."
        ),
    }
    output_writer(messages[status])


def present_memory_edit_proposal(
    pending_edit: PendingMemoryEdit,
    output_writer: Callable[[str], None],
) -> None:
    output_writer("Ação proposta: editar memória")
    output_writer(f"Conteúdo atual: {pending_edit.expected_content}")
    output_writer(f"Novo conteúdo: {pending_edit.new_content}")
    output_writer("Confirmar edição? Digite 'sim' para confirmar ou 'não' para cancelar.")


def present_memory_edit_result(
    status: EditMemoryStatus,
    output_writer: Callable[[str], None],
) -> None:
    messages = {
        EditMemoryStatus.EDITED: "Memória editada localmente.",
        EditMemoryStatus.NOT_FOUND: "A memória proposta não foi encontrada.",
        EditMemoryStatus.DUPLICATE: "Já existe uma memória com o novo conteúdo.",
        EditMemoryStatus.INVALID: "A proposta de edição não é mais válida.",
        EditMemoryStatus.UNCHANGED: "A memória já possui o conteúdo proposto.",
        EditMemoryStatus.CONFLICT: (
            "A memória mudou desde a proposta. Nenhuma alteração foi feita."
        ),
    }
    output_writer(messages[status])
