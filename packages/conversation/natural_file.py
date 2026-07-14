import json
import re
from dataclasses import dataclass
from typing import Protocol

from packages.conversation.model import ModelMessage, ModelRole
from packages.conversation.provider import ModelProvider

_FILE_READ_VERB = re.compile(
    r"\b(?:leia|ler|abra|abrir|consulte|consultar)\b|\bveja\s+o\s+arquivo\b",
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
_EXPLICIT_FILE_READ = re.compile(
    r"^\s*(?:leia|abra|consulte)\s+(?:o\s+arquivo\s+)?"
    r"(?P<path>(?:[\w.@+-]+[/\\])*[\w@+-]+(?:\.[\w@+-]+)+)"
    r"(?=$|[\s.,;:!?])",
    re.IGNORECASE,
)
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
    ) or _FILE_LIST_REQUEST.search(message) is not None


def detect_explicit_file_read(user_input: str) -> ReadTextFileIntent | None:
    message = user_input.strip()
    if not message or "\n" in message or "\r" in message:
        return None
    match = _EXPLICIT_FILE_READ.match(message)
    if match is None:
        return None
    return ReadTextFileIntent(match.group("path"))


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
