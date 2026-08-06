from pathlib import Path

from apps.cli.handlers import NaturalOpenLocationHandler
from capabilities.desktop import OpenWorkspaceLocationCapability
from packages.conversation import OpenWorkspaceLocationProposal


class RecordingLauncher:
    def __init__(self) -> None:
        self.paths: list[Path] = []

    def open(self, path: Path) -> None:
        self.paths.append(path)


def _handler(workspace: Path) -> tuple[NaturalOpenLocationHandler, RecordingLauncher]:
    launcher = RecordingLauncher()
    return NaturalOpenLocationHandler(
        OpenWorkspaceLocationCapability(workspace.resolve(), launcher)
    ), launcher


def test_open_location_returns_structured_confirmation_before_launch(tmp_path: Path) -> None:
    (tmp_path / "docs").mkdir()
    handler, launcher = _handler(tmp_path)

    proposal = handler.handle_proposal(OpenWorkspaceLocationProposal("docs"), "abra docs")

    assert proposal.kind == "confirmation_required"
    assert proposal.facts["path"] == str((tmp_path / "docs").resolve())
    assert launcher.paths == []


def test_open_location_executes_only_after_confirmation(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    handler, launcher = _handler(tmp_path)
    handler.handle_proposal(OpenWorkspaceLocationProposal("docs"), "abra docs")

    result = handler.handle("sim")

    assert result is not None
    assert result.kind == "open_location_completed"
    assert result.facts["status"] == "success"
    assert result.original_request == "abra docs"
    assert launcher.paths == [docs.resolve()]


def test_open_location_cancellation_has_no_effect(tmp_path: Path) -> None:
    (tmp_path / "docs").mkdir()
    handler, launcher = _handler(tmp_path)
    handler.handle_proposal(OpenWorkspaceLocationProposal("docs"), "abra docs")

    result = handler.handle("não")

    assert result is not None
    assert result.kind == "open_location_cancelled"
    assert launcher.paths == []


def test_unknown_confirmation_keeps_proposal_pending(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    handler, launcher = _handler(tmp_path)
    handler.handle_proposal(OpenWorkspaceLocationProposal("docs"), "abra docs")

    unknown = handler.handle("talvez")
    completed = handler.handle("sim")

    assert unknown is not None
    assert unknown.kind == "confirmation_unknown"
    assert completed is not None
    assert completed.kind == "open_location_completed"
    assert launcher.paths == [docs.resolve()]


def test_changed_target_is_not_opened_after_confirmation(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    handler, launcher = _handler(tmp_path)
    handler.handle_proposal(OpenWorkspaceLocationProposal("docs"), "abra docs")
    docs.rename(tmp_path / "old-docs")
    docs.mkdir()

    result = handler.handle("sim")

    assert result is not None
    assert result.facts["status"] == "target_changed"
    assert launcher.paths == []


def test_open_location_rejects_outside_workspace(tmp_path: Path) -> None:
    handler, launcher = _handler(tmp_path)

    result = handler.handle_proposal(OpenWorkspaceLocationProposal("../fora"), "abra")

    assert result.kind == "open_location_refused"
    assert result.facts["status"] == "outside_workspace"
    assert launcher.paths == []


def test_unrelated_message_is_not_consumed(tmp_path: Path) -> None:
    handler, _ = _handler(tmp_path)

    assert handler.handle("sabe o explorer?") is None
