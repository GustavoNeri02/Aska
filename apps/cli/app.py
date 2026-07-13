import os
from collections.abc import Callable

from apps.cli.parser import (
    ChatMessage,
    EditMemoryCommand,
    ExitCommand,
    ForgetMemoryCommand,
    ListMemoriesCommand,
    RememberMemoryCommand,
    SearchMemoryCommand,
    parse_input,
)
from packages.conversation import ConversationService, ModelProvider, ModelProviderError
from packages.inference import OllamaProvider
from packages.memory import (
    AddMemoryStatus,
    EditMemoryStatus,
    JsonMemoryDataSource,
    LocalMemoryRepository,
    MemoryRepositoryError,
    MemoryService,
)


def build_banner() -> str:
    return (
        "╔══════════════════════════════════════╗\n"
        "║                 Aska                 ║\n"
        "║          Personal Local AI           ║\n"
        "╚══════════════════════════════════════╝"
    )


def run_conversation_loop(
    model_provider: ModelProvider,
    memory_service: MemoryService,
    input_reader: Callable[[str], str] = input,
    output_writer: Callable[[str], None] = print,
) -> None:
    output_writer(build_banner())
    output_writer("")
    output_writer("Olá, Gustavo.")
    output_writer("")
    output_writer("Digite 'sair' para encerrar.")
    output_writer("")
    conversation_service = ConversationService(model_provider, memory_service)

    while True:
        try:
            user_input = input_reader("Você > ").strip()
        except (EOFError, KeyboardInterrupt):
            output_writer("\nEncerrando o Aska.")
            return

        if not user_input:
            continue

        parsed_input = parse_input(user_input)
        if isinstance(parsed_input, ExitCommand):
            output_writer("Até mais, Gustavo.")
            return

        try:
            if isinstance(parsed_input, ListMemoriesCommand):
                _list_memories(memory_service, output_writer)
            elif isinstance(parsed_input, RememberMemoryCommand):
                _remember(parsed_input, memory_service, output_writer)
            elif isinstance(parsed_input, ForgetMemoryCommand):
                _forget(parsed_input, memory_service, output_writer)
            elif isinstance(parsed_input, EditMemoryCommand):
                _edit(parsed_input, memory_service, output_writer)
            elif isinstance(parsed_input, SearchMemoryCommand):
                _search(parsed_input, memory_service, output_writer)
            elif isinstance(parsed_input, ChatMessage):
                response = conversation_service.send(parsed_input.content)
                output_writer(f"Aska > {response}")
        except MemoryRepositoryError as error:
            output_writer(f"Não foi possível acessar as memórias: {error}")
        except ModelProviderError as error:
            output_writer(f"Aska > {error}")


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
    if not command.content:
        return
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
    if not command.content:
        return
    if memory_service.delete(command.content):
        output_writer("Memória removida localmente.")
    else:
        output_writer("Nenhuma memória correspondente foi encontrada.")


def _edit(
    command: EditMemoryCommand,
    memory_service: MemoryService,
    output_writer: Callable[[str], None],
) -> None:
    if command.is_malformed:
        output_writer("Use: editar memória: <atual> -> <novo>")
        return
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
    if not command.term:
        output_writer("Use: buscar memória: <termo>")
        return
    matches = memory_service.search(command.term)
    if not matches:
        output_writer("Nenhuma memória encontrada para o termo.")
        return
    output_writer("Resultados da busca:")
    for memory in matches:
        output_writer(memory.content)


def main() -> None:
    model_provider = OllamaProvider(
        model=os.getenv("ASKA_MODEL", "gemma3:12b"),
        base_url=os.getenv("ASKA_OLLAMA_URL", "http://localhost:11434"),
    )
    memory_data_source = JsonMemoryDataSource("data/memory/memories.json")
    memory_repository = LocalMemoryRepository(memory_data_source)
    memory_service = MemoryService(memory_repository)
    run_conversation_loop(model_provider, memory_service=memory_service)


if __name__ == "__main__":
    main()
