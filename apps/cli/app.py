import os
from collections.abc import Callable
from contextlib import suppress
from pathlib import Path

from apps.cli.action_coordinator import CliActionCoordinator
from apps.cli.command_parser import parse_input
from apps.cli.commands import ChatMessage, ExitCommand, InvalidCommand, MemoryCommand
from apps.cli.confirmation import ConfirmationInterpreter, ModelConfirmationInterpreter
from apps.cli.handler_result import HandlerResult
from apps.cli.handlers import (
    NaturalFileReadHandler,
    NaturalFileSearchHandler,
    NaturalMemoryHandler,
    handle_memory_command,
)
from apps.cli.loading import run_with_loading
from capabilities.desktop import OpenWorkspaceLocationCapability, WindowsExplorerLauncher
from capabilities.filesystem import (
    ListFilesCapability,
    ReadTextFileCapability,
    SearchTextCapability,
)
from capabilities.terminal import (
    PythonModuleRunner,
    PythonProjectTestRunner,
    RunProjectLintCapability,
    RunProjectTestsCapability,
)
from packages.conversation import (
    ConversationDecisionError,
    ConversationEvent,
    ConversationService,
    FileIntentInterpreter,
    MemoryIntentInterpreter,
    ModelFileIntentInterpreter,
    ModelMemoryIntentInterpreter,
    ModelProvider,
    ModelProviderError,
    ModelTextSearchIntentInterpreter,
    ReplyDecision,
    TextSearchIntentInterpreter,
    detect_explicit_project_lint,
    is_memory_usage_question,
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
    project_tests_capability: RunProjectTestsCapability | None = None,
    project_lint_capability: RunProjectLintCapability | None = None,
    confirmation_interpreter: ConfirmationInterpreter | None = None,
    input_reader: Callable[[str], str] = input,
    output_writer: Callable[[str], None] = print,
) -> None:
    output_writer(build_banner())
    output_writer("")
    conversation_service = ConversationService(model_provider, memory_service)

    natural_memory_handler = NaturalMemoryHandler(
        memory_service,
        memory_intent_interpreter,
        confirmation_interpreter,
    )
    natural_file_handler = (
        NaturalFileReadHandler(
            file_reader,
            file_intent_interpreter,
            file_lister,
        )
        if file_reader is not None and file_intent_interpreter is not None
        else None
    )
    natural_file_search_handler = (
        NaturalFileSearchHandler(
            file_searcher,
            text_search_intent_interpreter,
        )
        if file_searcher is not None and text_search_intent_interpreter is not None
        else None
    )
    action_coordinator = CliActionCoordinator.compose(
        open_location_capability,
        project_tests_capability,
        project_lint_capability,
        confirmation_interpreter,
    )

    while True:
        try:
            user_input = input_reader("Você > ").strip()
        except (EOFError, KeyboardInterrupt):
            return

        if not user_input:
            continue

        parsed_input = parse_input(user_input)
        if isinstance(parsed_input, ExitCommand):
            return
        if isinstance(parsed_input, InvalidCommand):
            _render_handler_result(
                HandlerResult("cli", "invalid_command", {"usage": parsed_input.usage}),
                user_input,
                conversation_service,
                output_writer,
            )
            continue

        try:
            if isinstance(parsed_input, MemoryCommand):
                cancelled = natural_memory_handler.cancel_pending_for_literal_command()
                cancelled_operations = list(action_coordinator.cancel_pending())
                if cancelled is not None:
                    operation = cancelled.facts.get("operation")
                    if isinstance(operation, str):
                        cancelled_operations.insert(0, operation)
                handler_result = handle_memory_command(parsed_input, memory_service)
                if cancelled_operations:
                    handler_result = HandlerResult(
                        handler_result.domain,
                        handler_result.kind,
                        {
                            **handler_result.facts,
                            "cancelled_operations": tuple(cancelled_operations),
                        },
                    )
                _render_handler_result(
                    handler_result,
                    user_input,
                    conversation_service,
                    output_writer,
                )
            elif isinstance(parsed_input, ChatMessage):
                if is_memory_usage_question(parsed_input.content):
                    response = conversation_service.present_memory_usage(parsed_input.content)
                    output_writer(f"Aska > {response}")
                    continue
                if (
                    handler_result := natural_memory_handler.handle(parsed_input.content)
                ) is not None:
                    _render_handler_result(
                        handler_result, parsed_input.content, conversation_service, output_writer
                    )
                    continue
                if (
                    natural_file_search_handler is not None
                    and (handler_result := natural_file_search_handler.handle(parsed_input.content))
                    is not None
                ):
                    _render_handler_result(
                        handler_result,
                        parsed_input.content,
                        conversation_service,
                        output_writer,
                    )
                    continue
                if (
                    natural_file_handler is not None
                    and (handler_result := natural_file_handler.handle(parsed_input.content))
                    is not None
                ):
                    _render_handler_result(
                        handler_result,
                        parsed_input.content,
                        conversation_service,
                        output_writer,
                    )
                    continue
                if (
                    handler_result := action_coordinator.handle_pending(parsed_input.content)
                ) is not None:
                    _render_handler_result(
                        handler_result,
                        parsed_input.content,
                        conversation_service,
                        output_writer,
                    )
                    continue
                explicit_lint = detect_explicit_project_lint(parsed_input.content)
                if explicit_lint is not None:
                    handler_result = action_coordinator.dispatch(
                        explicit_lint, parsed_input.content
                    )
                    _render_handler_result(
                        handler_result,
                        parsed_input.content,
                        conversation_service,
                        output_writer,
                    )
                    continue
                if action_coordinator.is_available:
                    decision = conversation_service.decide(parsed_input.content)
                    if isinstance(decision, ReplyDecision):
                        output_writer(f"Aska > {decision.content}")
                    else:
                        handler_result = action_coordinator.dispatch(decision, parsed_input.content)
                        _render_handler_result(
                            handler_result,
                            parsed_input.content,
                            conversation_service,
                            output_writer,
                        )
                    continue
                response = conversation_service.send(parsed_input.content)
                output_writer(f"Aska > {response}")
        except MemoryRepositoryError as error:
            output_writer(f"Erro > Falha ao acessar memórias: {error}")
        except ModelProviderError as error:
            output_writer(f"Erro > Provider indisponível: {error}")
        except ConversationDecisionError:
            output_writer("Erro > Resposta do modelo inválida para o contrato esperado.")


