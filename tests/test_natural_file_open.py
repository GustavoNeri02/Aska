from pathlib import Path

from apps.cli.handlers import NaturalOpenFileHandler
from capabilities.desktop import OpenWorkspaceFileCapability
from capabilities.filesystem import ListFilesCapability
from packages.conversation import OpenWorkspaceFileProposal, detect_explicit_open_file


class Launcher:
    def __init__(self) -> None:
        self.paths: list[Path] = []

    def open(self, path: Path) -> None:
        self.paths.append(path)


def test_explicit_file_open_is_detected_without_confusing_explorer() -> None:
    assert detect_explicit_open_file("Abra o README.md") == OpenWorkspaceFileProposal("README.md")
    assert detect_explicit_open_file("Abra o Explorer") is None
    assert detect_explicit_open_file("Abra a pasta docs no Explorer") is None
    assert detect_explicit_open_file("Abra sua mente") is None
    assert detect_explicit_open_file('Abra "C:\\Users\\Gustavo\\Desktop\\minha imagem.png"') == (
        OpenWorkspaceFileProposal('"C:\\Users\\Gustavo\\Desktop\\minha imagem.png"')
    )


def test_handler_discovers_known_file_and_requires_confirmation(tmp_path: Path) -> None:
    docs = tmp_path / "docs" / "project"
    docs.mkdir(parents=True)
    roadmap = docs / "roadmap.md"
    roadmap.write_text("roadmap", encoding="utf-8")
    launcher = Launcher()
    handler = NaturalOpenFileHandler(
        OpenWorkspaceFileCapability(tmp_path.resolve(), launcher),
        ListFilesCapability(tmp_path.resolve()),
    )

    proposal = handler.handle("Abra o roadmap")
    completed = handler.handle("sim")

    assert proposal is not None
    assert proposal.kind == "confirmation_required"
    assert proposal.facts["path"] == "docs/project/roadmap.md"
    assert completed is not None
    assert completed.kind == "open_file_completed"
    assert launcher.paths == [roadmap.resolve()]


def test_handler_returns_suggestions_without_opening(tmp_path: Path) -> None:
    (tmp_path / "memories.json").write_text("[]", encoding="utf-8")
    handler = NaturalOpenFileHandler(
        OpenWorkspaceFileCapability(tmp_path.resolve(), Launcher()),
        ListFilesCapability(tmp_path.resolve()),
    )

    result = handler.handle_proposal(OpenWorkspaceFileProposal("memory.json"), "abra")

    assert result.kind == "open_file_not_found"
    assert result.facts["suggestions"] == ("memories.json",)
