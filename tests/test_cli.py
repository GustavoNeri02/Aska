from collections.abc import Callable, Iterator
from io import StringIO
from pathlib import Path

import pytest

from apps.cli.app import (
    build_banner,
    main,
    run_conversation_loop,
)
from apps.cli.loading import run_with_loading
from packages.conversation import ModelProviderError
from packages.memory import (
    EditMemoryStatus,
    JsonMemoryDataSource,
    LocalMemoryRepository,
    Memory,
    MemoryService,
)


def memory_contents(memories: list[Memory]) -> list[str]:
    return [memory.content for memory in memories]


def create_memory_service(path: str | Path) -> MemoryService:
    return MemoryService(LocalMemoryRepository(JsonMemoryDataSource(path)))


def create_temp_memory_service(tmp_path: Path) -> MemoryService:
    return create_memory_service(path=tmp_path / "memories.json")


class FakeProvider:
    def __init__(self, response: str = "Resposta local") -> None:
        self.response = response
        self.messages: list[str] = []

    def generate(self, prompt: str) -> str:
        self.messages.append(prompt)
        return self.response


class FailingProvider:
    def generate(self, prompt: str) -> str:
        del prompt
        raise ModelProviderError("Modelo indisponível")


class FailingThenWorkingProvider:
    def __init__(self, response: str = "Resposta local") -> None:
        self.response = response
        self.messages: list[str] = []
        self._should_fail = True

    def generate(self, prompt: str) -> str:
        self.messages.append(prompt)
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


def test_loading_displays_message_and_clears_line() -> None:
    output = StringIO()

    run_with_loading(lambda: None, "Carregando modelo...", stream=output)

    assert output.getvalue() == "| Carregando modelo...\r\033[K"


def test_main_stops_configured_ollama_model_on_exit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ASKA_MODEL", "custom-model")
    monkeypatch.setattr("apps.cli.app.OllamaProvider.warm_up", lambda self: None)
    monkeypatch.setattr("apps.cli.app.run_with_loading", lambda action, message: action())
    monkeypatch.setattr("apps.cli.app.run_conversation_loop", lambda *args, **kwargs: None)
    commands: list[tuple[list[str], bool]] = []

    monkeypatch.setattr(
        "apps.cli.app.subprocess.run",
        lambda command, check: commands.append((command, check)),
    )

    main()

    assert commands == [(["ollama", "stop", "custom-model"], False)]


def test_main_stops_ollama_model_when_conversation_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail(*args: object, **kwargs: object) -> None:
        raise RuntimeError("unexpected failure")

    commands: list[list[str]] = []
    monkeypatch.setattr("apps.cli.app.OllamaProvider.warm_up", lambda self: None)
    monkeypatch.setattr("apps.cli.app.run_with_loading", lambda action, message: action())
    monkeypatch.setattr("apps.cli.app.run_conversation_loop", fail)
    monkeypatch.setattr(
        "apps.cli.app.subprocess.run",
        lambda command, check: commands.append(command),
    )

    with pytest.raises(RuntimeError, match="unexpected failure"):
        main()

    assert commands == [["ollama", "stop", "gemma3:12b"]]


