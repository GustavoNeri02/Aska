from capabilities.filesystem import suggest_similar_file_paths


def test_matcher_suggests_pluralized_filename_with_same_extension() -> None:
    result = suggest_similar_file_paths(
        "memory.json",
        ("data/memory/memories.json", "docs/memory.md"),
    )

    assert result == ("data/memory/memories.json",)


def test_matcher_ignores_candidates_with_different_extension() -> None:
    assert suggest_similar_file_paths("memory.json", ("docs/memory.md",)) == ()


def test_matcher_normalizes_case_and_accents() -> None:
    result = suggest_similar_file_paths("MEMÓRIA.json", ("data/memoria.json",))

    assert result == ("data/memoria.json",)


def test_matcher_rejects_dissimilar_names() -> None:
    assert suggest_similar_file_paths("memory.json", ("data/settings.json",)) == ()


def test_matcher_orders_best_matches_and_limits_results() -> None:
    result = suggest_similar_file_paths(
        "memory.json",
        (
            "data/memories.json",
            "archive/memory-old.json",
            "backup/memory-backup.json",
        ),
        max_results=2,
        cutoff=0.5,
    )

    assert result == ("data/memories.json", "archive/memory-old.json")
