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
_MEMORY_ADD_PATTERNS = (
    re.compile(r"lembre\s+que\s*(.*)", re.IGNORECASE),
    re.compile(r"memorize\s+que\s*(.*)", re.IGNORECASE),
    re.compile(r"guarde\s+que\s*(.*)", re.IGNORECASE),
    re.compile(r"não\s+esqueça\s+que\s*(.*)", re.IGNORECASE),
)
_MEMORY_DELETE_PATTERNS = (
    re.compile(r"esqueça\s+que\s*(.*)", re.IGNORECASE),
    re.compile(r"remova\s+a\s+memória\s*:\s*(.*)", re.IGNORECASE),
    re.compile(r"apague\s+a\s+memória\s*:\s*(.*)", re.IGNORECASE),
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
_MEMORY_ADD_GATE_TERMS = (
    re.compile(
        r"\b(?:lembre|lembrar|memorize|memorizar|guarde|guardar)\b.*\bque\b\s+\S",
        re.IGNORECASE,
    ),
    re.compile(r"\bnão\s+esqueça\b.*\bque\b\s+\S", re.IGNORECASE),
)
_MEMORY_DELETE_GATE_TERMS = (
    re.compile(r"\besqueça\b\s+que\b\s+\S", re.IGNORECASE),
    re.compile(
        r"\b(?:remov\w*|apag\w*|exclu\w*)\b.*\bmemória\b"
        r"(?:\s*:|\s+(?:sobre|de))?\s+\S",
        re.IGNORECASE,
    ),
    re.compile(r"\bnão\s+precisa\s+mais\s+lembrar\b.*\bque\b\s+\S", re.IGNORECASE),
    re.compile(r"\bapag\w*\b.*\bguard\w*\b.*\S", re.IGNORECASE),
)
_MEMORY_EDIT_GATE_TERMS = (
    re.compile(
        r"\b(?:atualize|corrija|altere|troque|mude|edite)\b.*"
        r"\b(?:memória|informação|preferência)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:memória|informação|preferência)\b.*\bmudou\b\s*:",
        re.IGNORECASE,
    ),
)
_INTERPRETER_INSTRUCTION = "\n".join(
    (
        "Apenas classifique a mensagem. Não responda ao pedido.",
        "Classifique somente se a mensagem pede explicitamente para:",
        "- alterar o nome de Gustavo; ou",
        "- guardar uma única informação como memória; ou",
        "- excluir uma memória descrita pelo usuário; ou",
        "- editar uma memória descrita pelo usuário, incluindo uma preferência conhecida.",
        "Responda com exatamente um objeto JSON, sem Markdown ou texto adicional.",
        "Formatos permitidos:",
        '{"action":"update_name","new_name":"Novo Nome"}',
        '{"action":"add_memory","content":"Informação a guardar."}',
        '{"action":"delete_memory","query":"Informação a localizar."}',
        ('{"action":"edit_memory","query":"Informação atual.","new_content":"Nova informação."}'),
        '{"action":"none"}',
        "Regras para edit_memory:",
        (
            "- Uma mudança explícita de preferência anteriormente conhecida é edit_memory, "
            'mesmo sem a palavra "memória".'
        ),
        "- query deve reutilizar palavras distintivas do conteúdo antigo, sem paráfrase excessiva.",
        "- new_content deve ser uma memória completa e independente.",
        "- Preserve negações e o significado informado.",
        (
            "Se não houver uma ação explícita de memória ou mudança de preferência conhecida, "
            'retorne {"action":"none"}.'
        ),
        "Exemplos:",
        "Entrada: Troque minha preferência por respostas longas para respostas diretas.",
        (
            'Saída: {"action":"edit_memory","query":"respostas longas",'
            '"new_content":"Prefiro respostas diretas."}'
        ),
        "Entrada: Atualize a memória sobre Flutter: agora eu trabalho com Python.",
        (
            'Saída: {"action":"edit_memory","query":"Flutter",'
            '"new_content":"Eu trabalho com Python."}'
        ),
        "Entrada: Atualize meu aplicativo.",
        'Saída: {"action":"none"}',
        "Não execute ações, não informe sucesso e não invente informações.",
    )
)


@dataclass(frozen=True, slots=True)
class PendingMemoryEdit:
    memory_id: str
    expected_content: str
    new_content: str


@dataclass(frozen=True, slots=True)
class PendingMemoryAdd:
    content: str


@dataclass(frozen=True, slots=True)
class PendingMemoryDelete:
    memory_id: str
    expected_content: str


@dataclass(frozen=True, slots=True)
class NameUpdateIntent:
    new_name: str


@dataclass(frozen=True, slots=True)
class AddMemoryIntent:
    content: str


@dataclass(frozen=True, slots=True)
class DeleteMemoryIntent:
    query: str


@dataclass(frozen=True, slots=True)
class EditMemoryIntent:
    query: str
    new_content: str


type MemoryIntent = NameUpdateIntent | AddMemoryIntent | DeleteMemoryIntent | EditMemoryIntent


class MemoryIntentInterpreter(Protocol):
    def interpret(self, user_input: str) -> MemoryIntent | None: ...


class ModelMemoryIntentInterpreter:
    def __init__(self, model_provider: ModelProvider) -> None:
        self._model_provider = model_provider

    def interpret(self, user_input: str) -> MemoryIntent | None:
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


def detect_memory_add(user_input: str) -> AddMemoryIntent | None:
    message = user_input.strip()
    if "\n" in message or "\r" in message:
        return None
    for pattern in _MEMORY_ADD_PATTERNS:
        match = pattern.fullmatch(message)
        if match is None:
            continue
        content = match.group(1).strip()
        return AddMemoryIntent(content) if content else None
    return None


def detect_memory_delete(user_input: str) -> DeleteMemoryIntent | None:
    message = user_input.strip()
    if "\n" in message or "\r" in message:
        return None
    for pattern in _MEMORY_DELETE_PATTERNS:
        match = pattern.fullmatch(message)
        if match is None:
            continue
        query = match.group(1).strip()
        return DeleteMemoryIntent(query) if query else None
    return None


def should_interpret_name_change(user_input: str) -> bool:
    message = user_input.strip()
    return any(pattern.search(message) for pattern in _NAME_CHANGE_GATE_TERMS)


def should_interpret_memory_add(user_input: str) -> bool:
    message = user_input.strip()
    if "\n" in message or "\r" in message:
        return False
    return any(pattern.search(message) for pattern in _MEMORY_ADD_GATE_TERMS)


def should_interpret_memory_delete(user_input: str) -> bool:
    message = user_input.strip()
    if "\n" in message or "\r" in message:
        return False
    patterns = _MEMORY_DELETE_GATE_TERMS
    if re.search(r"\bnão\s+esqueça\b", message, re.IGNORECASE):
        patterns = patterns[1:]
    return any(pattern.search(message) for pattern in patterns)


def should_interpret_memory_edit(user_input: str) -> bool:
    message = user_input.strip()
    if "\n" in message or "\r" in message:
        return False
    return any(pattern.search(message) for pattern in _MEMORY_EDIT_GATE_TERMS)


def should_interpret_memory_intent(user_input: str) -> bool:
    return (
        should_interpret_name_change(user_input)
        or should_interpret_memory_add(user_input)
        or should_interpret_memory_delete(user_input)
        or should_interpret_memory_edit(user_input)
    )


def canonical_name_memory(new_name: str) -> str:
    return f"Meu nome é {new_name}."


def find_name_memory_candidates(memories: Sequence[Memory]) -> list[Memory]:
    return [
        memory
        for memory in memories
        if any(pattern.fullmatch(memory.content.strip()) for pattern in _NAME_MEMORY_PATTERNS)
    ]


def _parse_interpretation(response: str) -> MemoryIntent | None:
    try:
        data = json.loads(response)
    except (json.JSONDecodeError, TypeError):
        return None

    if not isinstance(data, dict):
        return None
    if data == {"action": "none"}:
        return None

    action = data.get("action")
    if action == "add_memory":
        if set(data) != {"action", "content"}:
            return None
        content = data.get("content")
        if not isinstance(content, str):
            return None
        normalized_content = content.strip()
        if not normalized_content or "\n" in normalized_content or "\r" in normalized_content:
            return None
        return AddMemoryIntent(normalized_content)

    if action == "delete_memory":
        if set(data) != {"action", "query"}:
            return None
        query = data.get("query")
        if not isinstance(query, str):
            return None
        normalized_query = query.strip()
        if not normalized_query or "\n" in normalized_query or "\r" in normalized_query:
            return None
        return DeleteMemoryIntent(normalized_query)

    if action == "edit_memory":
        if set(data) != {"action", "query", "new_content"}:
            return None
        query = data.get("query")
        new_content = data.get("new_content")
        if not isinstance(query, str) or not isinstance(new_content, str):
            return None
        normalized_query = query.strip()
        normalized_content = new_content.strip()
        if (
            not normalized_query
            or not normalized_content
            or "\n" in normalized_query
            or "\r" in normalized_query
            or "\n" in normalized_content
            or "\r" in normalized_content
            or normalized_query.casefold() == normalized_content.casefold()
        ):
            return None
        return EditMemoryIntent(normalized_query, normalized_content)

    if action != "update_name" or set(data) != {"action", "new_name"}:
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
