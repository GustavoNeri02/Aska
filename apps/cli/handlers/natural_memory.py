from collections.abc import Callable

from packages.conversation import PendingMemoryAdd, PendingMemoryDelete, PendingMemoryEdit
from packages.memory import (
    AddMemoryResult,
    AddMemoryStatus,
    DeleteMemoryStatus,
    EditMemoryStatus,
)


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
