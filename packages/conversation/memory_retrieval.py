import re
import unicodedata
from dataclasses import dataclass
from typing import Protocol

from packages.memory import Memory

_TOKEN = re.compile(r"[a-z0-9]+")
_STOP_WORDS = {
    "a",
    "ao",
    "aos",
    "as",
    "com",
    "da",
    "das",
    "de",
    "do",
    "dos",
    "e",
    "em",
    "eu",
    "me",
    "meu",
    "minha",
    "no",
    "nos",
    "o",
    "os",
    "para",
    "por",
    "que",
    "se",
    "sobre",
    "um",
    "uma",
    "voce",
}


class MemorySource(Protocol):
    def list(self) -> list[Memory]: ...


@dataclass(frozen=True, slots=True)
class MemorySelection:
    memories: tuple[Memory, ...]
    query_terms: tuple[str, ...]


class TextMemoryRetriever:
    def __init__(self, source: MemorySource, *, max_results: int = 5) -> None:
        if max_results <= 0 or max_results > 20:
            raise ValueError("max_results must be between 1 and 20")
        self._source = source
        self._max_results = max_results

    def retrieve(self, query: str) -> MemorySelection:
        query_terms = _meaningful_terms(query)
        if not query_terms:
            return MemorySelection((), ())
        query_set = set(query_terms)
        ranked: list[tuple[int, int, Memory]] = []
        for position, memory in enumerate(self._source.list()):
            overlap = query_set.intersection(_meaningful_terms(memory.content))
            if overlap:
                ranked.append((len(overlap), position, memory))
        ranked.sort(key=lambda item: (-item[0], item[1]))
        return MemorySelection(
            tuple(item[2] for item in ranked[: self._max_results]),
            query_terms,
        )


def is_memory_usage_question(message: str) -> bool:
    normalized = _normalize(message)
    return bool(
        re.search(r"\b(?:memoria|memorias)\b", normalized)
        and re.search(
            r"\b(?:usou|usadas|usada|utilizou|utilizada|utilizadas|considerou|"
            r"considerada|consideradas)\b",
            normalized,
        )
    )


def _meaningful_terms(value: str) -> tuple[str, ...]:
    return tuple(
        dict.fromkeys(
            token
            for token in _TOKEN.findall(_normalize(value))
            if len(token) >= 3 and token not in _STOP_WORDS
        )
    )


def _normalize(value: str) -> str:
    return "".join(
        character
        for character in unicodedata.normalize("NFKD", value.casefold())
        if not unicodedata.combining(character)
    )
