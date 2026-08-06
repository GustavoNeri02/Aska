import pytest

from apps.cli.confirmation import (
    ConfirmationDecision,
    ModelConfirmationInterpreter,
    parse_confirmation,
)
from tests.cli_support import FakeProvider


@pytest.mark.parametrize(
    "value",
    [
        "sim",
        "confirmar",
        "confirmo",
        " SIM ",
        "siiiim",
        "simm",
        "confirmooo",
        "y",
        "yes",
        "yep",
        "yeah",
        "YEAH!",
    ],
)
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


@pytest.mark.parametrize(
    ("response", "expected"),
    [
        ('{"decision":"confirm"}', ConfirmationDecision.CONFIRM),
        ('{"decision":"cancel"}', ConfirmationDecision.CANCEL),
        ('{"decision":"unknown"}', ConfirmationDecision.UNKNOWN),
        ("resposta livre", ConfirmationDecision.UNKNOWN),
        ('{"decision":"confirm","extra":true}', ConfirmationDecision.UNKNOWN),
    ],
)
def test_model_confirmation_interpreter_uses_strict_decision_envelope(
    response: str,
    expected: ConfirmationDecision,
) -> None:
    provider = FakeProvider(response)
    interpreter = ModelConfirmationInterpreter(provider)

    decision = interpreter.interpret("yep", "abrir a pasta proposta")

    assert decision is expected
    assert provider.messages[0][-1].content == "yep"
    assert "abrir a pasta proposta" in provider.messages[0][0].content
