from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ConversationTurn:
    user_message: str
    assistant_message: str
