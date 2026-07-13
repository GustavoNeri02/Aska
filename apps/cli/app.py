import os
from collections.abc import Callable
from contextlib import suppress

from apps.cli.command_parser import parse_input
from apps.cli.commands import ChatMessage, ExitCommand, InvalidCommand, MemoryCommand
from apps.cli.handlers import (
    handle_memory_command,
    present_memory_edit_proposal,
    present_memory_edit_result,
)
from apps.cli.loading import run_with_loading
from packages.conversation import (
    ConversationService,
    ModelProvider,
    ModelProviderError,
    PendingMemoryEdit,
    detect_name_change,
    find_name_memory_candidates,
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
    pending_memory_edit: PendingMemoryEdit | None = None

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
                if pending_memory_edit is not None:
                    pending_memory_edit = None
                    output_writer("Proposta de edição anterior cancelada.")
                handle_memory_command(parsed_input, memory_service, output_writer)
            elif isinstance(parsed_input, ChatMessage):
                normalized_input = parsed_input.content.casefold()
                if pending_memory_edit is not None:
                    if normalized_input in {"sim", "confirmar", "confirmo"}:
                        confirmed_edit = pending_memory_edit
                        pending_memory_edit = None
                        status = memory_service.edit_by_id(
                            confirmed_edit.memory_id,
                            confirmed_edit.expected_content,
                            confirmed_edit.new_content,
                        )
                        present_memory_edit_result(status, output_writer)
                    elif normalized_input in {"não", "nao", "cancelar", "cancela"}:
                        pending_memory_edit = None
                        output_writer("Edição de memória cancelada.")
                    else:
                        output_writer(
                            "Confirmação não reconhecida. Digite 'sim' para confirmar "
                            "ou 'não' para cancelar."
                        )
                    continue

                new_content = detect_name_change(parsed_input.content)
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
                        pending_memory_edit = PendingMemoryEdit(
                            memory_id=candidate.id,
                            expected_content=candidate.content,
                            new_content=new_content,
                        )
                        present_memory_edit_proposal(pending_memory_edit, output_writer)
                    continue

                response = conversation_service.send(parsed_input.content)
                output_writer(f"Aska > {response}")
        except MemoryRepositoryError as error:
            output_writer(f"Não foi possível acessar as memórias: {error}")
        except ModelProviderError as error:
            output_writer(f"Aska > {error}")


def main() -> None:
    model = os.getenv("ASKA_MODEL", "gemma3:12b")
    model_provider = OllamaProvider(
        model=model,
        base_url=os.getenv("ASKA_OLLAMA_URL", "http://localhost:11434"),
    )
    memory_data_source = JsonMemoryDataSource("data/memory/memories.json")
    memory_repository = LocalMemoryRepository(memory_data_source)
    memory_service = MemoryService(memory_repository)

    try:
        try:
            run_with_loading(model_provider.warm_up, f"Carregando {model}...")
        except ModelProviderError as error:
            print(f"Aska > {error}")
            return
        run_conversation_loop(model_provider, memory_service=memory_service)
    finally:
        with suppress(ModelProviderError):
            model_provider.unload()


if __name__ == "__main__":
    main()
