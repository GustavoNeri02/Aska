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
        try:
            decision = parse_conversation_decision(response)
        except ConversationDecisionError:
            retry_messages = self._context_builder.build(
                history=self._history,
                user_message=user_message,
                memories=self._memory_reader.list(),
                additional_system_instruction=(
                    f"{decision_instruction}\n\nSua resposta anterior violou o contrato. "
                    "Tente uma única vez novamente e devolva somente um dos objetos JSON "
                    "permitidos, sem texto antes ou depois."
                ),
            )
            decision = parse_conversation_decision(self._model_provider.generate(retry_messages))
        if isinstance(decision, ReplyDecision):
            self._history.append(ConversationTurn(user_message, decision.content))
            self._pending_offer = decision.offer
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
        status = event.facts.get("status")
        requires_status_ack = (
            event.domain in {"project_tests", "project_lint"}
            and event.kind == "completed"
            and isinstance(status, str)
        )
        event_instruction = CONVERSATION_EVENT_RESPONSE_INSTRUCTION
        if requires_status_ack:
            event_instruction = (
                f"{event_instruction}\nPara este resultado executável, responda exatamente como: "
                '{"type":"event_reply","acknowledged_status":"STATUS_EXATO",'
                '"content":"sua apresentação natural"}. '
                f'O acknowledged_status deve ser exatamente "{status}".'
            )
        messages = self._context_builder.build(
            history=self._history,
            user_message=event.to_context_message(event_request),
            memories=self._memory_reader.list(),
            additional_system_instruction=event_instruction,
        )
        response = self._model_provider.generate(messages)
        try:
            natural_response = _parse_event_response(response, requires_status_ack, status)
        except ConversationDecisionError:
            retry_messages = self._context_builder.build(
                history=self._history,
                user_message=event.to_context_message(event_request),
                memories=self._memory_reader.list(),
                additional_system_instruction=(
                    f"{event_instruction}\n\nSua resposta anterior violou o contrato de "
                    "apresentação. Tente uma única vez novamente. Apenas apresente o evento "
                    "recebido no envelope exigido; não responda ao pedido original como uma "
                    "nova decisão e não produza capability_proposal."
                ),
            )
            retry_response = self._model_provider.generate(retry_messages)
            natural_response = _parse_event_response(retry_response, requires_status_ack, status)
        self._history.append(
            ConversationTurn(
                user_message.strip(),
                natural_response,
                event.to_context_message(event_request),
            )
        )
        self._pending_offer = None
        return natural_response


def _parse_event_response(
    response: str,
    requires_status_ack: bool,
    status: object,
) -> str:
    if requires_status_ack:
        if not isinstance(status, str):
            raise ConversationDecisionError("executable event status must be text")
        return _parse_status_acknowledged_event(response, status)
    return _parse_regular_event_response(response)


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


def _parse_status_acknowledged_event(response: str, expected_status: str) -> str:
    normalized = response.strip()
    object_start = normalized.find("{")
    if object_start < 0:
        raise ConversationDecisionError("executable result response must acknowledge status")
    try:
        payload = json.loads(normalized[object_start:])
    except (json.JSONDecodeError, TypeError) as error:
        raise ConversationDecisionError("invalid executable result response") from error
    if not isinstance(payload, dict) or set(payload) != {
        "type",
        "acknowledged_status",
        "content",
    }:
        raise ConversationDecisionError("invalid executable result response contract")
    if (
        payload.get("type") != "event_reply"
        or payload.get("acknowledged_status") != expected_status
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