def test_main_reports_ollama_warm_up_error_and_does_not_start_conversation(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fail_warm_up(self: object) -> None:
        raise ModelProviderError("Modelo indisponível")

    conversation_started = False

    def start_conversation(*args: object, **kwargs: object) -> None:
        nonlocal conversation_started
        conversation_started = True

    monkeypatch.setattr("apps.cli.app.OllamaProvider.warm_up", fail_warm_up)
    monkeypatch.setattr("apps.cli.app.run_with_loading", lambda action, message: action())
    monkeypatch.setattr("apps.cli.app.run_conversation_loop", start_conversation)
    monkeypatch.setattr("apps.cli.app.subprocess.run", lambda command, check: None)

    main()

    assert "Aska > Modelo indisponível" in capsys.readouterr().out
    assert conversation_started is False


def test_conversation_sends_message_to_provider(tmp_path: Path) -> None:
    output: list[str] = []
    provider = FakeProvider()

    run_conversation_loop(
        provider,
        input_reader=create_input_reader(["Olá", "sair"]),
        output_writer=output.append,
        memory_service=create_temp_memory_service(tmp_path),
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
        memory_service=create_temp_memory_service(tmp_path),
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
        memory_service=create_temp_memory_service(tmp_path),
    )

    assert "Até mais, Gustavo." in output


def test_conversation_ignores_blank_messages(tmp_path: Path) -> None:
    output: list[str] = []

    run_conversation_loop(
        FakeProvider(),
        input_reader=create_input_reader(["", "   ", "Olá", "sair"]),
        output_writer=output.append,
        memory_service=create_temp_memory_service(tmp_path),
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
        memory_service=create_temp_memory_service(tmp_path),
    )

    assert "\nEncerrando o Aska." in output


def test_conversation_reports_provider_error_and_keeps_running(tmp_path: Path) -> None:
    output: list[str] = []

    run_conversation_loop(
        FailingProvider(),
        input_reader=create_input_reader(["Olá", "sair"]),
        output_writer=output.append,
        memory_service=create_temp_memory_service(tmp_path),
    )

    assert "Aska > Modelo indisponível" in output
    assert "Até mais, Gustavo." in output


def test_memory_service_persists_memories_to_disk(tmp_path: Path) -> None:
    store = create_memory_service(path=tmp_path / "memories.json")

    store.add("gosto de python")

    assert memory_contents(store.list()) == ["gosto de python"]
    assert (tmp_path / "memories.json").exists()


def test_memory_service_ignores_blank_entries(tmp_path: Path) -> None:
    store = create_memory_service(path=tmp_path / "memories.json")

    store.add("   ")

    assert memory_contents(store.list()) == []


def test_memory_service_does_not_store_duplicates(tmp_path: Path) -> None:
    store = create_memory_service(path=tmp_path / "memories.json")

    store.add("gosto de python")
    store.add("gosto de python")

    assert memory_contents(store.list()) == ["gosto de python"]


def test_memory_service_persists_between_instances(tmp_path: Path) -> None:
    path = tmp_path / "memories.json"
    first_store = create_memory_service(path=path)
    first_store.add("gosto de python")

    second_store = create_memory_service(path=path)

    assert memory_contents(second_store.list()) == ["gosto de python"]


def test_memory_service_deletes_existing_memory(tmp_path: Path) -> None:
    store = create_memory_service(path=tmp_path / "memories.json")

    store.add("gosto de python")
    deleted = store.delete("gosto de python")

    assert deleted is True
    assert memory_contents(store.list()) == []


def test_memory_service_reports_missing_memory_without_changes(tmp_path: Path) -> None:
    store = create_memory_service(path=tmp_path / "memories.json")

    store.add("gosto de python")
    deleted = store.delete("gosto de dart")

    assert deleted is False
    assert memory_contents(store.list()) == ["gosto de python"]


def test_memory_service_ignores_blank_delete_entries(tmp_path: Path) -> None:
    store = create_memory_service(path=tmp_path / "memories.json")

    store.add("gosto de python")
    deleted = store.delete("   ")

    assert deleted is False
    assert memory_contents(store.list()) == ["gosto de python"]


def test_memory_service_persists_deletion_between_instances(tmp_path: Path) -> None:
    path = tmp_path / "memories.json"
    first_store = create_memory_service(path=path)
    first_store.add("gosto de python")
    first_store.delete("gosto de python")

    second_store = create_memory_service(path=path)

    assert memory_contents(second_store.list()) == []


def test_memory_service_edits_existing_memory(tmp_path: Path) -> None:
    store = create_memory_service(path=tmp_path / "memories.json")

    store.add("gosto de python")
    status = store.edit("gosto de python", "gosto de dart")

    assert status is EditMemoryStatus.EDITED
    assert memory_contents(store.list()) == ["gosto de dart"]


def test_memory_service_reports_missing_memory_without_changes_on_edit(tmp_path: Path) -> None:
    store = create_memory_service(path=tmp_path / "memories.json")

    store.add("gosto de python")
    status = store.edit("gosto de rust", "gosto de dart")

    assert status is EditMemoryStatus.NOT_FOUND
    assert memory_contents(store.list()) == ["gosto de python"]


def test_memory_service_reports_invalid_values_on_edit(tmp_path: Path) -> None:
    store = create_memory_service(path=tmp_path / "memories.json")

    store.add("gosto de python")
    assert store.edit("   ", "gosto de dart") is EditMemoryStatus.INVALID
    assert store.edit("gosto de python", "   ") is EditMemoryStatus.INVALID
    assert memory_contents(store.list()) == ["gosto de python"]


def test_memory_service_rejects_edit_when_new_value_already_exists(
    tmp_path: Path,
) -> None:
    store = create_memory_service(path=tmp_path / "memories.json")

    store.add("gosto de python")
    store.add("gosto de dart")
    status = store.edit("gosto de python", "gosto de dart")

    assert status is EditMemoryStatus.DUPLICATE
    assert memory_contents(store.list()) == ["gosto de python", "gosto de dart"]


def test_memory_service_reports_unchanged_when_edit_has_same_value(tmp_path: Path) -> None:
    store = create_memory_service(path=tmp_path / "memories.json")

    store.add("gosto de python")
    status = store.edit("gosto de python", "gosto de python")

    assert status is EditMemoryStatus.UNCHANGED
    assert memory_contents(store.list()) == ["gosto de python"]


def test_memory_service_preserves_position_when_editing(tmp_path: Path) -> None:
    store = create_memory_service(path=tmp_path / "memories.json")

    store.add("gosto de python")
    store.add("gosto de dart")
    store.add("gosto de rust")
    store.edit("gosto de dart", "gosto de go")

    assert memory_contents(store.list()) == ["gosto de python", "gosto de go", "gosto de rust"]


def test_memory_service_persists_edit_between_instances(tmp_path: Path) -> None:
    path = tmp_path / "memories.json"
    first_store = create_memory_service(path=path)
    first_store.add("gosto de python")
    first_store.edit("gosto de python", "gosto de dart")

    second_store = create_memory_service(path=path)

    assert memory_contents(second_store.list()) == ["gosto de dart"]


def test_memory_service_searches_partial_and_case_insensitive(tmp_path: Path) -> None:
    store = create_memory_service(path=tmp_path / "memories.json")

    store.add("gosto de python")
    store.add("gosto de dart")
    store.add("aprender rust")

    assert memory_contents(store.search("PYTH")) == ["gosto de python"]
    assert memory_contents(store.search("gosto")) == ["gosto de python", "gosto de dart"]


def test_memory_service_searches_exact_matches_and_accented_text(tmp_path: Path) -> None:
    store = create_memory_service(path=tmp_path / "memories.json")

    store.add("gosto de python")
    store.add("gosto de dart")
    store.add("café da manhã")

    assert memory_contents(store.search("gosto de python")) == ["gosto de python"]
    assert memory_contents(store.search("CAFÉ")) == ["café da manhã"]


def test_memory_service_returns_empty_results_without_rewriting_file(tmp_path: Path) -> None:
    path = tmp_path / "memories.json"
    store = create_memory_service(path=path)

    store.add("gosto de python")
    before = path.read_text(encoding="utf-8")
    results = store.search("rust")

    assert results == []
    assert path.read_text(encoding="utf-8") == before


def test_memory_service_ignores_blank_search_terms(tmp_path: Path) -> None:
    store = create_memory_service(path=tmp_path / "memories.json")

    store.add("gosto de python")

    assert store.search("   ") == []


def test_conversation_handles_invalid_json_without_broken_flow(tmp_path: Path) -> None:
    output: list[str] = []
    path = tmp_path / "memories.json"
    path.write_text("{not valid json", encoding="utf-8")
    store = create_memory_service(path=path)

    run_conversation_loop(
        FakeProvider(),
        input_reader=create_input_reader(["memórias", "sair"]),
        output_writer=output.append,
        memory_service=store,
    )

    assert any("Não foi possível acessar as memórias:" in message for message in output)
    assert "Até mais, Gustavo." in output


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
        memory_service=create_temp_memory_service(tmp_path),
    )

    assert not (tmp_path / "data" / "memory" / "memories.json").exists()


