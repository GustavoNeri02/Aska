from collections.abc import Callable

from capabilities.filesystem import (
    ReadTextFileCapability,
    ReadTextFileStatus,
)
from packages.conversation import (
    ContextDocument,
    ConversationService,
    FileIntentInterpreter,
    ReadTextFileIntent,
    should_interpret_file_read,
)


class NaturalFileReadHandler:
    def __init__(
        self,
        file_reader: ReadTextFileCapability,
        file_intent_interpreter: FileIntentInterpreter,
        conversation_service: ConversationService,
        output_writer: Callable[[str], None],
    ) -> None:
        self._file_reader = file_reader
        self._file_intent_interpreter = file_intent_interpreter
        self._conversation_service = conversation_service
        self._output_writer = output_writer

    def handle(self, user_input: str) -> bool:
        if not should_interpret_file_read(user_input):
            return False

        intent = self._file_intent_interpreter.interpret(user_input)
        if not isinstance(intent, ReadTextFileIntent):
            return False

        result = self._file_reader.read(intent.path)
        if result.status is not ReadTextFileStatus.SUCCESS:
            self._output_writer(_read_error_message(result.status))
            return True

        if result.relative_path is None or result.content is None:
            raise RuntimeError("successful file read returned no content")
        response = self._conversation_service.send(
            user_input,
            context_document=ContextDocument(
                source=result.relative_path,
                content=result.content,
            ),
        )
        self._output_writer(f"Aska > {response}")
        return True


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
