from pathlib import Path

import pytest

from capabilities.desktop import (
    OpenLocationStatus,
    OpenWorkspaceLocationCapability,
    ResolveLocationStatus,
)


class RecordingLauncher:
    def __init__(self, error: OSError | None = None) -> None:
        self.error = error
        self.paths: list[Path] = []

    def open(self, path: Path) -> None:
        self.paths.append(path)
        if self.error is not None:
            raise self.error


def test_prepare_returns_confined_directory_snapshot(tmp_path: Path) -> None:
    workspace = (tmp_path / "workspace").resolve()
    docs = workspace / "docs"
    docs.mkdir(parents=True)

    result = OpenWorkspaceLocationCapability(workspace, RecordingLauncher()).prepare("docs")

    assert result.status is ResolveLocationStatus.SUCCESS
    assert result.target is not None
    assert result.target.relative_path == "docs"
    assert result.target.resolved_path == docs.resolve()


@pytest.mark.parametrize("path", ["../outside", "C:\\Windows", "/tmp", "file://docs"])
def test_prepare_rejects_paths_outside_workspace(tmp_path: Path, path: str) -> None:
    workspace = (tmp_path / "workspace").resolve()
    workspace.mkdir()

    result = OpenWorkspaceLocationCapability(workspace, RecordingLauncher()).prepare(path)

    assert result.status in {
        ResolveLocationStatus.INVALID_PATH,
        ResolveLocationStatus.OUTSIDE_WORKSPACE,
    }
    assert result.target is None


def test_prepare_rejects_missing_path_and_file(tmp_path: Path) -> None:
    workspace = (tmp_path / "workspace").resolve()
    workspace.mkdir()
    (workspace / "file.txt").write_text("content", encoding="utf-8")
    capability = OpenWorkspaceLocationCapability(workspace, RecordingLauncher())

    assert capability.prepare("missing").status is ResolveLocationStatus.NOT_FOUND
    assert capability.prepare("file.txt").status is ResolveLocationStatus.NOT_DIRECTORY


def test_execute_opens_prepared_target_after_revalidation(tmp_path: Path) -> None:
    workspace = (tmp_path / "workspace").resolve()
    docs = workspace / "docs"
    docs.mkdir(parents=True)
    launcher = RecordingLauncher()
    capability = OpenWorkspaceLocationCapability(workspace, launcher)
    prepared = capability.prepare("docs")
    assert prepared.target is not None

    result = capability.open(prepared.target)

    assert result.status is OpenLocationStatus.SUCCESS
    assert launcher.paths == [docs.resolve()]


def test_execute_rejects_target_replaced_after_confirmation(tmp_path: Path) -> None:
    workspace = (tmp_path / "workspace").resolve()
    docs = workspace / "docs"
    docs.mkdir(parents=True)
    launcher = RecordingLauncher()
    capability = OpenWorkspaceLocationCapability(workspace, launcher)
    prepared = capability.prepare("docs")
    assert prepared.target is not None
    docs.rename(workspace / "old-docs")
    docs.mkdir()

    result = capability.open(prepared.target)

    assert result.status is OpenLocationStatus.TARGET_CHANGED
    assert launcher.paths == []


def test_execute_reports_launcher_failure(tmp_path: Path) -> None:
    workspace = (tmp_path / "workspace").resolve()
    docs = workspace / "docs"
    docs.mkdir(parents=True)
    capability = OpenWorkspaceLocationCapability(
        workspace,
        RecordingLauncher(OSError("blocked")),
    )
    prepared = capability.prepare("docs")
    assert prepared.target is not None

    assert capability.open(prepared.target).status is OpenLocationStatus.OPEN_FAILED
