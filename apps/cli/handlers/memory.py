from collections.abc import Callable

from apps.cli.commands import (
    EditMemoryCommand,
    ForgetMemoryCommand,
    ListMemoriesCommand,
    MemoryCommand,
    RememberMemoryCommand,
    SearchMemoryCommand,
)
from packages.memory import AddMemoryStatus, EditMemoryStatus, MemoryService


def handle_memory_command(
    command: MemoryCommand,
    memory_service: MemoryService,
    output_writer: Callable[[str], None],
) -> None:
    if isinstance(command, ListMemoriesCommand):
        _list_memories(memory_service, output_writer)
    elif isinstance(command, RememberMemoryCommand):
        _remember(command, memory_service, output_writer)
    elif isinstance(command, ForgetMemoryCommand):
        _forget(command, memory_service, output_writer)
    elif isinstance(command, EditMemoryCommand):
        _edit(command, memory_service, output_writer)
    elif isinstance(command, SearchMemoryCommand):
        _search(command, memory_service, output_writer)


def _list_memories(memory_service: MemoryService, output_writer: Callable[[str], None]) -> None:
    memories = memory_service.list()
    output_writer("Memórias locais:")
    if not memories:
        output_writer("(nenhuma memória registrada)")
        return
    for memory in memories:
        output_writer(memory.content)


def _remember(
    command: RememberMemoryCommand,
    memory_service: MemoryService,
    output_writer: Callable[[str], None],
) -> None:
    add_result = memory_service.add(command.content)
    if add_result.status is AddMemoryStatus.ADDED:
        output_writer("Memória registrada localmente.")
    elif add_result.status is AddMemoryStatus.DUPLICATE:
        output_writer("Já existe uma memória com esse conteúdo.")


def _forget(
    command: ForgetMemoryCommand,
    memory_service: MemoryService,
    output_writer: Callable[[str], None],
) -> None:
    if memory_service.delete(command.content):
        output_writer("Memória removida localmente.")
    else:
        output_writer("Nenhuma memória correspondente foi encontrada.")


def _edit(
    command: EditMemoryCommand,
    memory_service: MemoryService,
    output_writer: Callable[[str], None],
) -> None:
    status = memory_service.edit(command.current_content, command.new_content)
    status_messages = {
        EditMemoryStatus.EDITED: "Memória editada localmente.",
        EditMemoryStatus.NOT_FOUND: "Nenhuma memória correspondente foi encontrada.",
        EditMemoryStatus.DUPLICATE: "Já existe uma memória com esse conteúdo.",
        EditMemoryStatus.INVALID: "Informe a memória atual e o novo conteúdo.",
        EditMemoryStatus.UNCHANGED: "A memória já possui esse conteúdo.",
    }
    output_writer(status_messages[status])


def _search(
    command: SearchMemoryCommand,
    memory_service: MemoryService,
    output_writer: Callable[[str], None],
) -> None:
    matches = memory_service.search(command.term)
    if not matches:
        output_writer("Nenhuma memória encontrada para o termo.")
        return
    output_writer("Resultados da busca:")
    for memory in matches:
        output_writer(memory.content)
