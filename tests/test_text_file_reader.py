from pathlib import Path

import pytest

from capabilities.filesystem import (
    ReadTextFileCapability,
    ReadTextFileStatus,
)


@pytest.mark.parametrize("relative_path", ["AGENTS.md", "docs/instrucoes.md"])
def test_capability_reads_utf8_file_without_writing(
    relative_path: str,
    tmp_path: Path,
) -> None:
    workspace = (tmp_path / "workspace").resolve()
    file_path = workspace / relative_path
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_bytes("Instruções do projeto.\n".encode())
    content_before = file_path.read_bytes()
    modified_before = file_path.stat().st_mtime_ns

    result = ReadTextFileCapability(workspace).read(relative_path)

    assert result.status is ReadTextFileStatus.SUCCESS
    assert result.relative_path == relative_path
    assert result.content == "Instruções do projeto.\n"
    assert file_path.read_bytes() == content_before
    assert file_path.stat().st_mtime_ns == modified_before


@pytest.mark.parametrize(
    "path",
    ["../outside.txt", "../missing.txt", "/etc/passwd", r"C:\Windows\win.ini"],
)
def test_capability_rejects_traversal_and_absolute_paths(path: str, tmp_path: Path) -> None:
    workspace = (tmp_path / "workspace").resolve()
    workspace.mkdir()
    (tmp_path / "outside.txt").write_text("segredo", encoding="utf-8")

    result = ReadTextFileCapability(workspace).read(path)

    assert result.status is ReadTextFileStatus.OUTSIDE_WORKSPACE
    assert result.relative_path is None
    assert result.content is None


def test_capability_rejects_file_uri(tmp_path: Path) -> None:
    workspace = (tmp_path / "workspace").resolve()
    workspace.mkdir()

    result = ReadTextFileCapability(workspace).read("file:///etc/passwd")

    assert result.status is ReadTextFileStatus.INVALID_PATH


def test_capability_rejects_symlink_that_escapes_workspace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = (tmp_path / "workspace").resolve()
    workspace.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("segredo", encoding="utf-8")
    link = workspace / "link.txt"
    try:
        link.symlink_to(outside)
    except OSError:
        real_resolve = Path.resolve

        def resolve_link(path: Path, strict: bool = False) -> Path:
            if path == link:
                return real_resolve(outside, strict=strict)
            return real_resolve(path, strict=strict)

        monkeypatch.setattr(Path, "resolve", resolve_link)

    result = ReadTextFileCapability(workspace).read("link.txt")

    assert result.status is ReadTextFileStatus.OUTSIDE_WORKSPACE


@pytest.mark.parametrize(
    ("relative_path", "expected_status"),
    [
        ("", ReadTextFileStatus.INVALID_PATH),
        ("missing.md", ReadTextFileStatus.NOT_FOUND),
        (".", ReadTextFileStatus.NOT_FILE),
    ],
)
def test_capability_rejects_invalid_missing_and_directory_paths(
    relative_path: str,
    expected_status: ReadTextFileStatus,
    tmp_path: Path,
) -> None:
    workspace = (tmp_path / "workspace").resolve()
    workspace.mkdir()

    result = ReadTextFileCapability(workspace).read(relative_path)

    assert result.status is expected_status


def test_capability_rejects_binary_empty_and_oversized_files(tmp_path: Path) -> None:
    workspace = (tmp_path / "workspace").resolve()
    workspace.mkdir()
    (workspace / "binary.bin").write_bytes(b"texto\0binario")
    (workspace / "empty.txt").write_text("  ", encoding="utf-8")
    (workspace / "large.txt").write_text("x" * (64 * 1024 + 1), encoding="utf-8")
    expected_results = (
        (ReadTextFileCapability(workspace), "binary.bin", ReadTextFileStatus.NOT_TEXT),
        (ReadTextFileCapability(workspace), "empty.txt", ReadTextFileStatus.EMPTY),
        (ReadTextFileCapability(workspace), "large.txt", ReadTextFileStatus.TOO_LARGE),
    )

    for capability, path, expected_status in expected_results:
        assert capability.read(path).status is expected_status


def test_capability_rejects_non_utf8_content(tmp_path: Path) -> None:
    workspace = (tmp_path / "workspace").resolve()
    workspace.mkdir()
    (workspace / "invalid.txt").write_bytes(b"\xff\xfe")

    result = ReadTextFileCapability(workspace).read("invalid.txt")

    assert result.status is ReadTextFileStatus.NOT_TEXT


def test_capability_returns_typed_read_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = (tmp_path / "workspace").resolve()
    workspace.mkdir()
    (workspace / "file.txt").write_text("conteúdo", encoding="utf-8")

    def fail_read(path: Path) -> bytes:
        del path
        raise OSError("falha simulada")

    monkeypatch.setattr(Path, "read_bytes", fail_read)

    result = ReadTextFileCapability(workspace).read("file.txt")

    assert result.status is ReadTextFileStatus.READ_FAILED


def test_capability_requires_an_absolute_resolved_workspace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    Path("relative-workspace").mkdir()

    with pytest.raises(ValueError, match="absolute"):
        ReadTextFileCapability(Path("relative-workspace"))
