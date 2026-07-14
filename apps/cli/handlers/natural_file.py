from collections.abc import Callable

from capabilities.filesystem import (
    TextFileReader,
    TextFileReadError,
    TextFileReadErrorCode,
)
from packages.conversation import (
    ConversationService,
    FileIntentInterpreter,
    ReadTextFileIntent,
    TemporaryContext,
    should_interpret_file_read,
)


class NaturalFileReadHandler:
    def __init__(
        self,
        file_reader: TextFileReader,
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

        try:
            file_content = self._file_reader.read(intent.path)
        except TextFileReadError as error:
            self._output_writer(_read_error_message(error.code))
            return True

        response = self._conversation_service.send(
            user_input,
            temporary_context=TemporaryContext(
                source=file_content.relative_path,
                content=file_content.content,
            ),
        )
        self._output_writer(f"Aska > {response}")
        return True


def _read_error_message(code: TextFileReadErrorCode) -> str:
    messages = {
        TextFileReadErrorCode.INVALID_PATH: "O caminho informado não é válido.",
        TextFileReadErrorCode.OUTSIDE_WORKSPACE: (
            "Acesso negado: o arquivo deve estar dentro do workspace permitido."
        ),
        TextFileReadErrorCode.NOT_FOUND: "O arquivo informado não foi encontrado.",
        TextFileReadErrorCode.NOT_FILE: "O caminho informado não aponta para um arquivo.",
        TextFileReadErrorCode.TOO_LARGE: "O arquivo excede o limite de leitura permitido.",
        TextFileReadErrorCode.NOT_TEXT: "O arquivo não é um texto UTF-8 válido.",
        TextFileReadErrorCode.EMPTY: "O arquivo está vazio.",
        TextFileReadErrorCode.UNREADABLE: "Não foi possível ler o arquivo informado.",
    }
    return messages[code]
