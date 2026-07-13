from collections.abc import Sequence

from packages.conversation.identity import ASKA_IDENTITY
from packages.conversation.model import ConversationTurn, ModelMessage, ModelRole
from packages.memory import Memory


class ContextBuilder:
    def build(
        self,
        history: Sequence[ConversationTurn],
        user_message: str,
        memories: Sequence[Memory],
    ) -> list[ModelMessage]:
        system_content = ASKA_IDENTITY

        if memories:
            memory_context = "\n".join(
                ["Memórias sobre Gustavo:", *(f"- {memory.content}" for memory in memories)]
            )
            system_content = f"{system_content}\n\n{memory_context}"

        messages = [ModelMessage(ModelRole.SYSTEM, system_content)]
        for turn in history:
            messages.append(ModelMessage(ModelRole.USER, turn.user_message))
            messages.append(ModelMessage(ModelRole.ASSISTANT, turn.assistant_message))

        messages.append(ModelMessage(ModelRole.USER, user_message))
        return messages
