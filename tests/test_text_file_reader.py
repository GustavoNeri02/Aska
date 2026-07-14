from pathlib import Path

import pytest

from capabilities.filesystem import (
    TextFileReader,
    TextFileReadError,
    TextFileReadErrorCode,
)


def test_reader_reads_utf8_file_inside_workspace(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    file_path = workspace / "docs" / "instrucoes.md"
    file_path.parent.mkdir(parents=True)
    file_path.write_bytes("Instruções do projeto.\n".encode())

    result = TextFileReader(workspace).read("docs/instrucoes.md")

    assert result.relative_path == "docs/instrucoes.md"
    assert result.content == "Instruções do projeto.\n"


def test_reader_rejects_traversal_and_absolute_paths(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("segredo", encoding="utf-8")
    reader = TextFileReader(workspace)

    for path in ("../outside.txt", "../missing.txt", str(outside.resolve())):
        with pytest.raises(TextFileReadError) as captured:
            reader.read(path)
        assert captured.value.code is TextFileReadErrorCode.OUTSIDE_WORKSPACE


def test_reader_rejects_symlink_that_escapes_workspace(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("segredo", encoding="utf-8")
    link = workspace / "link.txt"
    try:
        link.symlink_to(outside)
    except OSError:
        pytest.skip("symlinks are unavailable in this environment")

    with pytest.raises(TextFileReadError) as captured:
        TextFileReader(workspace).read("link.txt")

    assert captured.value.code is TextFileReadErrorCode.OUTSIDE_WORKSPACE


@pytest.mark.parametrize(
    ("relative_path", "expected_code"),
    [
        ("", TextFileReadErrorCode.INVALID_PATH),
        ("missing.md", TextFileReadErrorCode.NOT_FOUND),
        (".", TextFileReadErrorCode.NOT_FILE),
    ],
)
def test_reader_rejects_invalid_missing_and_directory_paths(
    relative_path: str,
    expected_code: TextFileReadErrorCode,
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    with pytest.raises(TextFileReadError) as captured:
        TextFileReader(workspace).read(relative_path)

    assert captured.value.code is expected_code


def test_reader_rejects_binary_empty_and_oversized_files(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "binary.bin").write_bytes(b"texto\0binario")
    (workspace / "empty.txt").write_text("  ", encoding="utf-8")
    (workspace / "large.txt").write_text("12345", encoding="utf-8")
    expected_errors = (
        (TextFileReader(workspace), "binary.bin", TextFileReadErrorCode.NOT_TEXT),
        (TextFileReader(workspace), "empty.txt", TextFileReadErrorCode.EMPTY),
        (TextFileReader(workspace, max_bytes=4), "large.txt", TextFileReadErrorCode.TOO_LARGE),
    )
    for reader, path, expected_code in expected_errors:
        with pytest.raises(TextFileReadError) as captured:
            reader.read(path)
        assert captured.value.code is expected_code


def test_reader_rejects_non_utf8_content(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "invalid.txt").write_bytes(b"\xff\xfe")

    with pytest.raises(TextFileReadError) as captured:
        TextFileReader(workspace).read("invalid.txt")

    assert captured.value.code is TextFileReadErrorCode.NOT_TEXT
