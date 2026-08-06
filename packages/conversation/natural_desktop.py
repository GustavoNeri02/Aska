import json
import re
from dataclasses import dataclass
from typing import Protocol

from packages.conversation.model import ModelMessage, ModelRole
from packages.conversation.provider import ModelProvider

_EXPLICIT_OPEN_LOCATION = re.compile(
    r"^\s*abra\s+(?:a\s+|o\s+)?(?:pasta|diret[oó]rio)\s+"
    r"(?P<path>.+?)\s+(?:no|com\s+o)\s+(?:explorador|explorer)\s*[.!?]?\s*$",
    re.IGNORECASE,
)
_EXPLICIT_OPEN_EXPLORER = re.compile(
    r"^\s*(?:abra|abre)\s+(?:o\s+)?(?:programa\s+)?"
    r"(?:explorador(?:\s+de\s+arquivos)?|explorer)\s*[.!?]?\s*$",
    re.IGNORECASE,
)
_EXPLICIT_OPEN_EXPLORER_AT = re.compile(
    r"^\s*abra\s+(?:o\s+)?(?:explorador|explorer)\s+"
    r"(?:em|na\s+pasta|no\s+diret[oó]rio)\s+(?P<path>.+?)\s*[.!?]?\s*$",
    re.IGNORECASE,
)
_OPEN_LOCATION_REQUEST = re.compile(
    r"\b(?:abra|abre|abrir|inicia|inicie|iniciar|mostre|mostrar)\b.*"
    r"\b(?:explorador|explorer)\b",
    re.IGNORECASE,
)
_INTERPRETER_INSTRUCTION = "\n".join(
    (
        "Apenas classifique o pedido. Não responda ao usuário, não acesse o "
        "filesystem e não abra aplicativos.",
        "Reconheça somente pedidos claros para abrir uma pasta do workspace no "
        "Explorador de Arquivos.",
        "Extraia somente um caminho relativo ao workspace. Se o usuário pedir apenas "
        "para abrir o Explorador, use o caminho '.'.",
        "Responda com exatamente um objeto JSON, sem Markdown ou texto adicional.",
        "Formatos permitidos:",
        '{"action":"open_workspace_location","path":"docs"}',
        '{"action":"none"}',
        "Não conceda permissões, não invente caminhos e não proponha outra ação.",
    )
)


@dataclass(frozen=True, slots=True)
class OpenWorkspaceLocationIntent:
    path: str


class OpenLocationIntentInterpreter(Protocol):
    def interpret(self, user_input: str) -> OpenWorkspaceLocationIntent | None: ...


class ModelOpenLocationIntentInterpreter:
    def __init__(self, model_provider: ModelProvider) -> None:
        self._model_provider = model_provider

    def interpret(self, user_input: str) -> OpenWorkspaceLocationIntent | None:
        response = self._model_provider.generate(
            [
                ModelMessage(ModelRole.SYSTEM, _INTERPRETER_INSTRUCTION),
                ModelMessage(ModelRole.USER, user_input),
            ]
        )
        return _parse_interpretation(response)


def detect_explicit_open_location(
    user_input: str,
) -> OpenWorkspaceLocationIntent | None:
    message = user_input.strip()
    if not _is_single_line(message):
        return None
    explorer_at_match = _EXPLICIT_OPEN_EXPLORER_AT.fullmatch(message)
    if explorer_at_match is not None:
        path = _validated_path(explorer_at_match.group("path"))
        return OpenWorkspaceLocationIntent(path) if path is not None else None
    if _EXPLICIT_OPEN_EXPLORER.fullmatch(message) is not None:
        return OpenWorkspaceLocationIntent(".")
    match = _EXPLICIT_OPEN_LOCATION.fullmatch(message)
    if match is None:
        return None
    path = _validated_path(match.group("path"))
    return OpenWorkspaceLocationIntent(path) if path is not None else None


def should_interpret_open_location(user_input: str) -> bool:
    message = user_input.strip()
    return _is_single_line(message) and _OPEN_LOCATION_REQUEST.search(message) is not None


def _parse_interpretation(response: str) -> OpenWorkspaceLocationIntent | None:
    try:
        data = json.loads(response)
    except (json.JSONDecodeError, TypeError):
        return None
    if data == {"action": "none"}:
        return None
    if not isinstance(data, dict) or set(data) != {"action", "path"}:
        return None
    if data.get("action") != "open_workspace_location":
        return None
    path = _validated_path(data.get("path"))
    return OpenWorkspaceLocationIntent(path) if path is not None else None


def _validated_path(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    if not _is_single_line(normalized) or "\0" in normalized:
        return None
    return normalized


def _is_single_line(value: str) -> bool:
    return bool(value and "\n" not in value and "\r" not in value)
