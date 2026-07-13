import json
import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from packages.conversation.model import ModelMessage, ModelRole
from packages.conversation.provider import ModelProvider
from packages.memory import Memory

_NAME_CHANGE_PATTERNS = (
    re.compile(r"meu nome agora é\s+(.+)", re.IGNORECASE),
    re.compile(r"mude meu nome para\s+(.+)", re.IGNORECASE),
)
_NAME_COMPONENT = r"[^\W\d_]+(?:[-'’][^\W\d_]+)?"
_NAME = re.compile(rf"{_NAME_COMPONENT}(?:\s+{_NAME_COMPONENT})*", re.UNICODE)
_AMBIGUOUS_WORDS = frozenset({"e", "mas", "porque", "porém", "pois", "também"})
_NAME_MEMORY_PATTERNS = (
    re.compile(r"meu nome é\s+.+", re.IGNORECASE),
    re.compile(r"eu me chamo\s+.+", re.IGNORECASE),
)
_NAME_CHANGE_GATE_TERMS = (
    re.compile(r"\bnome\b.*\b(atualiz\w*|mud\w*|alter\w*|troqu\w*)", re.IGNORECASE),
    re.compile(r"\b(atualiz\w*|mud\w*|alter\w*|troqu\w*)\b.*\bnome\b", re.IGNORECASE),
    re.compile(r"\b(passe|quero|agora|diante)\b.*\bcham\w*\b", re.IGNORECASE),
    re.compile(r"\bcham\w*\b.*\b(passe|quero|agora|diante)\b", re.IGNORECASE),
)
_INTERPRETER_INSTRUCTION = """Classifique somente se a mensagem pede para alterar o nome de Gustavo.
Responda com exatamente um objeto JSON, sem Markdown ou texto adicional.
Formatos permitidos:
{"action":"update_name","new_name":"Novo Nome"}
{"action":"none"}
Não execute ações e não invente informações."""


@dataclass(frozen=True, slots=True)
class PendingMemoryEdit:
    memory_id: str
    expected_content: str
    new_content: str


@dataclass(frozen=True, slots=True)
class NameUpdateIntent:
    new_name: str


class MemoryIntentInterpreter(Protocol):
    def interpret(self, user_input: str) -> NameUpdateIntent | None: ...


class ModelMemoryIntentInterpreter:
    def __init__(self, model_provider: ModelProvider) -> None:
        self._model_provider = model_provider

    def interpret(self, user_input: str) -> NameUpdateIntent | None:
        response = self._model_provider.generate(
            [
                ModelMessage(ModelRole.SYSTEM, _INTERPRETER_INSTRUCTION),
                ModelMessage(ModelRole.USER, user_input),
            ]
        )
        return _parse_interpretation(response)


def detect_name_change(user_input: str) -> str | None:
    message = user_input.strip()
    for pattern in _NAME_CHANGE_PATTERNS:
        match = pattern.fullmatch(message)
        if match is None:
            continue

        new_name = _normalize_name(match.group(1))
        return canonical_name_memory(new_name) if new_name is not None else None
    return None


def should_interpret_name_change(user_input: str) -> bool:
    message = user_input.strip()
    return any(pattern.search(message) for pattern in _NAME_CHANGE_GATE_TERMS)


def canonical_name_memory(new_name: str) -> str:
    return f"Meu nome é {new_name}."


def find_name_memory_candidates(memories: Sequence[Memory]) -> list[Memory]:
    return [
        memory
        for memory in memories
        if any(pattern.fullmatch(memory.content.strip()) for pattern in _NAME_MEMORY_PATTERNS)
    ]


def _parse_interpretation(response: str) -> NameUpdateIntent | None:
    try:
        data = json.loads(response)
    except (json.JSONDecodeError, TypeError):
        return None

    if not isinstance(data, dict):
        return None
    if data == {"action": "none"}:
        return None
    if set(data) != {"action", "new_name"} or data.get("action") != "update_name":
        return None

    new_name = data.get("new_name")
    if not isinstance(new_name, str):
        return None
    normalized_name = _normalize_name(new_name)
    if normalized_name is None:
        return None
    return NameUpdateIntent(normalized_name)


def _normalize_name(value: str) -> str | None:
    new_name = value.strip().removesuffix(".").strip()
    if not new_name or _NAME.fullmatch(new_name) is None:
        return None
    if _AMBIGUOUS_WORDS.intersection(new_name.casefold().split()):
        return None
    return new_name
