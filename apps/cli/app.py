import os
from collections.abc import Callable
from contextlib import suppress

from apps.cli.command_parser import parse_input
from apps.cli.commands import ChatMessage, ExitCommand, InvalidCommand, MemoryCommand
from apps.cli.handlers import (
    handle_memory_command,
    present_memory_add_proposal,
    present_memory_add_result,
    present_memory_delete_proposal,
    present_memory_delete_result,
    present_memory_edit_proposal,
    present_memory_edit_result,
)
from apps.cli.loading import run_with_loading
from packages.conversation import (
    AddMemoryIntent,
    ConversationService,
    DeleteMemoryIntent,
    MemoryIntentInterpreter,
    ModelMemoryIntentInterpreter,
    ModelProvider,
    ModelProviderError,
    NameUpdateIntent,
    PendingMemoryAdd,
    PendingMemoryDelete,
    PendingMemoryEdit,
    canonical_name_memory,
    detect_memory_add,
    detect_memory_delete,
    detect_name_change,
    find_name_memory_candidates,
    should_interpret_memory_add,
    should_interpret_memory_delete,
    should_interpret_name_change,
)
from packages.inference import OllamaProvider
from packages.memory import (
    JsonMemoryDataSource,
    LocalMemoryRepository,
    MemoryRepositoryError,
    MemoryService,
)


def build_banner() -> str:
    return (
        "╔══════════════════════════════════════╗\n"
        "║                 Aska                 ║\n"
        "║          Personal Local AI           ║\n"
        "╚══════════════════════════════════════╝"
    )


def run_conversation_loop(
    model_provider: ModelProvider,
    memory_service: MemoryService,
    memory_intent_interpreter: MemoryIntentInterpreter | None = None,
    input_reader: Callable[[str], str] = input,
    output_writer: Callable[[str], None] = print,
) -> None:
    output_writer(build_banner())
    output_writer("")
    output_writer("Olá, Gustavo.")
    output_writer("")
    output_writer("Digite 'sair' para encerrar.")
    output_writer("")
    conversation_service = ConversationService(model_provider, memory_service)
    pending_memory_action: PendingMemoryAdd | PendingMemoryDelete | PendingMemoryEdit | None = None

    while True:
        try:
            user_input = input_reader("Você > ").strip()
        except (EOFError, KeyboardInterrupt):
            output_writer("\nEncerrando o Aska.")
            return

        if not user_input:
            continue

        parsed_input = parse_input(user_input)
        if isinstance(parsed_input, ExitCommand):
            output_writer("Até mais, Gustavo.")
            return
        if isinstance(parsed_input, InvalidCommand):
            output_writer(parsed_input.usage)
            continue

        try:
            if isinstance(parsed_input, MemoryCommand):
                if pending_memory_action is not None:
                    cancelled_action = pending_memory_action
                    pending_memory_action = None
                    if isinstance(cancelled_action, PendingMemoryEdit):
                        output_writer("Proposta de edição anterior cancelada.")
                    elif isinstance(cancelled_action, PendingMemoryDelete):
                        output_writer("Proposta de exclusão anterior cancelada.")
                    else:
                        output_writer("Proposta de inclusão anterior cancelada.")
                handle_memory_command(parsed_input, memory_service, output_writer)
            elif isinstance(parsed_input, ChatMessage):
                normalized_input = parsed_input.content.casefold()
                if pending_memory_action is not None:
                    if normalized_input in {"sim", "confirmar", "confirmo"}:
                        confirmed_action = pending_memory_action
                        pending_memory_action = None
                        if isinstance(confirmed_action, PendingMemoryEdit):
                            status = memory_service.edit_by_id(
                                confirmed_action.memory_id,
                                confirmed_action.expected_content,
                                confirmed_action.new_content,
                            )
                            present_memory_edit_result(status, output_writer)
                        elif isinstance(confirmed_action, PendingMemoryDelete):
                            status = memory_service.delete_by_id(
                                confirmed_action.memory_id,
                                confirmed_action.expected_content,
                            )
                            present_memory_delete_result(status, output_writer)
                        else:
                            result = memory_service.add(confirmed_action.content)
                            present_memory_add_result(result, output_writer)
                    elif normalized_input in {"não", "nao", "cancelar", "cancela"}:
                        cancelled_action = pending_memory_action
                        pending_memory_action = None
                        if isinstance(cancelled_action, PendingMemoryEdit):
                            output_writer("Edição de memória cancelada.")
                        elif isinstance(cancelled_action, PendingMemoryDelete):
                            output_writer("Exclusão de memória cancelada.")
                        else:
                            output_writer("Inclusão de memória cancelada.")
                    else:
                        output_writer(
                            "Confirmação não reconhecida. Digite 'sim' para confirmar "
                            "ou 'não' para cancelar."
                        )
                    continue

                new_content = detect_name_change(parsed_input.content)
                name_gate = should_interpret_name_change(parsed_input.content)
                delete_gate = should_interpret_memory_delete(parsed_input.content)
                add_gate = should_interpret_memory_add(parsed_input.content)
                deterministic_delete = detect_memory_delete(parsed_input.content)
                deterministic_add = detect_memory_add(parsed_input.content)
                if new_content is None and not name_gate and deterministic_delete is not None:
                    pending_memory_action = _propose_memory_delete(
                        deterministic_delete.query,
                        memory_service,
                        output_writer,
                    )
                    continue
                if (
                    new_content is None
                    and not name_gate
                    and not delete_gate
                    and deterministic_add is not None
                ):
                    pending_memory_action = PendingMemoryAdd(deterministic_add.content)
                    present_memory_add_proposal(pending_memory_action, output_writer)
                    continue
                if (
                    new_content is None
                    and memory_intent_interpreter is not None
                    and (name_gate or delete_gate or add_gate)
                ):
                    intent = memory_intent_interpreter.interpret(parsed_input.content)
                    if name_gate and isinstance(intent, NameUpdateIntent):
                        new_content = canonical_name_memory(intent.new_name)
                    elif not name_gate and delete_gate and isinstance(intent, DeleteMemoryIntent):
                        pending_memory_action = _propose_memory_delete(
                            intent.query,
                            memory_service,
                            output_writer,
                        )
                        continue
                    elif (
                        not name_gate
                        and not delete_gate
                        and add_gate
                        and isinstance(intent, AddMemoryIntent)
                    ):
                        pending_memory_action = PendingMemoryAdd(intent.content)
                        present_memory_add_proposal(pending_memory_action, output_writer)
                        continue
                if new_content is not None:
                    candidates = find_name_memory_candidates(memory_service.list())
                    if not candidates:
                        output_writer("Não encontrei uma memória de nome para atualizar.")
                    elif len(candidates) > 1:
                        output_writer(
                            "Encontrei mais de uma memória de nome. "
                            "Nenhuma foi escolhida automaticamente."
                        )
                    else:
                        candidate = candidates[0]
                        pending_memory_action = PendingMemoryEdit(
                            memory_id=candidate.id,
                            expected_content=candidate.content,
                            new_content=new_content,
                        )
                        present_memory_edit_proposal(pending_memory_action, output_writer)
                    continue

                response = conversation_service.send(parsed_input.content)
                output_writer(f"Aska > {response}")
        except MemoryRepositoryError as error:
            output_writer(f"Não foi possível acessar as memórias: {error}")
        except ModelProviderError as error:
            output_writer(f"Aska > {error}")


