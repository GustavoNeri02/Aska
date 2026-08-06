import json
import re
import unicodedata
from enum import StrEnum
from typing import Protocol

from packages.conversation import ModelMessage, ModelProvider, ModelRole


class ConfirmationDecision(StrEnum):
    CONFIRM = "confirm"
    CANCEL = "cancel"
    UNKNOWN = "unknown"


class ConfirmationInterpreter(Protocol):
    def interpret(
        self,
        user_input: str,
        pending_action: str,
    ) -> ConfirmationDecision: ...


class ModelConfirmationInterpreter:
    def __init__(self, model_provider: ModelProvider) -> None:
        self._model_provider = model_provider

    def interpret(
        self,
        user_input: str,
        pending_action: str,
    ) -> ConfirmationDecision:
        instruction = "\n".join(
            (
                "Classifique a resposta do usuário à confirmação pendente.",
                "Não converse, não execute e não altere a ação.",
                "Aceite linguagem natural, abreviações, erros e outros idiomas.",
                "Confirme somente quando a intenção afirmativa for clara; na dúvida, use unknown.",
                "Responda somente com um destes JSONs:",
                '{"decision":"confirm"}',
                '{"decision":"cancel"}',
                '{"decision":"unknown"}',
                f"Ação pendente: {pending_action}",
            )
        )
        response = self._model_provider.generate(
            [
                ModelMessage(ModelRole.SYSTEM, instruction),
                ModelMessage(ModelRole.USER, user_input),
            ]
        )
        try:
            data = json.loads(response)
        except (json.JSONDecodeError, TypeError):
            return ConfirmationDecision.UNKNOWN
        if not isinstance(data, dict) or set(data) != {"decision"}:
            return ConfirmationDecision.UNKNOWN
        try:
            return ConfirmationDecision(data["decision"])
        except (ValueError, TypeError):
            return ConfirmationDecision.UNKNOWN


def parse_confirmation(user_input: str) -> ConfirmationDecision:
    normalized_input = _normalize(user_input)
    expressive_input = re.sub(r"(.)\1+", r"\1", normalized_input)
    if expressive_input in {
        "sim",
        "confirmar",
        "confirmo",
        "y",
        "yes",
        "yep",
        "yeah",
    }:
        return ConfirmationDecision.CONFIRM
    cancellations = {
        "n",
        "nao",
        "naum",
        "no",
        "nop",
        "negativo",
        "cancelar",
        "cancela",
        "nao quero",
        "pode cancelar",
        "de jeito nenhum",
    }
    if normalized_input in cancellations:
        return ConfirmationDecision.CANCEL
    return ConfirmationDecision.UNKNOWN


def _normalize(value: str) -> str:
    without_accents = "".join(
        character
        for character in unicodedata.normalize("NFKD", value.casefold())
        if not unicodedata.combining(character)
    )
    without_punctuation = re.sub(r"[^a-z0-9\s]", " ", without_accents)
    return " ".join(without_punctuation.split())
