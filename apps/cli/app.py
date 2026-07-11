import os
from collections.abc import Callable

from packages.models import ModelProvider, ModelProviderError, OllamaProvider

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


def run_conversation_loop(
    provider: ModelProvider,
    input_reader: Callable[[str], str] = input,
    output_writer: Callable[[str], None] = print,
) -> None:
    output_writer(build_banner())
    output_writer("")
    output_writer("Olá, Gustavo.")
    output_writer("")
    output_writer("Digite 'sair' para encerrar.")
    output_writer("")

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

        try:
            response = provider.generate(message)
        except ModelProviderError as error:
            output_writer(f"Aska > {error}")
            continue

        output_writer(f"Aska > {response}")


def main() -> None:
    provider = OllamaProvider(
        model=os.getenv("ASKA_MODEL", "gemma3:12b"),
        base_url=os.getenv("ASKA_OLLAMA_URL", "http://localhost:11434"),
    )
    run_conversation_loop(provider)


if __name__ == "__main__":
    main()
