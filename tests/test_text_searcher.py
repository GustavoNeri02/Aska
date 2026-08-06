from pathlib import Path

import pytest

from capabilities.filesystem import (
    SearchTextCapability,
    SearchTextStatus,
    TextSearchMatch,
)


def test_capability_finds_literal_text_with_path_and_line(tmp_path: Path) -> None:
    workspace = (tmp_path / "workspace").resolve()
    document = workspace / "docs" / "roadmap.md"
    document.parent.mkdir(parents=True)
    document.write_text("Fase 4\nBusca Vetorial permanece planned.\n", encoding="utf-8")

    result = SearchTextCapability(workspace).search("busca vetorial")

    assert result.status is SearchTextStatus.SUCCESS
    assert result.matches == (
        TextSearchMatch("docs/roadmap.md", 2, "Busca Vetorial permanece planned."),
    )


def test_capability_filters_by_extension_without_reading_other_files(tmp_path: Path) -> None:
    workspace = (tmp_path / "workspace").resolve()
    workspace.mkdir()
    (workspace / "app.py").write_text("MemoryService", encoding="utf-8")
    (workspace / "notes.md").write_text("MemoryService", encoding="utf-8")

    result = SearchTextCapability(workspace).search("MemoryService", extension="py")

    assert result.matches == (TextSearchMatch("app.py", 1, "MemoryService"),)


def test_capability_returns_success_without_matches(tmp_path: Path) -> None:
    workspace = (tmp_path / "workspace").resolve()
    workspace.mkdir()
    (workspace / "README.md").write_text("Aska local", encoding="utf-8")

    result = SearchTextCapability(workspace).search("inexistente")

    assert result.status is SearchTextStatus.SUCCESS
    assert result.matches == ()


@pytest.mark.parametrize("query", ["", "   ", "duas\nlinhas", "nul\0byte"])
def test_capability_rejects_invalid_query(tmp_path: Path, query: str) -> None:
    workspace = (tmp_path / "workspace").resolve()
    workspace.mkdir()

    assert SearchTextCapability(workspace).search(query).status is SearchTextStatus.INVALID_QUERY


def test_capability_preserves_workspace_confinement(tmp_path: Path) -> None:
    workspace = (tmp_path / "workspace").resolve()
    workspace.mkdir()

    result = SearchTextCapability(workspace).search("segredo", directory="../outside")

    assert result.status is SearchTextStatus.OUTSIDE_WORKSPACE
    assert result.matches == ()


def test_capability_truncates_at_match_limit(tmp_path: Path) -> None:
    workspace = (tmp_path / "workspace").resolve()
    workspace.mkdir()
    (workspace / "one.txt").write_text("termo\ntermo\n", encoding="utf-8")

    result = SearchTextCapability(workspace, max_matches=1).search("termo")

    assert result.status is SearchTextStatus.LIMIT_REACHED
    assert result.matches == (TextSearchMatch("one.txt", 1, "termo"),)
