from pathlib import Path

import pytest

from apps.cli.app import run_conversation_loop
from packages.conversation import (
    ModelMemoryIntentInterpreter,
    NameUpdateIntent,
)
from tests.cli_support import (
    FakeMemoryIntentInterpreter,
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


def test_natural_name_edit_proposes_without_changing_persistence(tmp_path: Path) -> None:
    output: list[str] = []
    interpreter = FakeMemoryIntentInterpreter(NameUpdateIntent("Nome não utilizado"))
    store = create_memory_service(path=tmp_path / "memories.json")
    original = store.add("Meu nome é Gustavo.").memory
    assert original is not None

    run_conversation_loop(
        FakeProvider(),
        input_reader=create_input_reader(["Meu nome agora é Gustavo Neri", "sair"]),
        output_writer=output.append,
        memory_service=store,
        memory_intent_interpreter=interpreter,
    )

    assert "Ação proposta: editar memória" in output
    assert "Conteúdo atual: Meu nome é Gustavo." in output
    assert "Novo conteúdo: Meu nome é Gustavo Neri." in output
    assert store.list() == [original]
    assert interpreter.inputs == []


def test_natural_name_edit_confirmation_executes_only_once(tmp_path: Path) -> None:
    output: list[str] = []
    provider = FakeProvider()
    store = create_memory_service(path=tmp_path / "memories.json")
    original = store.add("Meu nome é Gustavo.").memory
    assert original is not None

    run_conversation_loop(
        provider,
        input_reader=create_input_reader(
            ["Mude meu nome para Gustavo Neri", "confirmar", "confirmo", "sair"]
        ),
        output_writer=output.append,
        memory_service=store,
    )

    edited = store.list()[0]
    assert edited.content == "Meu nome é Gustavo Neri."
    assert edited.id == original.id
    assert output.count("Memória editada localmente.") == 1
    assert len(provider.messages) == 1
    assert provider.messages[0][-1].content == "confirmo"


@pytest.mark.parametrize("cancellation", ["não", "nao", "cancelar", "cancela"])
def test_natural_name_edit_cancellation_does_not_change_memory(
    cancellation: str,
    tmp_path: Path,
) -> None:
    output: list[str] = []
    store = create_memory_service(path=tmp_path / "memories.json")
    original = store.add("Meu nome é Gustavo.").memory
    assert original is not None

    run_conversation_loop(
        FakeProvider(),
        input_reader=create_input_reader(["Meu nome agora é Gustavo Neri", cancellation, "sair"]),
        output_writer=output.append,
        memory_service=store,
    )

    assert "Edição de memória cancelada." in output
    assert store.list() == [original]


def test_ambiguous_confirmation_does_not_execute_edit(tmp_path: Path) -> None:
    output: list[str] = []
    store = create_memory_service(path=tmp_path / "memories.json")
    original = store.add("Meu nome é Gustavo.").memory
    assert original is not None

    run_conversation_loop(
        FakeProvider(),
        input_reader=create_input_reader(["Meu nome agora é Gustavo Neri", "pode ser", "sair"]),
        output_writer=output.append,
        memory_service=store,
    )

    assert any("Confirmação não reconhecida" in message for message in output)
    assert store.list() == [original]


def test_literal_memory_command_cancels_pending_edit_before_execution(tmp_path: Path) -> None:
    output: list[str] = []
    provider = FakeProvider()
    interpreter = FakeMemoryIntentInterpreter(NameUpdateIntent("Gustavo Neri"))
    store = create_memory_service(path=tmp_path / "memories.json")
    store.add("Meu nome é Gustavo.")

    run_conversation_loop(
        provider,
        input_reader=create_input_reader(
            [
                "Pode atualizar meu nome para Gustavo Neri?",
                "editar memória: Meu nome é Gustavo. -> Meu nome é Gustavo Souza.",
                "sim",
                "sair",
            ]
        ),
        output_writer=output.append,
        memory_service=store,
        memory_intent_interpreter=interpreter,
    )

    assert "Proposta de edição anterior cancelada." in output
    assert store.list()[0].content == "Meu nome é Gustavo Souza."
    assert len(provider.messages) == 1
    assert provider.messages[0][-1].content == "sim"
    assert interpreter.inputs == ["Pode atualizar meu nome para Gustavo Neri?"]


def test_natural_name_edit_reports_missing_candidate_without_proposal(tmp_path: Path) -> None:
    output: list[str] = []
    provider = FakeProvider()
    store = create_memory_service(path=tmp_path / "memories.json")
    store.add("Gosto de Python.")

    run_conversation_loop(
        provider,
        input_reader=create_input_reader(["Meu nome agora é Gustavo Neri", "sair"]),
        output_writer=output.append,
        memory_service=store,
    )

    assert "Não encontrei uma memória de nome para atualizar." in output
    assert "Ação proposta: editar memória" not in output
    assert provider.messages == []


def test_natural_name_edit_reports_multiple_candidates_without_choosing(
    tmp_path: Path,
) -> None:
    output: list[str] = []
    store = create_memory_service(path=tmp_path / "memories.json")
    store.add("Meu nome é Gustavo.")
    store.add("Eu me chamo Gustavo Souza.")

    run_conversation_loop(
        FakeProvider(),
        input_reader=create_input_reader(["Meu nome agora é Gustavo Neri", "sair"]),
        output_writer=output.append,
        memory_service=store,
    )

    assert any("mais de uma memória de nome" in message for message in output)
    assert "Ação proposta: editar memória" not in output
    assert [memory.content for memory in store.list()] == [
        "Meu nome é Gustavo.",
        "Eu me chamo Gustavo Souza.",
    ]


def test_natural_name_edit_does_not_report_success_when_persistence_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output: list[str] = []
    store = create_memory_service(path=tmp_path / "memories.json")
    original = store.add("Meu nome é Gustavo.").memory
    assert original is not None

    def fail_replace(source: object, destination: object) -> None:
        del source, destination
        raise OSError("falha simulada")

    monkeypatch.setattr("packages.memory.data.json_data_source.os.replace", fail_replace)

    run_conversation_loop(
        FakeProvider(),
        input_reader=create_input_reader(["Meu nome agora é Gustavo Neri", "sim", "sair"]),
        output_writer=output.append,
        memory_service=store,
    )

    assert "Memória editada localmente." not in output
    assert any("Não foi possível acessar as memórias:" in message for message in output)
    assert store.list() == [original]


def test_interpreted_name_change_proposes_without_persisting(tmp_path: Path) -> None:
    output: list[str] = []
    interpreter = FakeMemoryIntentInterpreter(NameUpdateIntent("Gustavo Neri"))
    store = create_memory_service(path=tmp_path / "memories.json")
    original = store.add("Meu nome é Gustavo.").memory
    assert original is not None

    run_conversation_loop(
        FakeProvider(),
        memory_intent_interpreter=interpreter,
        input_reader=create_input_reader(
            ["Quero que você passe a me chamar de Gustavo Neri.", "sair"]
        ),
        output_writer=output.append,
        memory_service=store,
    )

    assert "Ação proposta: editar memória" in output
    assert "Novo conteúdo: Meu nome é Gustavo Neri." in output
    assert store.list() == [original]


def test_interpreted_name_change_confirmation_executes_only_once(tmp_path: Path) -> None:
    output: list[str] = []
    provider = FakeProvider()
    interpreter = FakeMemoryIntentInterpreter(NameUpdateIntent("Gustavo Neri"))
    store = create_memory_service(path=tmp_path / "memories.json")
    store.add("Meu nome é Gustavo.")

    run_conversation_loop(
        provider,
        memory_intent_interpreter=interpreter,
        input_reader=create_input_reader(
            ["Meu nome mudou para Gustavo Neri.", "sim", "confirmar", "sair"]
        ),
        output_writer=output.append,
        memory_service=store,
    )

    assert store.list()[0].content == "Meu nome é Gustavo Neri."
    assert output.count("Memória editada localmente.") == 1
    assert len(provider.messages) == 1
    assert provider.messages[0][-1].content == "confirmar"


def test_interpreted_name_change_cancellation_does_not_persist(tmp_path: Path) -> None:
    output: list[str] = []
    interpreter = FakeMemoryIntentInterpreter(NameUpdateIntent("Gustavo Neri"))
    store = create_memory_service(path=tmp_path / "memories.json")
    original = store.add("Meu nome é Gustavo.").memory
    assert original is not None

    run_conversation_loop(
        FakeProvider(),
        memory_intent_interpreter=interpreter,
        input_reader=create_input_reader(
            ["De agora em diante me chame de Gustavo Neri.", "cancelar", "sair"]
        ),
        output_writer=output.append,
        memory_service=store,
    )

    assert "Edição de memória cancelada." in output
    assert store.list() == [original]


def test_none_interpretation_falls_back_to_normal_conversation(tmp_path: Path) -> None:
    output: list[str] = []
    provider = FakeProvider()
    interpreter = FakeMemoryIntentInterpreter(None)
    store = create_memory_service(path=tmp_path / "memories.json")
    original = store.add("Meu nome é Gustavo.").memory
    assert original is not None

    message = "Pode atualizar meu nome talvez?"
    run_conversation_loop(
        provider,
        memory_intent_interpreter=interpreter,
        input_reader=create_input_reader([message, "sair"]),
        output_writer=output.append,
        memory_service=store,
    )

    assert "Ação proposta: editar memória" not in output
    assert "Aska > Resposta local" in output
    assert provider.messages[0][-1].content == message
    assert store.list() == [original]


@pytest.mark.parametrize(
    "response",
    [
        "not-json",
        '{"action":"delete_name","new_name":"Gustavo Neri"}',
        '{"action":"update_name","new_name":""}',
    ],
)
def test_invalid_model_interpretation_never_persists(
    response: str,
    tmp_path: Path,
) -> None:
    output: list[str] = []
    conversation_provider = FakeProvider()
    interpretation_provider = FakeProvider(response=response)
    interpreter = ModelMemoryIntentInterpreter(interpretation_provider)
    store = create_memory_service(path=tmp_path / "memories.json")
    original = store.add("Meu nome é Gustavo.").memory
    assert original is not None

    run_conversation_loop(
        conversation_provider,
        memory_intent_interpreter=interpreter,
        input_reader=create_input_reader(["Pode atualizar meu nome para Gustavo Neri?", "sair"]),
        output_writer=output.append,
        memory_service=store,
    )

    assert "Ação proposta: editar memória" not in output
    assert store.list() == [original]
    assert len(conversation_provider.messages) == 1


@pytest.mark.parametrize("candidate_count", [0, 2])
def test_interpreted_name_change_does_not_choose_invalid_candidate_count(
    candidate_count: int,
    tmp_path: Path,
) -> None:
    output: list[str] = []
    interpreter = FakeMemoryIntentInterpreter(NameUpdateIntent("Gustavo Neri"))
    store = create_memory_service(path=tmp_path / "memories.json")
    if candidate_count == 2:
        store.add("Meu nome é Gustavo.")
        store.add("Eu me chamo Gustavo Souza.")

    run_conversation_loop(
        FakeProvider(),
        memory_intent_interpreter=interpreter,
        input_reader=create_input_reader(["Pode atualizar meu nome para Gustavo Neri?", "sair"]),
        output_writer=output.append,
        memory_service=store,
    )

    assert "Ação proposta: editar memória" not in output
    assert len(store.list()) == candidate_count


def test_common_message_does_not_call_memory_interpreter(tmp_path: Path) -> None:
    provider = FakeProvider()
    interpreter = FakeMemoryIntentInterpreter(NameUpdateIntent("Não utilizado"))

    run_conversation_loop(
        provider,
        memory_intent_interpreter=interpreter,
        input_reader=create_input_reader(["Como vai?", "sair"]),
        output_writer=lambda message: None,
        memory_service=create_temp_memory_service(tmp_path),
    )

    assert interpreter.inputs == []
    assert len(provider.messages) == 1


def test_interpretation_does_not_enter_conversation_history(tmp_path: Path) -> None:
    provider = FakeProvider()
    interpreter = FakeMemoryIntentInterpreter(NameUpdateIntent("Gustavo Neri"))
    store = create_memory_service(path=tmp_path / "memories.json")
    store.add("Meu nome é Gustavo.")

    run_conversation_loop(
        provider,
        memory_intent_interpreter=interpreter,
        input_reader=create_input_reader(
            ["Meu nome mudou para Gustavo Neri.", "cancelar", "Olá", "sair"]
        ),
        output_writer=lambda message: None,
        memory_service=store,
    )

    assert len(provider.messages) == 1
    assert [message.content for message in provider.messages[0][1:]] == ["Olá"]
