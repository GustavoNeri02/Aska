from pathlib import Path

from apps.cli.app import run_conversation_loop
from capabilities.filesystem import TextFileReader
from packages.conversation import ReadTextFileIntent
from tests.cli_support import (
    FakeFileIntentInterpreter,
    FakeProvider,
    create_input_reader,
    create_memory_service,
)


def test_file_request_adds_temporary_context_without_contaminating_next_request(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "AGENTS.md").write_text("Regra exclusiva do arquivo.", encoding="utf-8")
    provider = FakeProvider()
    interpreter = FakeFileIntentInterpreter(ReadTextFileIntent("AGENTS.md"))

    run_conversation_loop(
        provider,
        memory_service=create_memory_service(tmp_path / "memories.json"),
        file_reader=TextFileReader(workspace),
        file_intent_interpreter=interpreter,
        input_reader=create_input_reader(
            ["Leia AGENTS.md e resuma.", "Continue a conversa.", "sair"]
        ),
        output_writer=lambda message: None,
    )

    assert interpreter.inputs == ["Leia AGENTS.md e resuma."]
    assert "Fonte: AGENTS.md" in provider.messages[0][0].content
    assert "Regra exclusiva do arquivo." in provider.messages[0][0].content
    assert "Regra exclusiva do arquivo." not in provider.messages[1][0].content
    assert provider.messages[0][-1].content == "Leia AGENTS.md e resuma."


def test_file_request_outside_workspace_is_consumed_without_model_response(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (tmp_path / "outside.txt").write_text("segredo", encoding="utf-8")
    provider = FakeProvider()
    output: list[str] = []

    run_conversation_loop(
        provider,
        memory_service=create_memory_service(tmp_path / "memories.json"),
        file_reader=TextFileReader(workspace),
        file_intent_interpreter=FakeFileIntentInterpreter(ReadTextFileIntent("../outside.txt")),
        input_reader=create_input_reader(["Leia o arquivo outside.txt.", "sair"]),
        output_writer=output.append,
    )

    assert provider.messages == []
    assert "Acesso negado: o arquivo deve estar dentro do workspace permitido." in output


def test_invalid_file_interpretation_falls_back_to_normal_conversation(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    provider = FakeProvider()
    interpreter = FakeFileIntentInterpreter(None)
    message = "Leia AGENTS.md e resuma."

    run_conversation_loop(
        provider,
        memory_service=create_memory_service(tmp_path / "memories.json"),
        file_reader=TextFileReader(workspace),
        file_intent_interpreter=interpreter,
        input_reader=create_input_reader([message, "sair"]),
        output_writer=lambda output: None,
    )

    assert interpreter.inputs == [message]
    assert provider.messages[0][-1].content == message
    assert "Contexto temporário" not in provider.messages[0][0].content


def test_common_message_does_not_call_file_interpreter(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    provider = FakeProvider()
    interpreter = FakeFileIntentInterpreter(ReadTextFileIntent("AGENTS.md"))

    run_conversation_loop(
        provider,
        memory_service=create_memory_service(tmp_path / "memories.json"),
        file_reader=TextFileReader(workspace),
        file_intent_interpreter=interpreter,
        input_reader=create_input_reader(["Como vai?", "sair"]),
        output_writer=lambda output: None,
    )

    assert interpreter.inputs == []
    assert provider.messages[0][-1].content == "Como vai?"
