from collections.abc import Callable

from apps.cli.action_coordinator import CliActionCoordinator
from apps.cli.command_parser import parse_input
from apps.cli.commands import ChatMessage, ExitCommand, InvalidCommand, MemoryCommand
from apps.cli.confirmation import ConfirmationInterpreter
from apps.cli.handler_result import HandlerResult
from apps.cli.handlers import (
    NaturalFileReadHandler,
    NaturalFileSearchHandler,
    NaturalMemoryHandler,
    handle_memory_command,
)
from capabilities.desktop import OpenWorkspaceLocationCapability
from capabilities.filesystem import (
    ListFilesCapability,
    ReadTextFileCapability,
    SearchTextCapability,
)
from capabilities.terminal import RunProjectLintCapability, RunProjectTestsCapability
from packages.conversation import (
    ConversationDecisionError,
    ConversationEvent,
    ConversationService,
    FileIntentInterpreter,
    MemoryIntentInterpreter,
    ModelProvider,
    ModelProviderError,
    ReplyDecision,
    TextSearchIntentInterpreter,
    detect_explicit_project_lint,
    is_memory_usage_question,
)
from packages.memory import MemoryRepositoryError, MemoryService


def build_banner() -> str:
    return (
        "╔══════════════════════════════════════╗\n"
        "║                 Aska                 ║\n"
        "║          Personal Local AI           ║\n"
        "╚══════════════════════════════════════╝"
    )


class CliSession:
    def __init__(
        self,
        conversation: ConversationService,
        memory_service: MemoryService,
        memory_handler: NaturalMemoryHandler,
        file_handler: NaturalFileReadHandler | None,
        file_search_handler: NaturalFileSearchHandler | None,
        actions: CliActionCoordinator,
        output_writer: Callable[[str], None],
    ) -> None:
        self._conversation = conversation
        self._memory_service = memory_service
        self._memory_handler = memory_handler
        self._file_handler = file_handler
        self._file_search_handler = file_search_handler
        self._actions = actions
        self._output_writer = output_writer

    def handle(
        self,
        parsed_input: InvalidCommand | MemoryCommand | ChatMessage,
        user_input: str,
    ) -> None:
        if isinstance(parsed_input, InvalidCommand):
            self._render(
                HandlerResult("cli", "invalid_command", {"usage": parsed_input.usage}),
                user_input,
            )
            return
        if isinstance(parsed_input, MemoryCommand):
            self._handle_memory_command(parsed_input, user_input)
            return
        self._handle_chat_message(parsed_input)

    def _handle_memory_command(self, command: MemoryCommand, user_input: str) -> None:
        cancelled_operations = list(self._actions.cancel_pending())
        cancelled_memory = self._memory_handler.cancel_pending_for_literal_command()
        if cancelled_memory is not None:
            operation = cancelled_memory.facts.get("operation")
            if isinstance(operation, str):
                cancelled_operations.insert(0, operation)

        result = handle_memory_command(command, self._memory_service)
        if cancelled_operations:
            result = HandlerResult(
                result.domain,
                result.kind,
                {
                    **result.facts,
                    "cancelled_operations": tuple(cancelled_operations),
                },
            )
        self._render(result, user_input)

    def _handle_chat_message(self, message: ChatMessage) -> None:
        content = message.content
        if is_memory_usage_question(content):
            self._write_reply(self._conversation.present_memory_usage(content))
            return

        result = self._memory_handler.handle(content)
        if result is None and self._file_search_handler is not None:
            result = self._file_search_handler.handle(content)
        if result is None and self._file_handler is not None:
            result = self._file_handler.handle(content)
        if result is None:
            result = self._actions.handle_pending(content)
        if result is not None:
            self._render(result, content)
            return

        explicit_lint = detect_explicit_project_lint(content)
        if explicit_lint is not None:
            self._render(self._actions.dispatch(explicit_lint, content), content)
            return

        if self._actions.is_available:
            decision = self._conversation.decide(content)
            if isinstance(decision, ReplyDecision):
                self._write_reply(decision.content)
            else:
                self._render(self._actions.dispatch(decision, content), content)
            return

        self._write_reply(self._conversation.send(content))

    def _render(self, result: HandlerResult, user_message: str) -> None:
        if result.context_document is not None:
            response = self._conversation.send(user_message, result.context_document)
        else:
            response = self._conversation.present_event(
                user_message,
                ConversationEvent(result.domain, result.kind, result.facts),
                original_request=result.original_request,
            )
        self._write_reply(response)

    def _write_reply(self, response: str) -> None:
        self._output_writer(f"Aska > {response}")


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
    session = CliSession(
        ConversationService(model_provider, memory_service),
        memory_service,
        NaturalMemoryHandler(
            memory_service,
            memory_intent_interpreter,
            confirmation_interpreter,
        ),
        NaturalFileReadHandler(file_reader, file_intent_interpreter, file_lister)
        if file_reader is not None and file_intent_interpreter is not None
        else None,
        NaturalFileSearchHandler(file_searcher, text_search_intent_interpreter)
        if file_searcher is not None and text_search_intent_interpreter is not None
        else None,
        CliActionCoordinator.compose(
            open_location_capability,
            project_tests_capability,
            project_lint_capability,
            confirmation_interpreter,
        ),
        output_writer,
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
        try:
            session.handle(parsed_input, user_input)
        except MemoryRepositoryError as error:
            output_writer(f"Erro > Falha ao acessar memórias: {error}")
        except ModelProviderError as error:
            output_writer(f"Erro > Provider indisponível: {error}")
        except ConversationDecisionError:
            output_writer("Erro > Resposta do modelo inválida para o contrato esperado.")
