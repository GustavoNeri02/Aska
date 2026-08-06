from apps.cli.handler_result import HandlerResult
from capabilities.filesystem import SearchTextCapability, SearchTextStatus
from packages.conversation import (
    ContextDocument,
    TextSearchIntentInterpreter,
    detect_explicit_text_search,
    should_interpret_text_search,
)


class NaturalFileSearchHandler:
    def __init__(
        self,
        file_searcher: SearchTextCapability,
        intent_interpreter: TextSearchIntentInterpreter,
    ) -> None:
        self._file_searcher = file_searcher
        self._intent_interpreter = intent_interpreter

    def handle(self, user_input: str) -> HandlerResult | None:
        intent = detect_explicit_text_search(user_input)
        if intent is None:
            if not should_interpret_text_search(user_input):
                return None
            intent = self._intent_interpreter.interpret(user_input)
        if intent is None:
            return None
        result = self._file_searcher.search(
            intent.query, directory=intent.directory, extension=intent.extension
        )
        facts = {
            "status": result.status.value,
            "query": intent.query,
            "matches": tuple(
                {
                    "path": match.relative_path,
                    "line": match.line_number,
                    "snippet": match.snippet,
                }
                for match in result.matches
            ),
        }
        context = None
        if (
            result.status in {SearchTextStatus.SUCCESS, SearchTextStatus.LIMIT_REACHED}
            and result.matches
        ):
            context = ContextDocument(
                source="busca textual segura no workspace",
                content="\n".join(
                    f"- {match.relative_path}:{match.line_number}: {match.snippet}"
                    for match in result.matches
                ),
            )
        return HandlerResult("filesystem", "text_search", facts, context)
