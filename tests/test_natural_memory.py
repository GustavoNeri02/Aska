from datetime import UTC, datetime

import pytest

from packages.conversation import detect_name_change, find_name_memory_candidates
from packages.memory import Memory, MemorySource


@pytest.mark.parametrize(
    "message",
    [
        "Meu nome agora é Gustavo Neri",
        "Mude meu nome para Gustavo Neri",
        "MEU NOME AGORA É Gustavo Neri",
        "mUdE mEu NoMe PaRa Gustavo Neri",
    ],
)
def test_detect_name_change_accepts_supported_patterns_and_case_variations(
    message: str,
) -> None:
    assert detect_name_change(message) == "Meu nome é Gustavo Neri."


@pytest.mark.parametrize(
    "message",
    [
        "Meu nome agora é",
        "Mude meu nome para   ",
        "Meu nome agora é Gustavo Neri, e moro em São Paulo",
        "Meu nome agora é Gustavo Neri porque casei",
        "Qual é o meu nome?",
    ],
)
def test_detect_name_change_rejects_empty_ambiguous_or_unrelated_messages(
    message: str,
) -> None:
    assert detect_name_change(message) is None


def test_find_name_memory_candidates_uses_restricted_text_patterns() -> None:
    now = datetime(2026, 7, 13, tzinfo=UTC)
    memories = [
        Memory(
            id="11111111-1111-1111-1111-111111111111",
            content="Meu nome é Gustavo.",
            source=MemorySource.EXPLICIT_CLI,
            created_at=now,
            updated_at=now,
        ),
        Memory(
            id="22222222-2222-2222-2222-222222222222",
            content="EU ME CHAMO Gustavo Souza.",
            source=MemorySource.EXPLICIT_CLI,
            created_at=now,
            updated_at=now,
        ),
        Memory(
            id="33333333-3333-3333-3333-333333333333",
            content="Gustavo gosta de Python.",
            source=MemorySource.EXPLICIT_CLI,
            created_at=now,
            updated_at=now,
        ),
    ]

    assert find_name_memory_candidates(memories) == memories[:2]
