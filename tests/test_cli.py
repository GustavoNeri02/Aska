from collections.abc import Callable, Iterator
from pathlib import Path

import pytest

from apps.cli.app import (
    build_banner,
    run_conversation_loop,
)
from packages.models import ModelProviderError
from packages.runtime.memory import MemoryStore, ReplaceResult


def create_memory_store(tmp_path: Path) -> MemoryStore:
    return MemoryStore(path=tmp_path / "memories.json")


class FakeProvider:
    def __init__(self, response: str = "Resposta local") -> None:
        self.response = response
        self.messages: list[str] = []

    def generate(self, message: str) -> str:
        self.messages.append(message)
        return self.response


class FailingProvider:
    def generate(self, message: str) -> str:
        del message
        raise ModelProviderError("Modelo indisponível")


class FailingThenWorkingProvider:
    def __init__(self, response: str = "Resposta local") -> None:
        self.response = response
        self.messages: list[str] = []
        self._should_fail = True

    def generate(self, message: str) -> str:
        self.messages.append(message)
        if self._should_fail:
            self._should_fail = False
            raise ModelProviderError("Modelo indisponível")
        return self.response


def create_input_reader(messages: list[str]) -> Callable[[str], str]:
    iterator: Iterator[str] = iter(messages)

    def read_input(_: str) -> str:
        return next(iterator)

    return read_input


def create_interrupting_reader(error: BaseException) -> Callable[[str], str]:
    def read_input(_: str) -> str:
        raise error

    return read_input


def test_build_banner_contains_application_name() -> None:
    banner = build_banner()

    assert "Aska" in banner


def test_conversation_sends_message_to_provider(tmp_path: Path) -> None:
    output: list[str] = []
    provider = FakeProvider()

    run_conversation_loop(
        provider,
        input_reader=create_input_reader(["Olá", "sair"]),
        output_writer=output.append,
        memory_store=create_memory_store(tmp_path),
    )

    assert provider.messages == ["Olá"]
    assert "Aska > Resposta local" in output


def test_conversation_sends_recent_history_as_context(tmp_path: Path) -> None:
    output: list[str] = []
    provider = FakeProvider()

    run_conversation_loop(
        provider,
        input_reader=create_input_reader(["Olá", "Me conte mais", "sair"]),
        output_writer=output.append,
        memory_store=create_memory_store(tmp_path),
    )

    assert provider.messages[0] == "Olá"
    assert "Histórico da sessão" in provider.messages[1]
    assert "Você: Olá" in provider.messages[1]
    assert "Aska: Resposta local" in provider.messages[1]
    assert "Você: Me conte mais" in provider.messages[1]
    assert "Aska > Resposta local" in output


@pytest.mark.parametrize("command", ["sair", "exit", "quit", " SAIR "])
def test_conversation_stops_when_user_types_exit_command(command: str, tmp_path: Path) -> None:
    output: list[str] = []

    run_conversation_loop(
        FakeProvider(),
        input_reader=create_input_reader([command]),
        output_writer=output.append,
        memory_store=create_memory_store(tmp_path),
    )

    assert "Até mais, Gustavo." in output


def test_conversation_ignores_blank_messages(tmp_path: Path) -> None:
    output: list[str] = []

    run_conversation_loop(
        FakeProvider(),
        input_reader=create_input_reader(["", "   ", "Olá", "sair"]),
        output_writer=output.append,
        memory_store=create_memory_store(tmp_path),
    )

    responses = [line for line in output if line.startswith("Aska >")]

    assert len(responses) == 1


@pytest.mark.parametrize("error", [EOFError(), KeyboardInterrupt()])
def test_conversation_handles_interruption(error: BaseException, tmp_path: Path) -> None:
    output: list[str] = []

    run_conversation_loop(
        FakeProvider(),
        input_reader=create_interrupting_reader(error),
        output_writer=output.append,
        memory_store=create_memory_store(tmp_path),
    )

    assert "\nEncerrando o Aska." in output


