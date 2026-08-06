import pytest

from apps.cli.confirmation import ConfirmationDecision, parse_confirmation


@pytest.mark.parametrize("value", ["sim", "confirmar", "confirmo", " SIM "])
def test_parse_confirmation_accepts_confirmation_variants(value: str) -> None:
    assert parse_confirmation(value) is ConfirmationDecision.CONFIRM


@pytest.mark.parametrize(
    "value",
    [
        "não",
        "nao",
        "naum",
        "n",
        "no",
        "nop",
        "negativo",
        "não quero",
        "pode cancelar",
        "de jeito nenhum",
        "cancelar",
        "cancela",
        " NÃO ",
    ],
)
def test_parse_confirmation_accepts_cancellation_variants(value: str) -> None:
    assert parse_confirmation(value) is ConfirmationDecision.CANCEL


@pytest.mark.parametrize("value", ["pode ser", "talvez", "acho que não", "ok"])
def test_parse_confirmation_rejects_ambiguous_response(value: str) -> None:
    assert parse_confirmation(value) is ConfirmationDecision.UNKNOWN
