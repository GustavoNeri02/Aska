from collections.abc import Callable

from capabilities.filesystem import (
    ListFilesCapability,
    ListFilesStatus,
    ReadTextFileCapability,
    ReadTextFileStatus,
)
from packages.conversation import (
    ContextDocument,
    ConversationService,
    FileIntentInterpreter,
    ListFilesIntent,
    ReadTextFileIntent,
    detect_explicit_file_read,
    should_interpret_file_read,
)


class NaturalFileReadHandler:
    def __init__(
        self,
        file_reader: ReadTextFileCapability,
        file_intent_interpreter: FileIntentInterpreter,
        conversation_service: ConversationService,
        output_writer: Callable[[str], None],
        file_lister: ListFilesCapability | None = None,
    ) -> None:
        self._file_reader = file_reader
        self._file_intent_interpreter = file_intent_interpreter
        self._conversation_service = conversation_service
        self._output_writer = output_writer
        self._file_lister = file_lister

    def handle(self, user_input: str) -> bool:
        intent = detect_explicit_file_read(user_input)
        if intent is None:
            if not should_interpret_file_read(user_input):
                return False
            intent = self._file_intent_interpreter.interpret(user_input)
        if isinstance(intent, ReadTextFileIntent):
            return self._handle_read(user_input, intent)
        if isinstance(intent, ListFilesIntent) and self._file_lister is not None:
            return self._handle_list(user_input, intent)
        return False

    def _handle_read(self, user_input: str, intent: ReadTextFileIntent) -> bool:
        result = self._file_reader.read(intent.path)
        if result.status is not ReadTextFileStatus.SUCCESS:
            self._output_writer(_read_error_message(result.status))
            return True

        if result.relative_path is None or result.content is None:
            raise RuntimeError("successful file read returned no content")
        self._send_with_context(
            user_input,
            source=result.relative_path,
            content=result.content,
        )
        return True

    def _handle_list(self, user_input: str, intent: ListFilesIntent) -> bool:
        if self._file_lister is None:
            return False
        result = self._file_lister.list(
            intent.directory,
            name_contains=intent.name_contains,
            extension=intent.extension,
        )
        if result.status not in {
            ListFilesStatus.SUCCESS,
            ListFilesStatus.LIMIT_REACHED,
        }:
            self._output_writer(_list_error_message(result.status))
            return True

        listing = "\n".join(f"- {path}" for path in result.paths)
        if not listing:
            listing = "Nenhum arquivo encontrado para os filtros informados."
        elif result.status is ListFilesStatus.LIMIT_REACHED:
            listing = f"{listing}\n- Resultado truncado no limite seguro configurado."
        self._send_with_context(
            user_input,
            source="listagem segura de arquivos do workspace",
            content=listing,
        )
        return True

    def _send_with_context(self, user_input: str, *, source: str, content: str) -> None:
        response = self._conversation_service.send(
            user_input,
            context_document=ContextDocument(
                source=source,
                content=content,
            ),
        )
        self._output_writer(f"Aska > {response}")


def _read_error_message(status: ReadTextFileStatus) -> str:
    messages = {
        ReadTextFileStatus.INVALID_PATH: "O caminho informado não é válido.",
        ReadTextFileStatus.OUTSIDE_WORKSPACE: (
            "Acesso negado: o arquivo deve estar dentro do workspace permitido."
        ),
        ReadTextFileStatus.NOT_FOUND: "O arquivo informado não foi encontrado.",
        ReadTextFileStatus.NOT_FILE: "O caminho informado não aponta para um arquivo.",
        ReadTextFileStatus.TOO_LARGE: "O arquivo excede o limite de leitura permitido.",
        ReadTextFileStatus.NOT_TEXT: "O arquivo não é um texto UTF-8 válido.",
        ReadTextFileStatus.EMPTY: "O arquivo está vazio.",
        ReadTextFileStatus.READ_FAILED: "Não foi possível ler o arquivo informado.",
    }
    return messages[status]


def _list_error_message(status: ListFilesStatus) -> str:
    messages = {
        ListFilesStatus.INVALID_PATH: "O diretório informado não é válido.",
        ListFilesStatus.OUTSIDE_WORKSPACE: (
            "Acesso negado: o diretório deve estar dentro do workspace permitido."
        ),
        ListFilesStatus.NOT_FOUND: "O diretório informado não foi encontrado.",
        ListFilesStatus.NOT_DIRECTORY: ("O caminho informado não aponta para um diretório."),
        ListFilesStatus.READ_FAILED: "Não foi possível listar o diretório informado.",
    }
    return messages[status]
