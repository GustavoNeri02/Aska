from pathlib import Path

from apps.cli.app import run_conversation_loop
from capabilities.filesystem import SearchTextCapability
from packages.conversation import SearchTextIntent
from tests.cli_support import FakeProvider, create_input_reader, create_temp_memory_service


class FixedSearchInterpreter:
    def __init__(self, intent: SearchTextIntent | None) -> None:
        self.intent = intent

    def interpret(self, user_input: str) -> SearchTextIntent | None:
        del user_input
        return self.intent


def test_empty_search_result_is_presented_by_model(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "README.md").write_text("Aska", encoding="utf-8")
    provider = FakeProvider('{"type":"reply","content":"Não encontrei ocorrências."}')

    run_conversation_loop(
        provider,
        create_temp_memory_service(tmp_path),
        file_searcher=SearchTextCapability(workspace),
        text_search_intent_interpreter=FixedSearchInterpreter(None),
        input_reader=create_input_reader(['Busque "inexistente" nos arquivos.', "sair"]),
        output_writer=lambda _: None,
    )

    assert '"status": "success"' in provider.messages[0][-1].content
    assert '"matches": []' in provider.messages[0][-1].content


def test_search_matches_are_temporary_context(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "README.md").write_text("prefixo needle sufixo", encoding="utf-8")
    provider = FakeProvider("Resumo")

    run_conversation_loop(
        provider,
        create_temp_memory_service(tmp_path),
        file_searcher=SearchTextCapability(workspace),
        text_search_intent_interpreter=FixedSearchInterpreter(SearchTextIntent("needle")),
        input_reader=create_input_reader(["Quais arquivos mencionam needle?", "Continue", "sair"]),
        output_writer=lambda _: None,
    )

    assert any(
        "README.md:1: prefixo needle sufixo" in message.content for message in provider.messages[0]
    )
    assert all("prefixo needle sufixo" not in message.content for message in provider.messages[1])
