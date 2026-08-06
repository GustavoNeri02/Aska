from collections.abc import Callable

from capabilities.filesystem import (
    SearchTextCapability,
    SearchTextStatus,
)
from packages.conversation import (
    ContextDocument,
    ConversationService,
    TextSearchIntentInterpreter,
    detect_explicit_text_search,
    should_interpret_text_search,
)


class NaturalFileSearchHandler:
    def __init__(
        self,
        file_searcher: SearchTextCapability,
        intent_interpreter: TextSearchIntentInterpreter,
        conversation_service: ConversationService,
        output_writer: Callable[[str], None],
    ) -> None:
        self._file_searcher = file_searcher
        self._intent_interpreter = intent_interpreter
        self._conversation_service = conversation_service
        self._output_writer = output_writer

    def handle(self, user_input: str) -> bool:
        intent = detect_explicit_text_search(user_input)
        if intent is None:
            if not should_interpret_text_search(user_input):
                return False
            intent = self._intent_interpreter.interpret(user_input)
        if intent is None:
            return False

        result = self._file_searcher.search(
            intent.query,
            directory=intent.directory,
            extension=intent.extension,
        )
        if result.status not in {
            SearchTextStatus.SUCCESS,
            SearchTextStatus.LIMIT_REACHED,
        }:
            self._output_writer(_search_error_message(result.status))
            return True
        if not result.matches:
            self._output_writer("Nenhuma ocorrência correspondente foi encontrada.")
            return True

        matches = "\n".join(
            f"- {match.relative_path}:{match.line_number}: {match.snippet}"
            for match in result.matches
        )
        if result.status is SearchTextStatus.LIMIT_REACHED:
            matches = f"{matches}\n- Resultado truncado no limite seguro configurado."
        response = self._conversation_service.send(
            user_input,
            context_document=ContextDocument(
                source="busca textual segura no workspace",
                content=matches,
            ),
        )
        self._output_writer(f"Aska > {response}")
        return True


def _search_error_message(status: SearchTextStatus) -> str:
    messages = {
        SearchTextStatus.INVALID_QUERY: "O texto de busca informado não é válido.",
        SearchTextStatus.INVALID_PATH: "O diretório de busca informado não é válido.",
        SearchTextStatus.OUTSIDE_WORKSPACE: (
            "Acesso negado: a busca deve permanecer dentro do workspace permitido."
        ),
        SearchTextStatus.NOT_FOUND: "O diretório de busca não foi encontrado.",
        SearchTextStatus.NOT_DIRECTORY: (
            "O caminho de busca informado não aponta para um diretório."
        ),
        SearchTextStatus.SEARCH_FAILED: "Não foi possível buscar texto no workspace.",
    }
    return messages[status]
