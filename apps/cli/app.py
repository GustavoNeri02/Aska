import os
from collections.abc import Callable
from contextlib import suppress

from apps.cli.command_parser import parse_input
from apps.cli.commands import ChatMessage, ExitCommand, InvalidCommand, MemoryCommand
from apps.cli.handlers import handle_memory_command
from apps.cli.loading import run_with_loading
from packages.conversation import ConversationService, ModelProvider, ModelProviderError
from packages.inference import OllamaProvider
from packages.memory import (
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
        if isinstance(parsed_input, InvalidCommand):
            output_writer(parsed_input.usage)
            continue

        try:
            if isinstance(parsed_input, MemoryCommand):
                handle_memory_command(parsed_input, memory_service, output_writer)
            elif isinstance(parsed_input, ChatMessage):
                response = conversation_service.send(parsed_input.content)
                output_writer(f"Aska > {response}")
        except MemoryRepositoryError as error:
            output_writer(f"Não foi possível acessar as memórias: {error}")
        except ModelProviderError as error:
            output_writer(f"Aska > {error}")


def main() -> None:
    model = os.getenv("ASKA_MODEL", "gemma3:12b")
    model_provider = OllamaProvider(
        model=model,
        base_url=os.getenv("ASKA_OLLAMA_URL", "http://localhost:11434"),
    )
    memory_data_source = JsonMemoryDataSource("data/memory/memories.json")
    memory_repository = LocalMemoryRepository(memory_data_source)
    memory_service = MemoryService(memory_repository)

    try:
        try:
            run_with_loading(model_provider.warm_up, f"Carregando {model}...")
        except ModelProviderError as error:
            print(f"Aska > {error}")
            return
        run_conversation_loop(model_provider, memory_service=memory_service)
    finally:
        with suppress(ModelProviderError):
            model_provider.unload()


if __name__ == "__main__":
    main()