def test_conversation_can_store_and_report_search_no_results(tmp_path: Path) -> None:
    output: list[str] = []
    store = create_memory_service(path=tmp_path / "memories.json")

    run_conversation_loop(
        FakeProvider(),
        input_reader=create_input_reader(
            ["lembrar: gosto de python", "buscar memória: rust", "sair"]
        ),
        output_writer=output.append,
        memory_service=store,
    )

    assert "Memória registrada localmente." in output
    assert "Nenhuma memória encontrada para o termo." in output


def test_conversation_can_remove_memories_and_list_current_state(tmp_path: Path) -> None:
    output: list[str] = []
    store = create_memory_service(path=tmp_path / "memories.json")

    run_conversation_loop(
        FakeProvider(),
        input_reader=create_input_reader(
            ["lembrar: gosto de python", "esquecer: gosto de python", "memórias", "sair"]
        ),
        output_writer=output.append,
        memory_service=store,
    )

    assert "Memória removida localmente." in output
    assert "(nenhuma memória registrada)" in output


def test_conversation_can_edit_memories_and_list_current_state(tmp_path: Path) -> None:
    output: list[str] = []
    store = create_memory_service(path=tmp_path / "memories.json")

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
        memory_service=store,
    )

    assert "Memória editada localmente." in output
    assert "gosto de dart" in output
    assert "gosto de python" not in output


