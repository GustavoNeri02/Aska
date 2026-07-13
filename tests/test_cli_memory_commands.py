from pathlib import Path

import pytest

from apps.cli.app import run_conversation_loop
from tests.cli_support import (
    FakeProvider,
    create_input_reader,
    create_memory_service,
    create_temp_memory_service,
)


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
    assert [memory.content for memory in create_memory_service(path=path).list()] == [
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
    system_content = provider.messages[0][0].content
    assert "Memórias sobre Gustavo:" in system_content
    assert "- gosto de dart" in system_content
    assert "gosto de python" not in system_content


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
    assert "Memórias sobre Gustavo:" not in provider.messages[0][0].content
    assert not any("gosto de python" in message.content for message in provider.messages[0])
    assert provider.messages[0][-1].content == "Olá"


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
    system_content = provider.messages[0][0].content
    assert "Memórias sobre Gustavo:" in system_content
    assert "- gosto de python" in system_content
    assert provider.messages[0][-1].content == "Olá"
    assert memory.id not in system_content
    assert memory.source.value not in system_content
    assert memory.created_at.isoformat() not in system_content
