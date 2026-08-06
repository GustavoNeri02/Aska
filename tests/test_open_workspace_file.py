from pathlib import Path

import pytest

from capabilities.desktop import (
    OpenFileStatus,
    OpenWorkspaceFileCapability,
    ResolveFileStatus,
)


class Launcher:
    def __init__(self, error: OSError | None = None) -> None:
        self.error = error
        self.paths: list[Path] = []

    def open(self, path: Path) -> None:
        self.paths.append(path)
        if self.error is not None:
            raise self.error


def test_prepare_and_open_confined_file(tmp_path: Path) -> None:
    workspace = tmp_path.resolve()
    readme = workspace / "README.md"
    readme.write_text("Aska", encoding="utf-8")
    launcher = Launcher()
    capability = OpenWorkspaceFileCapability(workspace, launcher)

    prepared = capability.prepare("README.md")
    assert prepared.status is ResolveFileStatus.SUCCESS
    assert prepared.target is not None
    assert capability.open(prepared.target).status is OpenFileStatus.SUCCESS
    assert launcher.paths == [readme]


@pytest.mark.parametrize(
    "path",
    [
        "../outside.pdf",
        "file://a.pdf",
    ],
)
def test_prepare_rejects_external_paths(tmp_path: Path, path: str) -> None:
    result = OpenWorkspaceFileCapability(tmp_path.resolve(), Launcher()).prepare(path)

    assert result.status in {ResolveFileStatus.INVALID_PATH, ResolveFileStatus.OUTSIDE_WORKSPACE}


def test_prepare_and_open_explicit_absolute_file_outside_workspace(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    external = tmp_path / "outside image.png"
    external.write_bytes(b"image")
    launcher = Launcher()
    capability = OpenWorkspaceFileCapability(workspace.resolve(), launcher)

    prepared = capability.prepare(f'"{external.resolve()}"')
    assert prepared.status is ResolveFileStatus.SUCCESS
    assert prepared.target is not None
    assert prepared.target.relative_path == str(external.resolve())
    assert capability.open(prepared.target).status is OpenFileStatus.SUCCESS
    assert launcher.paths == [external.resolve()]


def test_absolute_executable_remains_blocked(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    external = tmp_path / "outside.exe"
    external.write_bytes(b"MZ executable")

    result = OpenWorkspaceFileCapability(workspace.resolve(), Launcher()).prepare(str(external))

    assert result.status is ResolveFileStatus.BLOCKED_TYPE


@pytest.mark.parametrize("filename", ["tool.exe", "script.py", "run.ps1", "link.lnk"])
def test_prepare_blocks_executable_file_types(tmp_path: Path, filename: str) -> None:
    (tmp_path / filename).write_text("content", encoding="utf-8")

    result = OpenWorkspaceFileCapability(tmp_path.resolve(), Launcher()).prepare(filename)

    assert result.status is ResolveFileStatus.BLOCKED_TYPE


def test_prepare_blocks_disguised_windows_executable(tmp_path: Path) -> None:
    (tmp_path / "report.pdf").write_bytes(b"MZ executable payload")

    result = OpenWorkspaceFileCapability(tmp_path.resolve(), Launcher()).prepare("report.pdf")

    assert result.status is ResolveFileStatus.BLOCKED_TYPE


def test_url_shortcut_can_be_opened_after_confirmation(tmp_path: Path) -> None:
    shortcut = tmp_path / "game.url"
    shortcut.write_text("[InternetShortcut]\nURL=steam://run/123", encoding="utf-8")
    launcher = Launcher()
    capability = OpenWorkspaceFileCapability(tmp_path.resolve(), launcher)

    prepared = capability.prepare("game.url")
    assert prepared.status is ResolveFileStatus.SUCCESS
    assert prepared.target is not None
    assert capability.open(prepared.target).status is OpenFileStatus.SUCCESS
    assert launcher.paths == [shortcut.resolve()]


def test_open_rejects_file_changed_after_confirmation(tmp_path: Path) -> None:
    path = tmp_path / "README.md"
    path.write_text("before", encoding="utf-8")
    launcher = Launcher()
    capability = OpenWorkspaceFileCapability(tmp_path.resolve(), launcher)
    prepared = capability.prepare("README.md")
    assert prepared.target is not None
    path.write_text("after confirmation", encoding="utf-8")

    assert capability.open(prepared.target).status is OpenFileStatus.TARGET_CHANGED
    assert launcher.paths == []


def test_open_reports_launcher_failure(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("Aska", encoding="utf-8")
    capability = OpenWorkspaceFileCapability(tmp_path.resolve(), Launcher(OSError("blocked")))
    prepared = capability.prepare("README.md")
    assert prepared.target is not None

    assert capability.open(prepared.target).status is OpenFileStatus.OPEN_FAILED
