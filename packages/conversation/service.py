from typing import Protocol

from packages.conversation.capability_router import (
    CONVERSATION_DECISION_INSTRUCTION,
    ConversationDecision,
    ReplyDecision,
    parse_conversation_decision,
)
from packages.conversation.context import ContextBuilder
from packages.conversation.model import ContextDocument, ConversationTurn
from packages.conversation.provider import ModelProvider
from packages.memory import Memory


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

    def send(
        self,
        user_message: str,
        context_document: ContextDocument | None = None,
    ) -> str:
        messages = self._context_builder.build(
            history=self._history,
            user_message=user_message,
            memories=self._memory_reader.list(),
            context_document=context_document,
        )
        response = self._model_provider.generate(messages)
        self._history.append(ConversationTurn(user_message, response))
        return response

    def decide(self, user_message: str) -> ConversationDecision:
        messages = self._context_builder.build(
            history=self._history,
            user_message=user_message,
            memories=self._memory_reader.list(),
            additional_system_instruction=CONVERSATION_DECISION_INSTRUCTION,
        )
        response = self._model_provider.generate(messages)
        decision = parse_conversation_decision(response)
        if isinstance(decision, ReplyDecision):
            self._history.append(ConversationTurn(user_message, decision.content))
        return decision
