import os
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
class MemoryMatch:
    memory: Memory
    score: int
    matched_terms: tuple[str, ...]
    match_kinds: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class MemorySelection:
    matches: tuple[MemoryMatch, ...]
    query_terms: tuple[str, ...]

    @property
    def memories(self) -> tuple[Memory, ...]:
        return tuple(match.memory for match in self.matches)


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
        ranked: list[tuple[int, int, MemoryMatch]] = []
        for position, memory in enumerate(self._source.list()):
            memory_terms = _meaningful_terms(memory.content)
            term_matches = [
                (query_term, _best_match_kind(query_term, memory_terms))
                for query_term in query_terms
            ]
            matched = [(term, kind) for term, kind in term_matches if kind is not None]
            if matched:
                score = sum(_MATCH_SCORES[kind] for _, kind in matched)
                match = MemoryMatch(
                    memory,
                    score,
                    tuple(term for term, _ in matched),
                    tuple(kind for _, kind in matched),
                )
                ranked.append((score, position, match))
        ranked.sort(key=lambda item: (-item[0], item[1]))
        return MemorySelection(
            tuple(item[2] for item in ranked[: self._max_results]),
            query_terms,
        )


def is_memory_usage_question(message: str) -> bool:
    normalized = _normalize(message)
    return bool(
        re.search(r"\b(?:memoria|memorias)\b", normalized)
        and (
            re.search(
                r"\b(?:usou|usadas|usada|utilizou|utilizada|utilizadas|considerou|"
                r"considerada|consideradas)\b",
                normalized,
            )
            or re.search(r"\b(?:porque|por que|motivo|razao)\b", normalized)
        )
    )


_MATCH_SCORES = {"exact": 3, "plural": 2, "related": 1}


def _best_match_kind(query_term: str, memory_terms: tuple[str, ...]) -> str | None:
    best_kind: str | None = None
    for memory_term in memory_terms:
        kind = _match_kind(query_term, memory_term)
        if kind is not None and (
            best_kind is None or _MATCH_SCORES[kind] > _MATCH_SCORES[best_kind]
        ):
            best_kind = kind
    return best_kind


def _match_kind(left: str, right: str) -> str | None:
    if left == right:
        return "exact"
    if _singular(left) == _singular(right):
        return "plural"
    common_prefix = len(os.path.commonprefix((left, right)))
    if common_prefix >= 6 and abs(len(left) - len(right)) <= 3:
        return "related"
    return None


def _singular(term: str) -> str:
    if len(term) > 4 and term.endswith("ies"):
        return f"{term[:-3]}y"
    if len(term) > 4 and term.endswith("s"):
        return term[:-1]
    return term


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