def test_conversation_reports_missing_memory_when_edit_fails(tmp_path: Path) -> None:
    output: list[str] = []
    store = create_memory_service(path=tmp_path / "memories.json")

    run_conversation_loop(
        FakeProvider(),
        input_reader=create_input_reader(
            ["editar memória: gosto de rust -> gosto de dart", "sair"]
        ),
        output_writer=output.append,
        memory_service=store,
    )

    assert "Nenhuma memória correspondente foi encontrada." in output


def test_conversation_rejects_edit_when_new_value_already_exists(tmp_path: Path) -> None:
    path = tmp_path / "memories.json"
    store = create_memory_service(path=path)
    store.add("teste de edição")
    store.add("novo texto")
    output: list[str] = []

    run_conversation_loop(
        FakeProvider(),
        input_reader=create_input_reader(["editar memória: teste de edição -> novo texto", "sair"]),
        output_writer=output.append,
        memory_service=store,
    )

    assert "Já existe uma memória com esse conteúdo." in output
    assert memory_contents(create_memory_service(path=path).list()) == [
        "teste de edição",
        "novo texto",
    ]


def test_conversation_can_search_memories(tmp_path: Path) -> None:
    output: list[str] = []
    store = create_memory_service(path=tmp_path / "memories.json")

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
        memory_service=store,
    )

    assert "Resultados da busca:" in output
    assert "gosto de python" in output
    assert "gosto de dart" in output


def test_conversation_reports_missing_search_results(tmp_path: Path) -> None:
    output: list[str] = []
    store = create_memory_service(path=tmp_path / "memories.json")

    run_conversation_loop(
        FakeProvider(),
        input_reader=create_input_reader(
            ["lembrar: gosto de python", "buscar memória: rust", "sair"]
        ),
        output_writer=output.append,
        memory_service=store,
    )

    assert "Nenhuma memória encontrada para o termo." in output


def test_conversation_reports_guidance_for_empty_search_term(tmp_path: Path) -> None:
    output: list[str] = []
    store = create_memory_service(path=tmp_path / "memories.json")

    run_conversation_loop(
        FakeProvider(),
        input_reader=create_input_reader(["buscar memória:   ", "sair"]),
        output_writer=output.append,
        memory_service=store,
    )

    assert "Use: buscar memória: <termo>" in output


