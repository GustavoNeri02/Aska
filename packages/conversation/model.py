from dataclasses import dataclass
from enum import StrEnum


class ModelRole(StrEnum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


@dataclass(frozen=True, slots=True)
class ModelMessage:
    role: ModelRole
    content: str

    def __post_init__(self) -> None:
        if not isinstance(self.role, ModelRole):
            raise TypeError("role must be a ModelRole")
        if not self.content.strip():
            raise ValueError("message content cannot be empty")


@dataclass(frozen=True, slots=True)
class ConversationTurn:
    user_message: str
    assistant_message: str
