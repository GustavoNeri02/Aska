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
from packages.conversation.memory_retrieval import (
    MemorySelection,
    TextMemoryRetriever,
    is_memory_usage_question,
)
from packages.conversation.model import ContextDocument, ConversationTurn
from packages.conversation.provider import ModelProvider
from packages.memory import Memory


class MemoryReader(Protocol):
    def list(self) -> list[Memory]: ...


class MemoryRetriever(Protocol):
    def retrieve(self, query: str) -> MemorySelection: ...


class ConversationService:
    def __init__(
        self,
        model_provider: ModelProvider,
        memory_reader: MemoryReader,
        context_builder: ContextBuilder | None = None,
        memory_retriever: MemoryRetriever | None = None,
    ) -> None:
        self._model_provider = model_provider
        self._memory_reader = memory_reader
        self._context_builder = context_builder or ContextBuilder()
        self._memory_retriever = memory_retriever or TextMemoryRetriever(memory_reader)
        self._history: list[ConversationTurn] = []
        self._pending_offer: CapabilityProposal | None = None
        self._last_used_memories: tuple[Memory, ...] = ()

    @property
    def history(self) -> list[ConversationTurn]:
        return list(self._history)

    @property
    def last_used_memories(self) -> tuple[Memory, ...]:
        return self._last_used_memories

    def send(
        self,
        user_message: str,
        context_document: ContextDocument | None = None,
    ) -> str:
        memories = self._select_memories(user_message)
        messages = self._context_builder.build(
            history=self._history,
            user_message=user_message,
            memories=memories,
            context_document=context_document,
        )
        response = self._model_provider.generate(messages)
        self._history.append(ConversationTurn(user_message, response))
        self._last_used_memories = memories
        return response

    def decide(self, user_message: str) -> ConversationDecision:
        memories = self._select_memories(user_message)
        decision_instruction = CONVERSATION_DECISION_INSTRUCTION
        pending_offer = self._pending_offer
        if pending_offer is not None:
            offer = json.dumps(
                describe_capability_proposal(pending_offer),
                ensure_ascii=False,
            )
            decision_instruction = (
                f"{decision_instruction}\n\n"
                "Oferta tipada pendente do turno anterior: "
                f"{offer}. Interprete a nova mensagem em relação a essa oferta; somente "
                "produza a proposal se o usuário a aceitar ou solicitar. Se recusar, "
                'responda como {"type":"reply","content":"resposta natural"} sem offer.'
            )
        messages = self._context_builder.build(
            history=self._history,
            user_message=user_message,
            memories=memories,
            additional_system_instruction=decision_instruction,
        )
        response = self._model_provider.generate(messages)
        try:
            decision = parse_conversation_decision(response)
        except ConversationDecisionError:
            plain_reply = _plain_decision_reply(response)
            if plain_reply is not None:
                decision = ReplyDecision(plain_reply)
            else:
                retry_messages = self._context_builder.build(
                    history=self._history,
                    user_message=user_message,
                    memories=memories,
                    additional_system_instruction=(
                        f"{decision_instruction}\n\nSua resposta anterior violou o contrato. "
                        "Tente uma única vez novamente e devolva somente um dos objetos JSON "
                        "permitidos, sem texto antes ou depois."
                    ),
                )
                decision = parse_conversation_decision(
                    self._model_provider.generate(retry_messages)
                )
        if isinstance(decision, ReplyDecision):
            self._history.append(ConversationTurn(user_message, decision.content))
            self._pending_offer = decision.offer
            self._last_used_memories = memories
        else:
            self._pending_offer = None
        return decision

    def present_event(
        self,
        user_message: str,
        event: ConversationEvent,
        original_request: str | None = None,
    ) -> str:
        event_request = original_request or user_message
        memories = self._select_memories(event_request)
        status = event.facts.get("status")
        requires_status_ack = (
            event.domain in {"project_tests", "project_lint"}
            and event.kind == "completed"
            and isinstance(status, str)
        )
        requires_event_ack = requires_status_ack or event.kind in {
            "confirmation_required",
            "memory_usage_report",
            "invalid_command",
        }
        event_instruction = CONVERSATION_EVENT_RESPONSE_INSTRUCTION
        if requires_event_ack:
            status_field = f'"acknowledged_status":"{status}",' if requires_status_ack else ""
            event_instruction = (
                f"{event_instruction}\nResponda exatamente como: "
                '{"type":"event_reply",'
                f'"acknowledged_domain":"{event.domain}",'
                f'"acknowledged_kind":"{event.kind}",'
                f'{status_field}"content":"sua apresentação natural"}}. '
                "Os campos acknowledged_* devem permanecer exatamente como fornecidos."
            )
            if event.kind == "confirmation_required":
                event_instruction = (
                    f"{event_instruction} O content deve pedir confirmação claramente e nunca "
                    "afirmar que a ação já aconteceu ou que o fato já foi salvo."
                )
            elif event.kind == "memory_usage_report":
                event_instruction = (
                    f"{event_instruction} Responda diretamente listando exatamente as memórias "
                    "do evento, ou diga que nenhuma foi usada."
                )
        messages = self._context_builder.build(
            history=self._history,
            user_message=event.to_context_message(event_request),
            memories=memories,
            additional_system_instruction=event_instruction,
        )
        response = self._model_provider.generate(messages)
        try:
            natural_response = _parse_event_response(
                response, event, requires_event_ack, requires_status_ack, status
            )
        except ConversationDecisionError:
            retry_messages = self._context_builder.build(
                history=self._history,
                user_message=event.to_context_message(event_request),
                memories=memories,
                additional_system_instruction=(
                    f"{event_instruction}\n\nSua resposta anterior violou o contrato de "
                    "apresentação. Tente uma única vez novamente. Apenas apresente o evento "
                    "recebido no envelope exigido; não responda ao pedido original como uma "
                    "nova decisão e não produza capability_proposal."
                ),
            )
            retry_response = self._model_provider.generate(retry_messages)
            natural_response = _parse_event_response(
                retry_response, event, requires_event_ack, requires_status_ack, status
            )
        self._history.append(
            ConversationTurn(
                user_message.strip(),
                natural_response,
                event.to_context_message(event_request),
            )
        )
        self._pending_offer = None
        self._last_used_memories = memories
        return natural_response

    def present_memory_usage(self, user_message: str) -> str:
        return self.present_event(
            user_message,
            ConversationEvent(
                "memory",
                "memory_usage_report",
                {"memories": tuple(memory.content for memory in self._last_used_memories)},
            ),
        )

    def _select_memories(self, user_message: str) -> tuple[Memory, ...]:
        if is_memory_usage_question(user_message):
            return self._last_used_memories
        recent_user_messages = [turn.user_message for turn in self._history[-2:]]
        retrieval_query = "\n".join([*recent_user_messages, user_message])
        return self._memory_retriever.retrieve(retrieval_query).memories