def test_conversation_reports_provider_error_and_keeps_running(tmp_path: Path) -> None:
    output: list[str] = []

    run_conversation_loop(
        FailingProvider(),
        input_reader=create_input_reader(["Olá", "sair"]),
        output_writer=output.append,
        memory_store=create_memory_store(tmp_path),
    )

    assert "Aska > Modelo indisponível" in output
    assert "Até mais, Gustavo." in output


def test_memory_store_persists_memories_to_disk(tmp_path: Path) -> None:
    store = MemoryStore(path=tmp_path / "memories.json")

    store.add("gosto de python")

    assert store.list() == ["gosto de python"]
    assert (tmp_path / "memories.json").exists()


def test_memory_store_ignores_blank_entries(tmp_path: Path) -> None:
    store = MemoryStore(path=tmp_path / "memories.json")

    store.add("   ")

    assert store.list() == []


def test_memory_store_does_not_store_duplicates(tmp_path: Path) -> None:
    store = MemoryStore(path=tmp_path / "memories.json")

    store.add("gosto de python")
    store.add("gosto de python")

    assert store.list() == ["gosto de python"]


def test_memory_store_persists_between_instances(tmp_path: Path) -> None:
    path = tmp_path / "memories.json"
    first_store = MemoryStore(path=path)
    first_store.add("gosto de python")

    second_store = MemoryStore(path=path)

    assert second_store.list() == ["gosto de python"]


def test_memory_store_removes_existing_memory(tmp_path: Path) -> None:
    store = MemoryStore(path=tmp_path / "memories.json")

    store.add("gosto de python")
    removed = store.remove("gosto de python")

    assert removed is True
    assert store.list() == []


def test_memory_store_reports_missing_memory_without_changes(tmp_path: Path) -> None:
    store = MemoryStore(path=tmp_path / "memories.json")

    store.add("gosto de python")
    removed = store.remove("gosto de dart")

    assert removed is False
    assert store.list() == ["gosto de python"]


def test_memory_store_ignores_blank_removal_entries(tmp_path: Path) -> None:
    store = MemoryStore(path=tmp_path / "memories.json")

    store.add("gosto de python")
    removed = store.remove("   ")

    assert removed is False
    assert store.list() == ["gosto de python"]


def test_memory_store_persists_removal_between_instances(tmp_path: Path) -> None:
    path = tmp_path / "memories.json"
    first_store = MemoryStore(path=path)
    first_store.add("gosto de python")
    first_store.remove("gosto de python")

    second_store = MemoryStore(path=path)

    assert second_store.list() == []


def test_memory_store_replaces_existing_memory(tmp_path: Path) -> None:
    store = MemoryStore(path=tmp_path / "memories.json")

    store.add("gosto de python")
    result = store.replace("gosto de python", "gosto de dart")

    assert result is ReplaceResult.REPLACED
    assert store.list() == ["gosto de dart"]


def test_memory_store_reports_missing_memory_without_changes_on_replace(tmp_path: Path) -> None:
    store = MemoryStore(path=tmp_path / "memories.json")

    store.add("gosto de python")
    result = store.replace("gosto de rust", "gosto de dart")

    assert result is ReplaceResult.NOT_FOUND
    assert store.list() == ["gosto de python"]


def test_memory_store_reports_invalid_values_on_replace(tmp_path: Path) -> None:
    store = MemoryStore(path=tmp_path / "memories.json")

    store.add("gosto de python")
    assert store.replace("   ", "gosto de dart") is ReplaceResult.INVALID
    assert store.replace("gosto de python", "   ") is ReplaceResult.INVALID
    assert store.list() == ["gosto de python"]


def test_memory_store_reports_duplicate_on_replace(tmp_path: Path) -> None:
    store = MemoryStore(path=tmp_path / "memories.json")

    store.add("gosto de python")
    store.add("gosto de dart")
    result = store.replace("gosto de python", "gosto de dart")

    assert result is ReplaceResult.DUPLICATE
    assert store.list() == ["gosto de python", "gosto de dart"]


