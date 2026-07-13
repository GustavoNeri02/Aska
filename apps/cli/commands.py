from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ExitCommand:
    pass


@dataclass(frozen=True, slots=True)
class InvalidCommand:
    usage: str


@dataclass(frozen=True, slots=True)
class ChatMessage:
    content: str


@dataclass(frozen=True, slots=True)
class ListMemoriesCommand:
    pass


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


@dataclass(frozen=True, slots=True)
class SearchMemoryCommand:
    term: str


MemoryCommand = (
    ListMemoriesCommand
    | RememberMemoryCommand
    | ForgetMemoryCommand
    | EditMemoryCommand
    | SearchMemoryCommand
)

ParsedInput = ExitCommand | InvalidCommand | MemoryCommand | ChatMessage