def _parse_event_response(
    response: str,
    event: ConversationEvent,
    requires_event_ack: bool,
    requires_status_ack: bool,
    status: object,
) -> str:
    if requires_event_ack:
        return _parse_acknowledged_event(response, event, status if requires_status_ack else None)
    return _parse_regular_event_response(response)


def _plain_decision_reply(response: str) -> str | None:
    normalized = response.strip()
    if not normalized or "\0" in normalized or "{" in normalized or "}" in normalized:
        return None
    return normalized


def _parse_regular_event_response(response: str) -> str:
    try:
        decision = parse_conversation_decision(response)
    except ConversationDecisionError:
        natural_response = _parse_event_response_with_optional_preamble(response)
    else:
        if not isinstance(decision, ReplyDecision) or decision.offer is not None:
            raise ConversationDecisionError("conversation event response must be a plain reply")
        natural_response = decision.content
    return natural_response


def _parse_acknowledged_event(
    response: str,
    event: ConversationEvent,
    expected_status: object | None,
) -> str:
    normalized = response.strip()
    object_start = normalized.find("{")
    if object_start < 0:
        raise ConversationDecisionError("executable result response must acknowledge status")
    try:
        payload = json.loads(normalized[object_start:])
    except (json.JSONDecodeError, TypeError) as error:
        raise ConversationDecisionError("invalid executable result response") from error
    expected_keys = {"type", "acknowledged_domain", "acknowledged_kind", "content"}
    if expected_status is not None:
        expected_keys.add("acknowledged_status")
    if not isinstance(payload, dict) or set(payload) != expected_keys:
        raise ConversationDecisionError("invalid executable result response contract")
    if (
        payload.get("type") != "event_reply"
        or payload.get("acknowledged_domain") != event.domain
        or payload.get("acknowledged_kind") != event.kind
        or (expected_status is not None and payload.get("acknowledged_status") != expected_status)
    ):
        raise ConversationDecisionError("executable result response changed authoritative status")
    content = payload.get("content")
    if not isinstance(content, str) or not content.strip() or "\0" in content:
        raise ConversationDecisionError("executable result response content must be valid")
    return content.strip()


def _parse_event_response_with_optional_preamble(response: str) -> str:
    normalized = response.strip()
    if not normalized or "\0" in normalized:
        raise ConversationDecisionError("conversation event response must be valid text")

    object_start = normalized.find("{")
    if object_start < 0:
        return normalized

    try:
        decision = parse_conversation_decision(normalized[object_start:])
    except ConversationDecisionError as error:
        raise ConversationDecisionError(
            "conversation event response contains an invalid envelope"
        ) from error
    if not isinstance(decision, ReplyDecision) or decision.offer is not None:
        raise ConversationDecisionError("conversation event response must be a plain reply")
    return decision.content
