from collections.abc import Callable

from packages.conversation import PendingMemoryEdit
from packages.memory import EditMemoryStatus


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
