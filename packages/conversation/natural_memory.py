import re
from collections.abc import Sequence
from dataclasses import dataclass

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


@dataclass(frozen=True, slots=True)
class PendingMemoryEdit:
    memory_id: str
    expected_content: str
    new_content: str


def detect_name_change(user_input: str) -> str | None:
    message = user_input.strip()
    for pattern in _NAME_CHANGE_PATTERNS:
        match = pattern.fullmatch(message)
        if match is None:
            continue

        new_name = match.group(1).strip().removesuffix(".").strip()
        if not new_name or _NAME.fullmatch(new_name) is None:
            return None
        if _AMBIGUOUS_WORDS.intersection(new_name.casefold().split()):
            return None
        return f"Meu nome é {new_name}."
    return None


def find_name_memory_candidates(memories: Sequence[Memory]) -> list[Memory]:
    return [
        memory
        for memory in memories
        if any(pattern.fullmatch(memory.content.strip()) for pattern in _NAME_MEMORY_PATTERNS)
    ]
