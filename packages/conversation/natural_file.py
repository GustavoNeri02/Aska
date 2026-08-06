import json
import re
from dataclasses import dataclass
from typing import Protocol

from packages.conversation.model import ModelMessage, ModelRole
from packages.conversation.provider import ModelProvider

_FILE_READ_VERB = re.compile(
    r"\b(?:leia|ler|abra|abrir|consulte|consultar|resuma|resumir|mostre|mostrar|"
    r"retorne|retornar)\b|\bveja\s+o\s+arquivo\b",
    re.IGNORECASE,
)
_FILE_REFERENCE = re.compile(
    r"(?:[^\s/\\]+[/\\])*[^\s/\\]+\.[^\s/\\.,;:!?]+",
    re.IGNORECASE,
)
_FILE_LIST_REQUEST = re.compile(
    r"\bquais\s+arquivos\b|"
    r"\b(?:liste|listar)\b.*\b(?:arquivos?|projeto)\b|"
    r"\b(?:localize|localizar|encontre|encontrar)\b.*"
    r"\b(?:arquivos?|roadmap|documenta[cç][aã]o)\b|"
    r"\bconsulte\s+a\s+documenta[cç][aã]o\b|"
    r"\bveja\s+quais\s+arquivos\b",
    re.IGNORECASE,
)
_FILE_LOCATION_REQUEST = re.compile(
    r"\b(?:onde\s+(?:est[aá]|fica)|qual\s+(?:[eé]\s+)?o\s+caminho)\b.*"
    r"\b(?:arquivo|documento)\b",
    re.IGNORECASE,
)
_DIRECT_FILE_ACTION = re.compile(
    r"^\s*(?:leia|abra|consulte|resuma|mostre|retorne)\b",
    re.IGNORECASE,
)
_KNOWN_DOCUMENT_REFERENCE = re.compile(
    r"\b(?:(?:o|no|do)\s+)(?:(?:documento|arquivo)\s+(?:de|das?)\s+)?"
    r"(?P<name>readme|agents|roadmap|decis[oõ]es)(?:\.md)?\b|"
    r"\b(?P<filename>readme|agents|roadmap|decis[oõ]es)\.md\b",
    re.IGNORECASE,
)
_CONTENT_QUESTION_START = re.compile(
    r"^\s*(?:qual|quais|o\s+que|como|onde|quando|por\s+que|porque)\b",
    re.IGNORECASE,
)
_KNOWN_DOCUMENT_PREDICATE = re.compile(
    r"\b(?:readme|agents|roadmap)(?:\.md)?\b.*"
    r"\b(?:diz|fala|define|menciona|orienta|explica|prev[eê]|cont[eé]m)\b",
    re.IGNORECASE,
)
_KNOWN_DOCUMENT_PATHS = {
    "readme": "README.md",
    "agents": "AGENTS.md",
    "roadmap": "roadmap.md",
    "decisões": "decisions.md",
    "decisoes": "decisions.md",
}
_INTERPRETER_INSTRUCTION = "\n".join(
    (
        "Apenas classifique o pedido. Não responda ao usuário, não leia arquivos "
        "e não acesse o filesystem.",
        "Reconheça pedidos para ler um arquivo ou descobrir caminhos de arquivos.",
        "Para leitura, extraia somente o caminho informado, relativo ao workspace.",
        "Para listagem, use diretório relativo, filtro de nome e extensão quando citados.",
        "Responda com exatamente um objeto JSON, sem Markdown ou texto adicional.",
        "Formatos permitidos:",
        '{"action":"read_text_file","path":"AGENTS.md"}',
        '{"action":"list_files","directory":".","name_contains":null,"extension":null}',
        '{"action":"none"}',
        "Exemplos:",
        "Entrada: Leia AGENTS.md e resuma as instruções principais.",
        'Saída: {"action":"read_text_file","path":"AGENTS.md"}',
        "Entrada: Localize o roadmap.",
        'Saída: {"action":"list_files","directory":".","name_contains":"roadmap","extension":null}',
        "Entrada: Veja quais arquivos Python existem.",
        'Saída: {"action":"list_files","directory":".","name_contains":null,"extension":".py"}',
        "Entrada: Onde está o arquivo de memória em JSON no projeto Aska?",
        'Saída: {"action":"list_files","directory":".","name_contains":"memori",'
        '"extension":".json"}',
        "Entrada: Explique como arquivos funcionam em Python.",
        'Saída: {"action":"none"}',
        "Não invente caminhos e não produza mais de uma ação.",
    )
)


