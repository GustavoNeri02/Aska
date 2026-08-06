from pathlib import Path

from apps.cli.app import run_conversation_loop
from capabilities.filesystem import ListFilesCapability, ReadTextFileCapability
from packages.conversation import ListFilesIntent, ReadTextFileIntent
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
        file_reader=ReadTextFileCapability(workspace.resolve()),
        file_intent_interpreter=interpreter,
        input_reader=create_input_reader(
            ["Leia AGENTS.md e resuma.", "Continue a conversa.", "sair"]
        ),
        output_writer=lambda message: None,
    )

    assert interpreter.inputs == []
    assert "Fonte: AGENTS.md" in provider.messages[0][-2].content
    assert "Regra exclusiva do arquivo." in provider.messages[0][-2].content
    assert not any(
        "Regra exclusiva do arquivo." in message.content for message in provider.messages[1]
    )
    assert provider.messages[0][-1].content == "Leia AGENTS.md e resuma."
    assert create_memory_service(tmp_path / "memories.json").list() == []


def test_natural_summary_with_relative_path_reads_file_deterministically(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    document = workspace / "docs" / "product" / "vision.md"
    document.parent.mkdir(parents=True)
    document.write_text("Visão real do produto.", encoding="utf-8")
    provider = FakeProvider()
    interpreter = FakeFileIntentInterpreter(None)

    run_conversation_loop(
        provider,
        memory_service=create_memory_service(tmp_path / "memories.json"),
        file_reader=ReadTextFileCapability(workspace.resolve()),
        file_intent_interpreter=interpreter,
        input_reader=create_input_reader([r"Resuma docs\product\vision.md", "sair"]),
        output_writer=lambda message: None,
    )

    assert interpreter.inputs == []
    assert "Visão real do produto." in provider.messages[0][-2].content


def test_bare_filename_is_discovered_and_read_when_match_is_unique(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    document = workspace / "docs" / "product" / "vision.md"
    document.parent.mkdir(parents=True)
    document.write_text("Visão encontrada pelo nome.", encoding="utf-8")
    provider = FakeProvider()

    run_conversation_loop(
        provider,
        memory_service=create_memory_service(tmp_path / "memories.json"),
        file_reader=ReadTextFileCapability(workspace.resolve()),
        file_lister=ListFilesCapability(workspace.resolve()),
        file_intent_interpreter=FakeFileIntentInterpreter(None),
        input_reader=create_input_reader(["Resuma vision.md", "sair"]),
        output_writer=lambda message: None,
    )

    assert "Fonte: docs/product/vision.md" in provider.messages[0][-2].content
    assert "Visão encontrada pelo nome." in provider.messages[0][-2].content


def test_bare_filename_with_multiple_matches_requests_relative_path(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    for directory in (workspace / "docs", workspace / "notes"):
        directory.mkdir(parents=True)
        (directory / "vision.md").write_text("conteúdo", encoding="utf-8")
    provider = FakeProvider()
    output: list[str] = []

    run_conversation_loop(
        provider,
        memory_service=create_memory_service(tmp_path / "memories.json"),
        file_reader=ReadTextFileCapability(workspace.resolve()),
        file_lister=ListFilesCapability(workspace.resolve()),
        file_intent_interpreter=FakeFileIntentInterpreter(None),
        input_reader=create_input_reader(["Resuma vision.md", "sair"]),
        output_writer=output.append,
    )

    assert provider.messages == []
    assert (
        "Não foi possível escolher um único arquivo. Informe o caminho relativo:\n"
        "- docs/vision.md\n"
        "- notes/vision.md"
    ) in output


def test_absolute_file_path_is_consumed_with_local_guidance(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    provider = FakeProvider()
    output: list[str] = []

    run_conversation_loop(
        provider,
        memory_service=create_memory_service(tmp_path / "memories.json"),
        file_reader=ReadTextFileCapability(workspace.resolve()),
        file_intent_interpreter=FakeFileIntentInterpreter(None),
        input_reader=create_input_reader(
            [r"Retorne exatamente o que está em D:\Projetos\Aska\README.md", "sair"]
        ),
        output_writer=output.append,
    )

    assert provider.messages == []
    assert (
        "Acesso negado: o arquivo deve estar dentro do workspace permitido. "
        "Use um caminho relativo ao workspace."
    ) in output


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
        file_reader=ReadTextFileCapability(workspace.resolve()),
        file_intent_interpreter=FakeFileIntentInterpreter(ReadTextFileIntent("../outside.txt")),
        input_reader=create_input_reader(["Você pode ler o arquivo outside.txt?", "sair"]),
        output_writer=output.append,
    )

    assert provider.messages == []
    assert (
        "Acesso negado: o arquivo deve estar dentro do workspace permitido. "
        "Use um caminho relativo ao workspace."
    ) in output


def test_file_read_error_is_consumed_without_conversational_provider(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    provider = FakeProvider()
    output: list[str] = []

    run_conversation_loop(
        provider,
        memory_service=create_memory_service(tmp_path / "memories.json"),
        file_reader=ReadTextFileCapability(workspace.resolve()),
        file_intent_interpreter=FakeFileIntentInterpreter(ReadTextFileIntent("missing.txt")),
        input_reader=create_input_reader(["Você pode ler missing.txt?", "sair"]),
        output_writer=output.append,
    )

    assert provider.messages == []
    assert "O arquivo informado não foi encontrado." in output


def test_invalid_file_interpretation_falls_back_to_normal_conversation(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    provider = FakeProvider()
    interpreter = FakeFileIntentInterpreter(None)
    message = "Você poderia ler AGENTS.md e resumir?"

    run_conversation_loop(
        provider,
        memory_service=create_memory_service(tmp_path / "memories.json"),
        file_reader=ReadTextFileCapability(workspace.resolve()),
        file_intent_interpreter=interpreter,
        input_reader=create_input_reader([message, "sair"]),
        output_writer=lambda output: None,
    )

    assert interpreter.inputs == [message]
    assert provider.messages[0][-1].content == message
    assert not any("Documento temporário" in message.content for message in provider.messages[0])


def test_common_message_does_not_call_file_interpreter(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    provider = FakeProvider()
    interpreter = FakeFileIntentInterpreter(ReadTextFileIntent("AGENTS.md"))

    run_conversation_loop(
        provider,
        memory_service=create_memory_service(tmp_path / "memories.json"),
        file_reader=ReadTextFileCapability(workspace.resolve()),
        file_intent_interpreter=interpreter,
        input_reader=create_input_reader(["Como vai?", "sair"]),
        output_writer=lambda output: None,
    )

    assert interpreter.inputs == []
    assert provider.messages[0][-1].content == "Como vai?"


def test_file_listing_is_temporary_context_and_does_not_read_contents(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "app.py").write_text("segredo do arquivo", encoding="utf-8")
    provider = FakeProvider()
    interpreter = FakeFileIntentInterpreter(ListFilesIntent(extension=".py"))

    run_conversation_loop(
        provider,
        memory_service=create_memory_service(tmp_path / "memories.json"),
        file_reader=ReadTextFileCapability(workspace.resolve()),
        file_lister=ListFilesCapability(workspace.resolve()),
        file_intent_interpreter=interpreter,
        input_reader=create_input_reader(
            ["Veja quais arquivos Python existem.", "Continue.", "sair"]
        ),
        output_writer=lambda output: None,
    )

    assert interpreter.inputs == ["Veja quais arquivos Python existem."]
    assert "- app.py" in provider.messages[0][-2].content
    assert "segredo do arquivo" not in provider.messages[0][-2].content
    assert not any("- app.py" in message.content for message in provider.messages[1])
