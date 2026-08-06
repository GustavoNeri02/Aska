from pathlib import Path

from apps.cli.turn_output import TurnOutput
from packages.conversation import ConversationService
from tests.cli_support import FakeProvider, create_temp_memory_service


def test_local_handler_output_becomes_system_facts_and_one_aska_reply(
    tmp_path: Path,
) -> None:
    provider = FakeProvider(
        '{"type":"reply","content":"Não encontrei arquivos correspondentes."}'
    )
    output: list[str] = []
    turn_output = TurnOutput(
        ConversationService(provider, create_temp_memory_service(tmp_path)),
        output.append,
        conversational_events=True,
    )

    turn_output.write("Status: empty")
    turn_output.write("Matches: 0")
    turn_output.finish("Encontre o arquivo.", domain="filesystem")

    assert output == [
        "Sistema > Status: empty",
        "Sistema > Matches: 0",
        "Aska > Não encontrei arquivos correspondentes.",
    ]
    assert len(provider.messages) == 1


def test_existing_aska_reply_is_not_presented_twice(tmp_path: Path) -> None:
    provider = FakeProvider()
    output: list[str] = []
    turn_output = TurnOutput(
        ConversationService(provider, create_temp_memory_service(tmp_path)),
        output.append,
        conversational_events=True,
    )

    turn_output.write("Aska > Resposta já gerada")
    turn_output.finish("pedido", domain="conversation")

    assert output == ["Aska > Resposta já gerada"]
    assert provider.messages == []
