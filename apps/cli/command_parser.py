from apps.cli.commands import (
    ChatMessage,
    EditMemoryCommand,
    ExitCommand,
    ForgetMemoryCommand,
    InvalidCommand,
    ListMemoriesCommand,
    ParsedInput,
    RememberMemoryCommand,
    SearchMemoryCommand,
)

EXIT_COMMANDS = frozenset({"sair", "exit", "quit"})


def parse_input(user_input: str) -> ParsedInput:
    normalized_message = user_input.casefold()
    if normalized_message in EXIT_COMMANDS:
        return ExitCommand()
    if normalized_message == "memórias":
        return ListMemoriesCommand()
    if normalized_message.startswith("lembrar:"):
        argument = _command_argument(user_input)
        if not argument:
            return InvalidCommand("Use: lembrar: <conteúdo>")
        return RememberMemoryCommand(argument)
    if normalized_message.startswith("esquecer:"):
        argument = _command_argument(user_input)
        if not argument:
            return InvalidCommand("Use: esquecer: <conteúdo>")
        return ForgetMemoryCommand(argument)
    if normalized_message.startswith("editar memória:"):
        edit_expression = _command_argument(user_input)
        if "->" not in edit_expression:
            return InvalidCommand("Use: editar memória: <atual> -> <novo>")
        current_content, new_content = (part.strip() for part in edit_expression.split("->", 1))
        if not current_content or not new_content:
            return InvalidCommand("Informe a memória atual e o novo conteúdo.")
        return EditMemoryCommand(current_content, new_content)
    if normalized_message.startswith("buscar memória:"):
        term = _command_argument(user_input)
        if not term:
            return InvalidCommand("Use: buscar memória: <termo>")
        return SearchMemoryCommand(term)
    return ChatMessage(user_input)


def _command_argument(user_input: str) -> str:
    _, _, argument = user_input.partition(":")
    return argument.strip()