def _propose_memory_delete(
    query: str,
    memory_service: MemoryService,
    output_writer: Callable[[str], None],
) -> PendingMemoryDelete | None:
    exact_candidates = [
        memory for memory in memory_service.list() if memory.content.casefold() == query.casefold()
    ]
    candidates = exact_candidates or memory_service.search(query)
    if not candidates:
        output_writer("Nenhuma memória correspondente foi encontrada.")
        return None
    if len(candidates) > 1:
        output_writer(
            "Encontrei mais de uma memória correspondente. Nenhuma foi escolhida automaticamente."
        )
        return None

    candidate = candidates[0]
    pending_delete = PendingMemoryDelete(
        memory_id=candidate.id,
        expected_content=candidate.content,
    )
    present_memory_delete_proposal(pending_delete, output_writer)
    return pending_delete


def main() -> None:
    model = os.getenv("ASKA_MODEL", "gemma3:12b")
    model_provider = OllamaProvider(
        model=model,
        base_url=os.getenv("ASKA_OLLAMA_URL", "http://localhost:11434"),
    )
    memory_data_source = JsonMemoryDataSource("data/memory/memories.json")
    memory_repository = LocalMemoryRepository(memory_data_source)
    memory_service = MemoryService(memory_repository)
    memory_intent_interpreter = ModelMemoryIntentInterpreter(model_provider)

    try:
        try:
            run_with_loading(model_provider.warm_up, f"Carregando {model}...")
        except ModelProviderError as error:
            print(f"Aska > {error}")
            return
        run_conversation_loop(
            model_provider,
            memory_service=memory_service,
            memory_intent_interpreter=memory_intent_interpreter,
        )
    finally:
        with suppress(ModelProviderError):
            model_provider.unload()


if __name__ == "__main__":
    main()
