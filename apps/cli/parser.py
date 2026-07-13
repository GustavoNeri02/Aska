from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ExitCommand: ...


@dataclass(frozen=True, slots=True)
class ListMemoriesCommand: ...


@dataclass(frozen=True, slots=True)
class RememberMemoryCommand:
    content: str


@dataclass(frozen=True, slots=True)
class ForgetMemoryCommand:
    content: str


@dataclass(frozen=True, slots=True)
class EditMemoryCommand:
    current_content: str
    new_content: str
    is_malformed: bool = False


@dataclass(frozen=True, slots=True)
class SearchMemoryCommand:
    term: str


@dataclass(frozen=True, slots=True)
class ChatMessage:
    content: str


ParsedInput = (
    ExitCommand
    | ListMemoriesCommand
    | RememberMemoryCommand
    | ForgetMemoryCommand
    | EditMemoryCommand
    | SearchMemoryCommand
    | ChatMessage
)

EXIT_COMMANDS = frozenset({"sair", "exit", "quit"})


def parse_input(user_input: str) -> ParsedInput:
    normalized_message = user_input.casefold()
    if normalized_message in EXIT_COMMANDS:
        return ExitCommand()
    if normalized_message == "memórias":
        return ListMemoriesCommand()
    if normalized_message.startswith("lembrar:"):
        return RememberMemoryCommand(user_input.split(":", 1)[1].strip())
    if normalized_message.startswith("esquecer:"):
        return ForgetMemoryCommand(user_input.split(":", 1)[1].strip())
    if normalized_message.startswith("editar memória:"):
        edit_expression = user_input.split(":", 1)[1].strip()
        if "->" not in edit_expression:
            return EditMemoryCommand("", "", is_malformed=True)
        current_content, new_content = (part.strip() for part in edit_expression.split("->", 1))
        return EditMemoryCommand(current_content, new_content)
    if normalized_message.startswith("buscar memória:"):
        return SearchMemoryCommand(user_input.split(":", 1)[1].strip())
    return ChatMessage(user_input)