def test_memory_store_reports_unchanged_when_replacement_is_same_value(tmp_path: Path) -> None:
    store = MemoryStore(path=tmp_path / "memories.json")

    store.add("gosto de python")
    result = store.replace("gosto de python", "gosto de python")

    assert result is ReplaceResult.UNCHANGED
    assert store.list() == ["gosto de python"]


def test_memory_store_preserves_position_when_replacing(tmp_path: Path) -> None:
    store = MemoryStore(path=tmp_path / "memories.json")

    store.add("gosto de python")
    store.add("gosto de dart")
    store.add("gosto de rust")
    store.replace("gosto de dart", "gosto de go")

    assert store.list() == ["gosto de python", "gosto de go", "gosto de rust"]


def test_memory_store_persists_replacement_between_instances(tmp_path: Path) -> None:
    path = tmp_path / "memories.json"
    first_store = MemoryStore(path=path)
    first_store.add("gosto de python")
    first_store.replace("gosto de python", "gosto de dart")

    second_store = MemoryStore(path=path)

    assert second_store.list() == ["gosto de dart"]


def test_memory_store_searches_partial_and_case_insensitive(tmp_path: Path) -> None:
    store = MemoryStore(path=tmp_path / "memories.json")

    store.add("gosto de python")
    store.add("gosto de dart")
    store.add("aprender rust")

    assert store.search("PYTH") == ["gosto de python"]
    assert store.search("gosto") == ["gosto de python", "gosto de dart"]


def test_memory_store_searches_exact_matches_and_accented_text(tmp_path: Path) -> None:
    store = MemoryStore(path=tmp_path / "memories.json")

    store.add("gosto de python")
    store.add("gosto de dart")
    store.add("café da manhã")

    assert store.search("gosto de python") == ["gosto de python"]
    assert store.search("CAFÉ") == ["café da manhã"]


def test_memory_store_returns_empty_results_without_rewriting_file(tmp_path: Path) -> None:
    path = tmp_path / "memories.json"
    store = MemoryStore(path=path)

    store.add("gosto de python")
    before = path.read_text(encoding="utf-8")
    results = store.search("rust")

    assert results == []
    assert path.read_text(encoding="utf-8") == before


def test_memory_store_ignores_blank_search_terms(tmp_path: Path) -> None:
    store = MemoryStore(path=tmp_path / "memories.json")

    store.add("gosto de python")

    assert store.search("   ") == []


def test_conversation_handles_invalid_json_without_broken_flow(tmp_path: Path) -> None:
    output: list[str] = []
    path = tmp_path / "memories.json"
    path.write_text("{not valid json", encoding="utf-8")
    store = MemoryStore(path=path)

    run_conversation_loop(
        FakeProvider(),
        input_reader=create_input_reader(["memórias", "sair"]),
        output_writer=output.append,
        memory_store=store,
    )

    assert "(nenhuma memória registrada)" in output


def test_run_conversation_loop_uses_injected_store_without_touching_real_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    output: list[str] = []

    run_conversation_loop(
        FakeProvider(),
        input_reader=create_input_reader(["lembrar: gosto de python", "sair"]),
        output_writer=output.append,
        memory_store=create_memory_store(tmp_path),
    )

    assert not (tmp_path / "data" / "memory" / "memories.json").exists()


def test_conversation_can_store_and_report_search_no_results(tmp_path: Path) -> None:
    output: list[str] = []
    store = MemoryStore(path=tmp_path / "memories.json")

    run_conversation_loop(
        FakeProvider(),
        input_reader=create_input_reader(
            ["lembrar: gosto de python", "buscar memória: rust", "sair"]
        ),
        output_writer=output.append,
        memory_store=store,
    )

    assert "Memória registrada localmente." in output
    assert "Nenhuma memória encontrada para o termo." in output


