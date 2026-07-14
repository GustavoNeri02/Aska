from pathlib import Path

import pytest

from capabilities.filesystem import (
    ListFilesCapability,
    ListFilesStatus,
)


def test_capability_lists_root_and_returns_relative_paths(tmp_path: Path) -> None:
    workspace = (tmp_path / "workspace").resolve()
    workspace.mkdir()
    (workspace / "README.md").write_text("readme", encoding="utf-8")
    (workspace / "src").mkdir()
    (workspace / "src" / "app.py").write_text("print()", encoding="utf-8")

    result = ListFilesCapability(workspace).list()

    assert result.status is ListFilesStatus.SUCCESS
    assert result.paths == ("README.md", "src/app.py")


def test_capability_lists_only_requested_subdirectory(tmp_path: Path) -> None:
    workspace = (tmp_path / "workspace").resolve()
    (workspace / "docs").mkdir(parents=True)
    (workspace / "docs" / "README.md").write_text("docs", encoding="utf-8")
    (workspace / "root.txt").write_text("root", encoding="utf-8")

    result = ListFilesCapability(workspace).list("docs")

    assert result.status is ListFilesStatus.SUCCESS
    assert result.paths == ("docs/README.md",)


def test_capability_filters_by_name_and_extension(tmp_path: Path) -> None:
    workspace = (tmp_path / "workspace").resolve()
    (workspace / "docs").mkdir(parents=True)
    (workspace / "docs" / "roadmap.md").write_text("roadmap", encoding="utf-8")
    (workspace / "docs" / "roadmap.py").write_text("roadmap", encoding="utf-8")
    (workspace / "docs" / "overview.md").write_text("overview", encoding="utf-8")

    result = ListFilesCapability(workspace).list(
        name_contains="ROADMAP",
        extension="md",
    )

    assert result.paths == ("docs/roadmap.md",)


@pytest.mark.parametrize(
    "ignored_directory",
    [
        ".git",
        ".venv",
        "venv",
        "__pycache__",
        "pycache",
        ".pytest_cache",
        ".ruff_cache",
        "node_modules",
    ],
)
def test_capability_ignores_configured_directories(
    ignored_directory: str,
    tmp_path: Path,
) -> None:
    workspace = (tmp_path / "workspace").resolve()
    hidden = workspace / ignored_directory
    hidden.mkdir(parents=True)
    (hidden / "ignored.txt").write_text("ignored", encoding="utf-8")
    (workspace / "visible.txt").write_text("visible", encoding="utf-8")

    result = ListFilesCapability(workspace).list()

    assert result.paths == ("visible.txt",)


def test_capability_returns_max_results_and_limit_status(
    tmp_path: Path,
) -> None:
    workspace = (tmp_path / "workspace").resolve()
    workspace.mkdir()
    for index in range(4):
        (workspace / f"{index}.txt").write_text(str(index), encoding="utf-8")

    result = ListFilesCapability(workspace, max_results=2).list()

    assert result.status is ListFilesStatus.LIMIT_REACHED
    assert result.paths == ("0.txt", "1.txt")


def test_capability_limits_depth(tmp_path: Path) -> None:
    workspace = (tmp_path / "workspace").resolve()
    nested = workspace / "one" / "two"
    nested.mkdir(parents=True)
    (workspace / "root.txt").write_text("root", encoding="utf-8")
    (workspace / "one" / "one.txt").write_text("one", encoding="utf-8")
    (nested / "two.txt").write_text("two", encoding="utf-8")

    result = ListFilesCapability(workspace, max_depth=1).list()

    assert result.paths == ("root.txt", "one/one.txt")


@pytest.mark.parametrize("directory", ["../outside", "/outside", r"C:\outside"])
def test_capability_rejects_traversal_and_absolute_paths(
    directory: str,
    tmp_path: Path,
) -> None:
    workspace = (tmp_path / "workspace").resolve()
    workspace.mkdir()

    result = ListFilesCapability(workspace).list(directory)

    assert result.status is ListFilesStatus.OUTSIDE_WORKSPACE


@pytest.mark.parametrize("directory", ["", "docs\nother", "file://docs"])
def test_capability_rejects_invalid_paths(directory: str, tmp_path: Path) -> None:
    workspace = (tmp_path / "workspace").resolve()
    workspace.mkdir()

    result = ListFilesCapability(workspace).list(directory)

    assert result.status is ListFilesStatus.INVALID_PATH


def test_capability_rejects_symlink_that_escapes_workspace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = (tmp_path / "workspace").resolve()
    workspace.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    link = workspace / "link"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except OSError:
        real_resolve = Path.resolve

        def resolve_link(path: Path, strict: bool = False) -> Path:
            if path == link:
                return real_resolve(outside, strict=strict)
            return real_resolve(path, strict=strict)

        monkeypatch.setattr(Path, "resolve", resolve_link)

    result = ListFilesCapability(workspace).list("link")

    assert result.status is ListFilesStatus.OUTSIDE_WORKSPACE


def test_capability_rejects_missing_directory_and_file_path(tmp_path: Path) -> None:
    workspace = (tmp_path / "workspace").resolve()
    workspace.mkdir()
    (workspace / "file.txt").write_text("file", encoding="utf-8")
    capability = ListFilesCapability(workspace)

    assert capability.list("missing").status is ListFilesStatus.NOT_FOUND
    assert capability.list("file.txt").status is ListFilesStatus.NOT_DIRECTORY


def test_capability_returns_typed_read_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = (tmp_path / "workspace").resolve()
    workspace.mkdir()

    def fail_iteration(path: Path) -> object:
        del path
        raise OSError("failure")

    monkeypatch.setattr(Path, "iterdir", fail_iteration)

    result = ListFilesCapability(workspace).list()

    assert result.status is ListFilesStatus.READ_FAILED