def _render_handler_result(
    result: HandlerResult,
    user_message: str,
    conversation_service: ConversationService,
    output_writer: Callable[[str], None],
) -> None:
    if result.context_document is not None:
        response = conversation_service.send(user_message, result.context_document)
    else:
        response = conversation_service.present_event(
            user_message,
            ConversationEvent(result.domain, result.kind, result.facts),
            original_request=result.original_request,
        )
    output_writer(f"Aska > {response}")


def main() -> None:
    try:
        workspace_root = Path(os.getenv("ASKA_WORKSPACE_ROOT", str(Path.cwd()))).resolve(
            strict=True
        )
        file_reader = ReadTextFileCapability(workspace_root)
        file_lister = ListFilesCapability(workspace_root)
        file_searcher = SearchTextCapability(workspace_root)
    except (OSError, ValueError):
        print("Erro > Workspace de leitura inválido.")
        return
    try:
        open_location_capability = OpenWorkspaceLocationCapability(
            workspace_root,
            WindowsExplorerLauncher(),
        )
    except ValueError:
        open_location_capability = None
    try:
        project_tests_capability = RunProjectTestsCapability(
            workspace_root,
            PythonProjectTestRunner(),
        )
    except ValueError:
        project_tests_capability = None
    try:
        project_lint_capability = RunProjectLintCapability(
            workspace_root,
            PythonModuleRunner("ruff", ("check", ".")),
        )
    except ValueError:
        project_lint_capability = None

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
    confirmation_interpreter = ModelConfirmationInterpreter(model_provider)

    try:
        try:
            run_with_loading(model_provider.warm_up, f"Carregando {model}...")
        except ModelProviderError as error:
            print(f"Erro > Provider indisponível: {error}")
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
            project_tests_capability=project_tests_capability,
            project_lint_capability=project_lint_capability,
            confirmation_interpreter=confirmation_interpreter,
        )
    finally:
        with suppress(ModelProviderError):
            model_provider.unload()


if __name__ == "__main__":
    main()
