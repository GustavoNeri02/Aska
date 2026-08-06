import json
import re
from dataclasses import dataclass
from typing import Protocol

from packages.conversation.model import ModelMessage, ModelRole
from packages.conversation.provider import ModelProvider

_QUOTED_TEXT_SEARCH = re.compile(
    r"\b(?:busque|procure|pesquise|encontre)\s+[\"“](?P<query>[^\"”]+)[\"”]",
    re.IGNORECASE,
)
_PYTHON_SCOPE = re.compile(r"\b(?:arquivos?|c[oó]digo)\s+python\b|\.py\b", re.IGNORECASE)
_TEXT_SEARCH_REQUEST = re.compile(
    r"\b(?:procure|busque|pesquise|encontre)\b.*"
    r"\b(?:arquivos?|documentos?|documenta[cç][aã]o|projeto|c[oó]digo)\b|"
    r"\bonde\b.*\b(?:projeto|documenta[cç][aã]o|documentos?|arquivos?)\b.*"
    r"\b(?:fala|menciona|define|cont[eé]m)\b|"
    r"\bquais\s+arquivos\b.*\b(?:mencionam|cont[eê]m|possuem)\b",
    re.IGNORECASE,
)
_INTERPRETER_INSTRUCTION = "\n".join(
    (
        "Apenas classifique o pedido. Não responda ao usuário e não acesse o filesystem.",
        "Reconheça somente pedidos explícitos para buscar texto dentro de arquivos.",
        "Extraia uma consulta literal curta, um diretório relativo e uma extensão opcional.",
        "Responda com exatamente um objeto JSON, sem Markdown ou texto adicional.",
        "Formatos permitidos:",
        '{"action":"search_text","query":"SQLite","directory":"docs","extension":".md"}',
        '{"action":"none"}',
        "Exemplos:",
        "Entrada: Procure referências a SQLite nos documentos.",
        'Saída: {"action":"search_text","query":"SQLite","directory":"docs","extension":".md"}',
        "Entrada: Onde o projeto fala sobre busca vetorial?",
        'Saída: {"action":"search_text","query":"busca vetorial","directory":".","extension":null}',
        "Entrada: Quais arquivos mencionam tool calling?",
        'Saída: {"action":"search_text","query":"tool calling","directory":".","extension":null}',
        "Entrada: Quais arquivos existem no projeto?",
        'Saída: {"action":"none"}',
        "Não invente conteúdo, caminhos ou mais de uma ação.",
    )
)


@dataclass(frozen=True, slots=True)
class SearchTextIntent:
    query: str
    directory: str = "."
    extension: str | None = None


class TextSearchIntentInterpreter(Protocol):
    def interpret(self, user_input: str) -> SearchTextIntent | None: ...


class ModelTextSearchIntentInterpreter:
    def __init__(self, model_provider: ModelProvider) -> None:
        self._model_provider = model_provider

    def interpret(self, user_input: str) -> SearchTextIntent | None:
        response = self._model_provider.generate(
            [
                ModelMessage(ModelRole.SYSTEM, _INTERPRETER_INSTRUCTION),
                ModelMessage(ModelRole.USER, user_input),
            ]
        )
        return _parse_interpretation(response)


def detect_explicit_text_search(user_input: str) -> SearchTextIntent | None:
    message = user_input.strip()
    if not message or "\n" in message or "\r" in message:
        return None
    match = _QUOTED_TEXT_SEARCH.search(message)
    if match is None:
        return None
    query = match.group("query").strip()
    if not query:
        return None
    extension = ".py" if _PYTHON_SCOPE.search(message) is not None else None
    return SearchTextIntent(query, extension=extension)


def should_interpret_text_search(user_input: str) -> bool:
    message = user_input.strip()
    return bool(
        message
        and "\n" not in message
        and "\r" not in message
        and _TEXT_SEARCH_REQUEST.search(message) is not None
    )


def _parse_interpretation(response: str) -> SearchTextIntent | None:
    try:
        data = json.loads(response)
    except (json.JSONDecodeError, TypeError):
        return None
    if data == {"action": "none"}:
        return None
    if not isinstance(data, dict) or set(data) != {
        "action",
        "query",
        "directory",
        "extension",
    }:
        return None
    if data.get("action") != "search_text":
        return None
    query = _validated_text(data.get("query"), required=True)
    directory = _validated_text(data.get("directory"), required=True)
    extension = _validated_text(data.get("extension"), required=False)
    if not isinstance(query, str) or not isinstance(directory, str) or extension is False:
        return None
    return SearchTextIntent(
        query,
        directory,
        extension if isinstance(extension, str) else None,
    )


def _validated_text(value: object, *, required: bool) -> str | None | bool:
    if value is None:
        return False if required else None
    if not isinstance(value, str):
        return False
    normalized = value.strip()
    if not normalized or any(marker in normalized for marker in ("\0", "\n", "\r")):
        return False
    return normalized
