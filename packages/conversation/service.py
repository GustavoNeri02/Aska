import json
from typing import Protocol

from packages.conversation.capability_router import (
    CONVERSATION_DECISION_INSTRUCTION,
    CapabilityProposal,
    ConversationDecision,
    ConversationDecisionError,
    ReplyDecision,
    describe_capability_proposal,
    parse_conversation_decision,
)
from packages.conversation.context import ContextBuilder
from packages.conversation.external_event import (
    CONVERSATION_EVENT_RESPONSE_INSTRUCTION,
    ConversationEvent,
)
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
        self._pending_offer: CapabilityProposal | None = None

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
        decision_instruction = CONVERSATION_DECISION_INSTRUCTION
        if self._pending_offer is not None:
            offer = json.dumps(
                describe_capability_proposal(self._pending_offer),
                ensure_ascii=False,
            )
            decision_instruction = (
                f"{decision_instruction}\n\n"
                "Oferta tipada pendente do turno anterior: "
                f"{offer}. Interprete a nova mensagem em relação a essa oferta; somente "
                "produza a proposal se o usuário a aceitar ou solicitar."
            )
        messages = self._context_builder.build(
            history=self._history,
            user_message=user_message,
            memories=self._memory_reader.list(),
            additional_system_instruction=decision_instruction,
        )
        response = self._model_provider.generate(messages)
        decision = parse_conversation_decision(response)
        if isinstance(decision, ReplyDecision):
            self._history.append(ConversationTurn(user_message, decision.content))
            self._pending_offer = decision.offer
        else:
            self._pending_offer = None
        return decision

    def present_event(
        self,
        original_user_message: str,
        event: ConversationEvent,
    ) -> str:
        messages = self._context_builder.build(
            history=self._history,
            user_message=event.to_context_message(original_user_message),
            memories=self._memory_reader.list(),
            additional_system_instruction=CONVERSATION_EVENT_RESPONSE_INSTRUCTION,
        )
        response = self._model_provider.generate(messages)
        try:
            decision = parse_conversation_decision(response)
        except ConversationDecisionError:
            natural_response = response.strip()
            if not natural_response or "\0" in natural_response:
                raise
        else:
            if not isinstance(decision, ReplyDecision) or decision.offer is not None:
                raise ConversationDecisionError(
                    "conversation event response must be a plain reply"
                )
            natural_response = decision.content
        self._history.append(
            ConversationTurn(
                original_user_message.strip(),
                natural_response,
                event.to_context_message(original_user_message),
            )
        )
        self._pending_offer = None
        return natural_response
