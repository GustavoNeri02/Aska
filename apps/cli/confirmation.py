import re
import unicodedata
from enum import StrEnum


class ConfirmationDecision(StrEnum):
    CONFIRM = "confirm"
    CANCEL = "cancel"
    UNKNOWN = "unknown"


def parse_confirmation(user_input: str) -> ConfirmationDecision:
    normalized_input = _normalize(user_input)
    if normalized_input in {"sim", "confirmar", "confirmo"}:
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
