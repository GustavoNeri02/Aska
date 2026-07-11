from collections.abc import Callable

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


def build_placeholder_response(message: str) -> str:
    del message
    return "Aska ainda não possui um modelo conectado."


def run_conversation_loop(
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

        response = build_placeholder_response(message)
        output_writer(f"Aska > {response}")


def main() -> None:
    run_conversation_loop()


if __name__ == "__main__":
    main()
