import os
from collections.abc import Callable
from contextlib import suppress
from pathlib import Path

from apps.cli.command_parser import parse_input
from apps.cli.commands import ChatMessage, ExitCommand, InvalidCommand, MemoryCommand
from apps.cli.handlers import (
    NaturalFileReadHandler,
    NaturalFileSearchHandler,
    NaturalMemoryHandler,
    NaturalOpenLocationHandler,
    handle_memory_command,
)
from apps.cli.loading import run_with_loading
from capabilities.desktop import OpenWorkspaceLocationCapability, WindowsExplorerLauncher
from capabilities.filesystem import (
    ListFilesCapability,
    ReadTextFileCapability,
    SearchTextCapability,
)
from packages.conversation import (
    ConversationDecisionError,
    ConversationService,
    FileIntentInterpreter,
    MemoryIntentInterpreter,
    ModelFileIntentInterpreter,
    ModelMemoryIntentInterpreter,
    ModelProvider,
    ModelProviderError,
    ModelTextSearchIntentInterpreter,
    OpenWorkspaceLocationProposal,
    ReplyDecision,
    TextSearchIntentInterpreter,
)
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
    memory_intent_interpreter: MemoryIntentInterpreter | None = None,
    file_reader: ReadTextFileCapability | None = None,
    file_lister: ListFilesCapability | None = None,
    file_intent_interpreter: FileIntentInterpreter | None = None,
    file_searcher: SearchTextCapability | None = None,
    text_search_intent_interpreter: TextSearchIntentInterpreter | None = None,
    open_location_capability: OpenWorkspaceLocationCapability | None = None,
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
    natural_memory_handler = NaturalMemoryHandler(
        memory_service,
        memory_intent_interpreter,
        output_writer,
    )
    natural_file_handler = (
        NaturalFileReadHandler(
            file_reader,
            file_intent_interpreter,
            conversation_service,
            output_writer,
            file_lister,
        )
        if file_reader is not None and file_intent_interpreter is not None
        else None
    )
    natural_file_search_handler = (
        NaturalFileSearchHandler(
            file_searcher,
            text_search_intent_interpreter,
            conversation_service,
            output_writer,
        )
        if file_searcher is not None and text_search_intent_interpreter is not None
        else None
    )
    natural_open_location_handler = (
        NaturalOpenLocationHandler(
            open_location_capability,
            output_writer,
        )
        if open_location_capability is not None
        else None
    )

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
                natural_memory_handler.cancel_pending_for_literal_command()
                if natural_open_location_handler is not None:
                    natural_open_location_handler.cancel_pending_for_literal_command()
                handle_memory_command(parsed_input, memory_service, output_writer)
            elif isinstance(parsed_input, ChatMessage):
                if natural_memory_handler.handle(parsed_input.content):
                    continue
                if natural_file_search_handler is not None and natural_file_search_handler.handle(
                    parsed_input.content
                ):
                    continue
                if natural_file_handler is not None and natural_file_handler.handle(
                    parsed_input.content
                ):
                    continue
                if natural_open_location_handler is not None and (
                    natural_open_location_handler.handle(parsed_input.content)
                ):
                    continue
                if natural_open_location_handler is not None:
                    decision = conversation_service.decide(parsed_input.content)
                    if isinstance(decision, ReplyDecision):
                        output_writer(f"Aska > {decision.content}")
                    elif isinstance(decision, OpenWorkspaceLocationProposal):
                        natural_open_location_handler.handle_proposal(decision)
                    continue
                response = conversation_service.send(parsed_input.content)
                output_writer(f"Aska > {response}")
        except MemoryRepositoryError as error:
            output_writer(f"Não foi possível acessar as memórias: {error}")
        except ModelProviderError as error:
            output_writer(f"Aska > {error}")
        except ConversationDecisionError:
            output_writer(
                "Aska > Não foi possível interpretar a resposta do modelo com segurança."
            )


def main() -> None:
    try:
        workspace_root = Path(os.getenv("ASKA_WORKSPACE_ROOT", str(Path.cwd()))).resolve(
            strict=True
        )
        file_reader = ReadTextFileCapability(workspace_root)
        file_lister = ListFilesCapability(workspace_root)
        file_searcher = SearchTextCapability(workspace_root)
    except (OSError, ValueError):
        print("Aska > Workspace de leitura inválido.")
        return
    try:
        open_location_capability = OpenWorkspaceLocationCapability(
            workspace_root,
            WindowsExplorerLauncher(),
        )
    except ValueError:
        open_location_capability = None

    model = os.getenv("ASKA_MODEL", "gemma3:12b")
    model_provider = OllamaProvider(
        model=model,
        base_url=os.getenv("ASKA_OLLAMA_URL", "http://localhost:11434"),
    )
    memory_data_source = JsonMemoryDataSource("data/memory/memories.json")
    memory_repository = LocalMemoryRepository(memory_data_source)
    memory_service = MemoryService(memory_repository)
    memory_intent_interpreter = ModelMemoryIntentInterpreter(model_provider)
    file_intent_interpreter = ModelFileIntentInterpreter(model_provider)
    text_search_intent_interpreter = ModelTextSearchIntentInterpreter(model_provider)

    try:
        try:
            run_with_loading(model_provider.warm_up, f"Carregando {model}...")
        except ModelProviderError as error:
            print(f"Aska > {error}")
            return
        run_conversation_loop(
            model_provider,
            memory_service=memory_service,
            memory_intent_interpreter=memory_intent_interpreter,
            file_reader=file_reader,
            file_lister=file_lister,
            file_intent_interpreter=file_intent_interpreter,
            file_searcher=file_searcher,
            text_search_intent_interpreter=text_search_intent_interpreter,
            open_location_capability=open_location_capability,
        )
    finally:
        with suppress(ModelProviderError):
            model_provider.unload()


if __name__ == "__main__":
    main()
