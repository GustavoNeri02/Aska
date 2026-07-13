from typing import Protocol

from packages.conversation.context import ContextBuilder
from packages.conversation.model import ConversationTurn
from packages.conversation.provider import ModelProvider
from packages.memory.domain.model import Memory


class MemoryReader(Protocol):
    def list(self) -> list[Memory]: ...


class ConversationService:
    def __init__(
        self,
        model_provider: ModelProvider,
        memory_reader: MemoryReader,
        context_builder: ContextBuilder | None = None,
    ) -> None:
        self._model_provider = model_provider
        self._memory_reader = memory_reader
        self._context_builder = context_builder or ContextBuilder()
        self._history: list[ConversationTurn] = []

    @property
    def history(self) -> list[ConversationTurn]:
        return list(self._history)

    def send(self, user_message: str) -> str:
        prompt = self._context_builder.build(
            history=self._history,
            user_message=user_message,
            memories=self._memory_reader.list(),
        )
        response = self._model_provider.generate(prompt)
        self._history.append(ConversationTurn(user_message, response))
        return response
