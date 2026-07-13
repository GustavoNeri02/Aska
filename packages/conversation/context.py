from packages.conversation.model import ConversationTurn
from packages.memory.domain.model import Memory


class ContextBuilder:
    def build(
        self,
        history: list[ConversationTurn],
        user_message: str,
        memories: list[Memory],
    ) -> str:
        lines: list[str] = []

        if memories:
            lines.append("Memórias salvas:")
            lines.extend(f"- {memory.content}" for memory in memories)
            lines.append("")

        if history:
            lines.append("Histórico da sessão:")
            for turn in history:
                lines.append(f"Você: {turn.user_message}")
                lines.append(f"Aska: {turn.assistant_message}")
            lines.append("")

        if not lines:
            return user_message

        lines.append(f"Você: {user_message}")
        return "\n".join(lines)
