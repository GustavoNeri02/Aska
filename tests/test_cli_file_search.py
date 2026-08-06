from pathlib import Path

from apps.cli.app import run_conversation_loop
from capabilities.filesystem import SearchTextCapability
from packages.conversation import SearchTextIntent
from tests.cli_support import FakeProvider, create_input_reader, create_memory_service


class FakeTextSearchIntentInterpreter:
    def __init__(self, result: SearchTextIntent | None) -> None:
        self.result = result
        self.inputs: list[str] = []

    def interpret(self, user_input: str) -> SearchTextIntent | None:
        self.inputs.append(user_input)
        return self.result


def test_quoted_search_adds_temporary_matches_without_interpreter_or_history(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "service.py").write_text("class MemoryService:\n    pass\n", encoding="utf-8")
    provider = FakeProvider()
    interpreter = FakeTextSearchIntentInterpreter(None)

    run_conversation_loop(
        provider,
        memory_service=create_memory_service(tmp_path / "memories.json"),
        file_searcher=SearchTextCapability(workspace.resolve()),
        text_search_intent_interpreter=interpreter,
        input_reader=create_input_reader(
            ['Busque "MemoryService" nos arquivos Python.', "Continue.", "sair"]
        ),
        output_writer=lambda output: None,
    )

    assert interpreter.inputs == []
    assert "service.py:1" in provider.messages[0][-2].content
    assert "class MemoryService:" in provider.messages[0][-2].content
    assert not any("service.py:1" in message.content for message in provider.messages[1])


def test_natural_search_uses_interpreter_and_returns_matches(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    docs = workspace / "docs"
    docs.mkdir(parents=True)
    (docs / "roadmap.md").write_text("Busca vetorial permanece planned.", encoding="utf-8")
    provider = FakeProvider()
    message = "Onde a documentação fala sobre busca vetorial?"
    interpreter = FakeTextSearchIntentInterpreter(SearchTextIntent("busca vetorial", "docs", ".md"))

    run_conversation_loop(
        provider,
        memory_service=create_memory_service(tmp_path / "memories.json"),
        file_searcher=SearchTextCapability(workspace.resolve()),
        text_search_intent_interpreter=interpreter,
        input_reader=create_input_reader([message, "sair"]),
        output_writer=lambda output: None,
    )

    assert interpreter.inputs == [message]
    assert "docs/roadmap.md:1" in provider.messages[0][-2].content


def test_empty_text_search_is_reported_locally_without_conversation_provider(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "README.md").write_text("Aska local", encoding="utf-8")
    provider = FakeProvider()
    output: list[str] = []

    run_conversation_loop(
        provider,
        memory_service=create_memory_service(tmp_path / "memories.json"),
        file_searcher=SearchTextCapability(workspace.resolve()),
        text_search_intent_interpreter=FakeTextSearchIntentInterpreter(None),
        input_reader=create_input_reader(['Busque "inexistente" nos arquivos.', "sair"]),
        output_writer=output.append,
    )

    assert provider.messages == []
    assert "Nenhuma ocorrência correspondente foi encontrada." in output