@dataclass(frozen=True, slots=True)
class ReadTextFileIntent:
    path: str


@dataclass(frozen=True, slots=True)
class ListFilesIntent:
    directory: str = "."
    name_contains: str | None = None
    extension: str | None = None


type FileIntent = ReadTextFileIntent | ListFilesIntent


class FileIntentInterpreter(Protocol):
    def interpret(self, user_input: str) -> FileIntent | None: ...


class ModelFileIntentInterpreter:
    def __init__(self, model_provider: ModelProvider) -> None:
        self._model_provider = model_provider

    def interpret(self, user_input: str) -> FileIntent | None:
        response = self._model_provider.generate(
            [
                ModelMessage(ModelRole.SYSTEM, _INTERPRETER_INSTRUCTION),
                ModelMessage(ModelRole.USER, user_input),
            ]
        )
        return _parse_interpretation(response)


def should_interpret_file_read(user_input: str) -> bool:
    message = user_input.strip()
    if not message or "\n" in message or "\r" in message:
        return False
    return (
        _FILE_READ_VERB.search(message) is not None and _FILE_REFERENCE.search(message) is not None
    ) or (
        _FILE_LIST_REQUEST.search(message) is not None
        or _FILE_LOCATION_REQUEST.search(message) is not None
    )


def detect_explicit_file_read(user_input: str) -> ReadTextFileIntent | None:
    message = user_input.strip()
    if not message or "\n" in message or "\r" in message:
        return None
    if _DIRECT_FILE_ACTION.match(message) is None:
        return None
    match = _FILE_REFERENCE.search(message)
    if match is None:
        return None
    return ReadTextFileIntent(match.group(0))


def detect_explicit_file_location(user_input: str) -> ListFilesIntent | None:
    message = user_input.strip()
    if not message or "\n" in message or "\r" in message:
        return None
    if _FILE_LOCATION_REQUEST.search(message) is None:
        return None
    match = _FILE_REFERENCE.search(message)
    if match is None or "/" in match.group(0) or "\\" in match.group(0):
        return None
    return ListFilesIntent(name_contains=match.group(0))


def detect_known_document_query(user_input: str) -> ReadTextFileIntent | None:
    message = user_input.strip()
    if not message or "\n" in message or "\r" in message:
        return None
    reference = _KNOWN_DOCUMENT_REFERENCE.search(message)
    if reference is None or (
        _CONTENT_QUESTION_START.search(message) is None
        and _KNOWN_DOCUMENT_PREDICATE.search(message) is None
        and _DIRECT_FILE_ACTION.match(message) is None
    ):
        return None
    document_name = reference.group("name") or reference.group("filename")
    return ReadTextFileIntent(_KNOWN_DOCUMENT_PATHS[document_name.casefold()])


def _parse_interpretation(response: str) -> FileIntent | None:
    try:
        data = json.loads(response)
    except (json.JSONDecodeError, TypeError):
        return None

    if data == {"action": "none"}:
        return None
    if not isinstance(data, dict):
        return None
    if data.get("action") == "read_text_file":
        return _parse_read_intent(data)
    if data.get("action") == "list_files":
        return _parse_list_intent(data)
    return None


def _parse_read_intent(data: dict[object, object]) -> ReadTextFileIntent | None:
    if set(data) != {"action", "path"}:
        return None

    path = data.get("path")
    if not isinstance(path, str):
        return None
    normalized_path = path.strip()
    if (
        not normalized_path
        or "\n" in normalized_path
        or "\r" in normalized_path
        or "\0" in normalized_path
    ):
        return None
    return ReadTextFileIntent(normalized_path)


def _parse_list_intent(data: dict[object, object]) -> ListFilesIntent | None:
    if set(data) != {"action", "directory", "name_contains", "extension"}:
        return None
    directory = _validated_text(data.get("directory"), required=True)
    name_contains = _validated_text(data.get("name_contains"), required=False)
    extension = _validated_text(data.get("extension"), required=False)
    if not isinstance(directory, str) or name_contains is False or extension is False:
        return None
    return ListFilesIntent(
        directory=directory,
        name_contains=name_contains if isinstance(name_contains, str) else None,
        extension=extension if isinstance(extension, str) else None,
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
