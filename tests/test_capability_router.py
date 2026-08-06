from collections.abc import Sequence

import pytest

from packages.conversation import (
    ModelCapabilityProposalRouter,
    ModelMessage,
    OpenWorkspaceLocationProposal,
    ProposalRouteResult,
    ProposalRouteStatus,
)


class StaticProvider:
    def __init__(self, response: str) -> None:
        self.response = response
        self.requests: list[list[ModelMessage]] = []

    def generate(self, messages: Sequence[ModelMessage]) -> str:
        self.requests.append(list(messages))
        return self.response


def test_router_returns_typed_capability_proposal() -> None:
    provider = StaticProvider(
        '{"action":"open_workspace_location","path":"docs"}'
    )

    result = ModelCapabilityProposalRouter(provider).route(
        "Será que você consegue colocar a documentação numa janela para mim?"
    )

    assert result == ProposalRouteResult(
        ProposalRouteStatus.PROPOSAL,
        OpenWorkspaceLocationProposal("docs"),
    )
    instruction = provider.requests[0][0].content
    assert "catálogo fechado" in instruction
    assert "não execute nada" in instruction
    assert "Não dependa de uma frase exata" in instruction


def test_router_distinguishes_no_action_from_invalid_model_output() -> None:
    none_result = ModelCapabilityProposalRouter(
        StaticProvider('{"action":"none"}')
    ).route("Explique o Explorador de Arquivos")
    invalid_result = ModelCapabilityProposalRouter(StaticProvider("não sei")).route(
        "Abra alguma coisa"
    )

    assert none_result.status is ProposalRouteStatus.NONE
    assert invalid_result.status is ProposalRouteStatus.INVALID_RESPONSE


@pytest.mark.parametrize(
    "response",
    [
        '{"action":"open_workspace_location","path":""}',
        '{"action":"open_workspace_location"}',
        '{"action":"open_workspace_location","path":"docs","extra":true}',
        '{"action":"run_command","command":"dir"}',
        '```json\n{"action":"none"}\n```',
    ],
)
def test_router_rejects_invalid_or_unknown_actions(response: str) -> None:
    result = ModelCapabilityProposalRouter(StaticProvider(response)).route("pedido")

    assert result.status is ProposalRouteStatus.INVALID_RESPONSE