def test_conversation_can_remove_memories_and_list_current_state(tmp_path: Path) -> None:
    output: list[str] = []
    store = MemoryStore(path=tmp_path / "memories.json")

    run_conversation_loop(
        FakeProvider(),
        input_reader=create_input_reader(
            ["lembrar: gosto de python", "esquecer: gosto de python", "memórias", "sair"]
        ),
        output_writer=output.append,
        memory_store=store,
    )

    assert "Memória removida localmente." in output
    assert "(nenhuma memória registrada)" in output


def test_conversation_can_edit_memories_and_list_current_state(tmp_path: Path) -> None:
    output: list[str] = []
    store = MemoryStore(path=tmp_path / "memories.json")

    run_conversation_loop(
        FakeProvider(),
        input_reader=create_input_reader(
            [
                "lembrar: gosto de python",
                "editar memória: gosto de python -> gosto de dart",
                "memórias",
                "sair",
            ]
        ),
        output_writer=output.append,
        memory_store=store,
    )

    assert "Memória editada localmente." in output
    assert "gosto de dart" in output
    assert "gosto de python" not in output


def test_conversation_reports_missing_memory_when_edit_fails(tmp_path: Path) -> None:
    output: list[str] = []
    store = MemoryStore(path=tmp_path / "memories.json")

    run_conversation_loop(
        FakeProvider(),
        input_reader=create_input_reader(
            ["editar memória: gosto de rust -> gosto de dart", "sair"]
        ),
        output_writer=output.append,
        memory_store=store,
    )

    assert "Nenhuma memória correspondente foi encontrada." in output


def test_conversation_can_search_memories(tmp_path: Path) -> None:
    output: list[str] = []
    store = MemoryStore(path=tmp_path / "memories.json")

    run_conversation_loop(
        FakeProvider(),
        input_reader=create_input_reader(
            [
                "lembrar: gosto de python",
                "lembrar: gosto de dart",
                "buscar memória: gosto",
                "sair",
            ]
        ),
        output_writer=output.append,
        memory_store=store,
    )

    assert "Resultados da busca:" in output
    assert "gosto de python" in output
    assert "gosto de dart" in output


def test_conversation_reports_missing_search_results(tmp_path: Path) -> None:
    output: list[str] = []
    store = MemoryStore(path=tmp_path / "memories.json")

    run_conversation_loop(
        FakeProvider(),
        input_reader=create_input_reader(
            ["lembrar: gosto de python", "buscar memória: rust", "sair"]
        ),
        output_writer=output.append,
        memory_store=store,
    )

    assert "Nenhuma memória encontrada para o termo." in output


def test_conversation_reports_guidance_for_empty_search_term(tmp_path: Path) -> None:
    output: list[str] = []
    store = MemoryStore(path=tmp_path / "memories.json")

    run_conversation_loop(
        FakeProvider(),
        input_reader=create_input_reader(["buscar memória:   ", "sair"]),
        output_writer=output.append,
        memory_store=store,
    )

    assert "Use: buscar memória: <termo>" in output


def test_conversation_reports_duplicate_and_invalid_edit_results(tmp_path: Path) -> None:
    output: list[str] = []
    store = MemoryStore(path=tmp_path / "memories.json")

    run_conversation_loop(
        FakeProvider(),
        input_reader=create_input_reader(
            [
                "lembrar: gosto de python",
                "lembrar: gosto de dart",
                "editar memória: gosto de python -> gosto de dart",
                "editar memória: gosto de python ->  ",
                "sair",
            ]
        ),
        output_writer=output.append,
        memory_store=store,
    )

    assert "Já existe uma memória com esse conteúdo." in output
    assert "Informe a memória atual e o novo conteúdo." in output


def test_conversation_reports_unchanged_edit_result(tmp_path: Path) -> None:
    output: list[str] = []
    store = MemoryStore(path=tmp_path / "memories.json")

    run_conversation_loop(
        FakeProvider(),
        input_reader=create_input_reader(
            [
                "lembrar: gosto de python",
                "editar memória: gosto de python -> gosto de python",
                "sair",
            ]
        ),
        output_writer=output.append,
        memory_store=store,
    )

    assert "A memória já possui esse conteúdo." in output


