from pathlib import Path

from apps.cli.app import run_conversation_loop
from capabilities.filesystem import ListFilesCapability, ReadTextFileCapability
from packages.conversation import ReadTextFileIntent
from tests.cli_support import (
    FakeFileIntentInterpreter,
    FakeProvider,
    create_input_reader,
    create_temp_memory_service,
)


def test_file_content_is_temporary_model_context(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "vision.md").write_text("Aska local", encoding="utf-8")
    provider = FakeProvider("Resumo gerado")

    run_conversation_loop(
        provider,
        create_temp_memory_service(tmp_path),
        file_reader=ReadTextFileCapability(workspace),
        file_intent_interpreter=FakeFileIntentInterpreter(ReadTextFileIntent("vision.md")),
        input_reader=create_input_reader(["Resuma vision.md", "sair"]),
        output_writer=lambda _: None,
    )

    assert any("Aska local" in message.content for message in provider.messages[0])


def test_missing_file_is_presented_by_model_from_structured_status(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    provider = FakeProvider('{"type":"reply","content":"Não encontrei."}')

    run_conversation_loop(
        provider,
        create_temp_memory_service(tmp_path),
        file_reader=ReadTextFileCapability(workspace),
        file_intent_interpreter=FakeFileIntentInterpreter(ReadTextFileIntent("missing.md")),
        input_reader=create_input_reader(["Leia missing.md", "sair"]),
        output_writer=lambda _: None,
    )

    assert '"status": "not_found"' in provider.messages[0][-1].content


def test_ambiguous_file_discovery_does_not_choose_path(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    for folder in (workspace / "docs", workspace / "notes"):
        folder.mkdir(parents=True)
        (folder / "vision.md").write_text("texto", encoding="utf-8")
    provider = FakeProvider('{"type":"reply","content":"Encontrei dois arquivos."}')

    run_conversation_loop(
        provider,
        create_temp_memory_service(tmp_path),
        file_reader=ReadTextFileCapability(workspace),
        file_lister=ListFilesCapability(workspace),
        file_intent_interpreter=FakeFileIntentInterpreter(None),
        input_reader=create_input_reader(["Resuma vision.md", "sair"]),
        output_writer=lambda _: None,
    )

    event = provider.messages[0][-1].content
    assert "docs/vision.md" in event
    assert "notes/vision.md" in event
    assert '"kind": "file_discovery_ambiguous"' in event
