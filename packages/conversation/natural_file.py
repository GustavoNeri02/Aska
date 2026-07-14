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
_INTERPRETER_INSTRUCTION = "\n".join(
    (
        "Apenas classifique o pedido. Não responda ao usuário e não leia arquivos.",
        "Reconheça somente um pedido explícito para ler um único arquivo textual.",
        "Extraia somente o caminho informado pelo usuário, relativo ao workspace.",
        "Responda com exatamente um objeto JSON, sem Markdown ou texto adicional.",
        "Formatos permitidos:",
        '{"action":"read_text_file","path":"AGENTS.md"}',
        '{"action":"none"}',
        "Exemplos:",
        "Entrada: Leia AGENTS.md e resuma as instruções principais.",
        'Saída: {"action":"read_text_file","path":"AGENTS.md"}',
        "Entrada: Explique como arquivos funcionam em Python.",
        'Saída: {"action":"none"}',
        "Não invente caminhos e não produza mais de uma ação.",
    )
)


@dataclass(frozen=True, slots=True)
class ReadTextFileIntent:
    path: str


class FileIntentInterpreter(Protocol):
    def interpret(self, user_input: str) -> ReadTextFileIntent | None: ...


class ModelFileIntentInterpreter:
    def __init__(self, model_provider: ModelProvider) -> None:
        self._model_provider = model_provider

    def interpret(self, user_input: str) -> ReadTextFileIntent | None:
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
    )


def _parse_interpretation(response: str) -> ReadTextFileIntent | None:
    try:
        data = json.loads(response)
    except (json.JSONDecodeError, TypeError):
        return None

    if data == {"action": "none"}:
        return None
    if not isinstance(data, dict) or set(data) != {"action", "path"}:
        return None
    if data.get("action") != "read_text_file":
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
