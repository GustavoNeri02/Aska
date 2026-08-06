from apps.cli.commands import (
    EditMemoryCommand,
    ForgetMemoryCommand,
    ListMemoriesCommand,
    MemoryCommand,
    RememberMemoryCommand,
    SearchMemoryCommand,
)
from apps.cli.handler_result import HandlerResult
from packages.memory import MemoryService


def handle_memory_command(
    command: MemoryCommand,
    memory_service: MemoryService,
) -> HandlerResult:
    if isinstance(command, ListMemoriesCommand):
        memories = memory_service.list()
        return HandlerResult(
            "memory", "listed", {"memories": tuple(item.content for item in memories)}
        )
    if isinstance(command, RememberMemoryCommand):
        result = memory_service.add(command.content)
        return HandlerResult("memory", "added", {"status": result.status.value})
    if isinstance(command, ForgetMemoryCommand):
        deleted = memory_service.delete(command.content)
        return HandlerResult("memory", "deleted", {"deleted": deleted})
    if isinstance(command, EditMemoryCommand):
        status = memory_service.edit(command.current_content, command.new_content)
        return HandlerResult("memory", "edited", {"status": status.value})
    if isinstance(command, SearchMemoryCommand):
        matches = memory_service.search(command.term)
        return HandlerResult(
            "memory", "searched", {"matches": tuple(item.content for item in matches)}
        )
    raise TypeError("unknown memory command")
