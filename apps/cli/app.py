import os
from collections.abc import Callable

from packages.models import ModelProvider, ModelProviderError, OllamaProvider
from packages.runtime.memory import MemoryStore, ReplaceResult

EXIT_COMMANDS = frozenset(
    {
        "sair",
        "exit",
        "quit",
    }
)


def build_banner() -> str:
    return (
        "╔══════════════════════════════════════╗\n"
        "║                 Aska                 ║\n"
        "║          Personal Local AI           ║\n"
        "╚══════════════════════════════════════╝"
    )


def _build_context_message(
    history: list[tuple[str, str]],
    message: str,
    memories: list[str] | None = None,
) -> str:
    lines: list[str] = []

    if memories:
        lines.append("Memórias salvas:")
        for memory in memories:
            lines.append(f"- {memory}")
        lines.append("")

    if history:
        lines.append("Histórico da sessão:")
        for user_message, assistant_message in history:
            lines.append(f"Você: {user_message}")
            lines.append(f"Aska: {assistant_message}")
        lines.append("")

    if lines:
        lines.append(f"Você: {message}")
        return "\n".join(lines)

    return message


def run_conversation_loop(
    provider: ModelProvider,
    memory_store: MemoryStore,
    input_reader: Callable[[str], str] = input,
    output_writer: Callable[[str], None] = print,
) -> None:
    output_writer(build_banner())
    output_writer("")
    output_writer("Olá, Gustavo.")
    output_writer("")
    output_writer("Digite 'sair' para encerrar.")
    output_writer("")

    session_history: list[tuple[str, str]] = []

    while True:
        try:
            message = input_reader("Você > ").strip()
        except (EOFError, KeyboardInterrupt):
            output_writer("\nEncerrando o Aska.")
            return

        if not message:
            continue

        if message.casefold() in EXIT_COMMANDS:
            output_writer("Até mais, Gustavo.")
            return

        if message.casefold() == "memórias":
            memories = memory_store.list()
            output_writer("Memórias locais:")
            if memories:
                for memory in memories:
                    output_writer(memory)
            else:
                output_writer("(nenhuma memória registrada)")
            continue

        if message.casefold().startswith("lembrar:"):
            memory = message.split(":", 1)[1].strip()
            if memory:
                memory_store.add(memory)
                output_writer("Memória registrada localmente.")
            continue

        if message.casefold().startswith("esquecer:"):
            memory = message.split(":", 1)[1].strip()
            if memory:
                removed = memory_store.remove(memory)
                if removed:
                    output_writer("Memória removida localmente.")
                else:
                    output_writer("Nenhuma memória correspondente foi encontrada.")
            continue

        if message.casefold().startswith("editar memória:"):
            command = message.split(":", 1)[1].strip()
            if "->" not in command:
                output_writer("Use: editar memória: <atual> -> <novo>")
                continue

            current_memory, new_memory = (part.strip() for part in command.split("->", 1))
            result = memory_store.replace(current_memory, new_memory)
            if result is ReplaceResult.REPLACED:
                output_writer("Memória editada localmente.")
            elif result is ReplaceResult.NOT_FOUND:
                output_writer("Nenhuma memória correspondente foi encontrada.")
            elif result is ReplaceResult.DUPLICATE:
                output_writer("Já existe uma memória com esse conteúdo.")
            elif result is ReplaceResult.INVALID:
                output_writer("Informe a memória atual e o novo conteúdo.")
            elif result is ReplaceResult.UNCHANGED:
                output_writer("A memória já possui esse conteúdo.")
            continue

        context_message = _build_context_message(session_history, message, memory_store.list())

        try:
            response = provider.generate(context_message)
        except ModelProviderError as error:
            output_writer(f"Aska > {error}")
            continue

        session_history.append((message, response))
        output_writer(f"Aska > {response}")


def main() -> None:
    provider = OllamaProvider(
        model=os.getenv("ASKA_MODEL", "gemma3:12b"),
        base_url=os.getenv("ASKA_OLLAMA_URL", "http://localhost:11434"),
    )
    run_conversation_loop(provider, memory_store=MemoryStore(path="data/memory/memories.json"))


if __name__ == "__main__":
    main()