def test_conversation_reports_duplicate_and_invalid_edit_results(
    tmp_path: Path,
) -> None:
    output: list[str] = []
    store = create_memory_service(path=tmp_path / "memories.json")

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
        memory_service=store,
    )

    assert "Já existe uma memória com esse conteúdo." in output
    assert "Informe a memória atual e o novo conteúdo." in output


def test_conversation_reports_unchanged_edit_result(tmp_path: Path) -> None:
    output: list[str] = []
    store = create_memory_service(path=tmp_path / "memories.json")

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
        memory_service=store,
    )

    assert "A memória já possui esse conteúdo." in output


def test_conversation_reports_short_guidance_for_malformed_edit_command(tmp_path: Path) -> None:
    output: list[str] = []
    store = create_memory_service(path=tmp_path / "memories.json")

    run_conversation_loop(
        FakeProvider(),
        input_reader=create_input_reader(["editar memória: gosto de python", "sair"]),
        output_writer=output.append,
        memory_service=store,
    )

    assert "Use: editar memória: <atual> -> <novo>" in output


def test_conversation_updates_provider_context_after_edit(tmp_path: Path) -> None:
    provider = FakeProvider()
    store = create_memory_service(path=tmp_path / "memories.json")

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
        memory_service=store,
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
        memory_service=create_temp_memory_service(tmp_path),
    )

    assert not (tmp_path / "data" / "memory" / "memories.json").exists()


def test_conversation_reports_missing_memory_when_removal_fails(tmp_path: Path) -> None:
    output: list[str] = []
    store = create_memory_service(path=tmp_path / "memories.json")

    run_conversation_loop(
        FakeProvider(),
        input_reader=create_input_reader(["esquecer: gosto de rust", "sair"]),
        output_writer=output.append,
        memory_service=store,
    )

    assert "Nenhuma memória correspondente foi encontrada." in output


def test_conversation_does_not_include_removed_memory_in_model_context(tmp_path: Path) -> None:
    provider = FakeProvider()
    store = create_memory_service(path=tmp_path / "memories.json")

    run_conversation_loop(
        provider,
        input_reader=create_input_reader(
            ["lembrar: gosto de python", "esquecer: gosto de python", "Olá", "sair"]
        ),
        output_writer=lambda message: None,
        memory_service=store,
    )

    assert len(provider.messages) == 1
    assert "Memórias salvas:" not in provider.messages[0]
    assert "gosto de python" not in provider.messages[0]
    assert provider.messages[0] == "Olá"


def test_conversation_includes_saved_memories_in_model_context(tmp_path: Path) -> None:
    provider = FakeProvider()
    store = create_memory_service(path=tmp_path / "memories.json")
    memory = store.add("gosto de python").memory
    assert memory is not None

    run_conversation_loop(
        provider,
        input_reader=create_input_reader(["Olá", "sair"]),
        output_writer=lambda message: None,
        memory_service=store,
    )

    assert len(provider.messages) == 1
    assert "Memórias salvas:" in provider.messages[0]
    assert "- gosto de python" in provider.messages[0]
    assert "Você: Olá" in provider.messages[0]
    assert memory.id not in provider.messages[0]
    assert memory.source not in provider.messages[0]
    assert memory.created_at.isoformat() not in provider.messages[0]


def test_conversation_does_not_include_provider_error_in_next_context(tmp_path: Path) -> None:
    output: list[str] = []
    provider = FailingThenWorkingProvider()

    run_conversation_loop(
        provider,
        input_reader=create_input_reader(["Olá", "Como vai", "sair"]),
        output_writer=output.append,
        memory_service=create_temp_memory_service(tmp_path),
    )

    assert provider.messages == ["Olá", "Como vai"]
    assert "Aska > Modelo indisponível" in output
    assert "Aska > Resposta local" in output