def test_conversation_reports_short_guidance_for_malformed_edit_command(tmp_path: Path) -> None:
    output: list[str] = []
    store = MemoryStore(path=tmp_path / "memories.json")

    run_conversation_loop(
        FakeProvider(),
        input_reader=create_input_reader(["editar memória: gosto de python", "sair"]),
        output_writer=output.append,
        memory_store=store,
    )

    assert "Use: editar memória: <atual> -> <novo>" in output


def test_conversation_updates_provider_context_after_edit(tmp_path: Path) -> None:
    provider = FakeProvider()
    store = MemoryStore(path=tmp_path / "memories.json")

    run_conversation_loop(
        provider,
        input_reader=create_input_reader(
            [
                "lembrar: gosto de python",
                "editar memória: gosto de python -> gosto de dart",
                "Olá",
                "sair",
            ]
        ),
        output_writer=lambda message: None,
        memory_store=store,
    )

    assert len(provider.messages) == 1
    assert "Memórias salvas:" in provider.messages[0]
    assert "- gosto de dart" in provider.messages[0]
    assert "gosto de python" not in provider.messages[0]


def test_run_conversation_loop_edit_uses_injected_store_without_touching_real_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    output: list[str] = []

    run_conversation_loop(
        FakeProvider(),
        input_reader=create_input_reader(
            ["lembrar: gosto de python", "editar memória: gosto de python -> gosto de dart", "sair"]
        ),
        output_writer=output.append,
        memory_store=create_memory_store(tmp_path),
    )

    assert not (tmp_path / "data" / "memory" / "memories.json").exists()


def test_conversation_reports_missing_memory_when_removal_fails(tmp_path: Path) -> None:
    output: list[str] = []
    store = MemoryStore(path=tmp_path / "memories.json")

    run_conversation_loop(
        FakeProvider(),
        input_reader=create_input_reader(["esquecer: gosto de rust", "sair"]),
        output_writer=output.append,
        memory_store=store,
    )

    assert "Nenhuma memória correspondente foi encontrada." in output


def test_conversation_does_not_include_removed_memory_in_model_context(tmp_path: Path) -> None:
    provider = FakeProvider()
    store = MemoryStore(path=tmp_path / "memories.json")

    run_conversation_loop(
        provider,
        input_reader=create_input_reader(
            ["lembrar: gosto de python", "esquecer: gosto de python", "Olá", "sair"]
        ),
        output_writer=lambda message: None,
        memory_store=store,
    )

    assert len(provider.messages) == 1
    assert "Memórias salvas:" not in provider.messages[0]
    assert "gosto de python" not in provider.messages[0]
    assert provider.messages[0] == "Olá"


def test_conversation_includes_saved_memories_in_model_context(tmp_path: Path) -> None:
    provider = FakeProvider()
    store = MemoryStore(path=tmp_path / "memories.json")

    run_conversation_loop(
        provider,
        input_reader=create_input_reader(["lembrar: gosto de python", "Olá", "sair"]),
        output_writer=lambda message: None,
        memory_store=store,
    )

    assert len(provider.messages) == 1
    assert "Memórias salvas:" in provider.messages[0]
    assert "- gosto de python" in provider.messages[0]
    assert "Você: Olá" in provider.messages[0]


def test_conversation_does_not_include_provider_error_in_next_context(tmp_path: Path) -> None:
    output: list[str] = []
    provider = FailingThenWorkingProvider()

    run_conversation_loop(
        provider,
        input_reader=create_input_reader(["Olá", "Como vai", "sair"]),
        output_writer=output.append,
        memory_store=create_memory_store(tmp_path),
    )

    assert provider.messages == ["Olá", "Como vai"]
    assert "Aska > Modelo indisponível" in output
    assert "Aska > Resposta local" in output
