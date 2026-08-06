import json
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from packages.conversation.model import ModelMessage, ModelRole
from packages.conversation.provider import ModelProvider

_ROUTER_INSTRUCTION = "\n".join(
    (
        "Você roteia pedidos do usuário para um catálogo fechado de capabilities.",
        "Apenas proponha uma ação; não responda ao usuário, não execute nada, não "
        "acesse o computador e não conceda permissões.",
        "Entenda paráfrases naturalmente. Não dependa de uma frase exata dos exemplos.",
        "Capability disponível:",
        "- open_workspace_location: abre uma pasta relativa do workspace no Explorador "
        "de Arquivos. Use path='.' quando o pedido for apenas abrir o Explorador.",
        "Responda com exatamente um objeto JSON, sem Markdown ou texto adicional.",
        "Formatos permitidos:",
        '{"action":"open_workspace_location","path":"docs"}',
        '{"action":"none"}',
        "Use action='none' para perguntas, explicações, comentários ou pedidos que não "
        "correspondam claramente à capability disponível.",
        "Preserve no path o caminho solicitado, mesmo se parecer absoluto ou inseguro; "
        "a política local decidirá se ele é permitido.",
        "Não invente actions, caminhos ou mais de uma ação.",
    )
)


@dataclass(frozen=True, slots=True)
class OpenWorkspaceLocationProposal:
    path: str


CapabilityProposal = OpenWorkspaceLocationProposal


class ProposalRouteStatus(StrEnum):
    PROPOSAL = "proposal"
    NONE = "none"
    INVALID_RESPONSE = "invalid_response"


@dataclass(frozen=True, slots=True)
class ProposalRouteResult:
    status: ProposalRouteStatus
    proposal: CapabilityProposal | None = None

    def __post_init__(self) -> None:
        has_proposal = self.proposal is not None
        if (self.status is ProposalRouteStatus.PROPOSAL) != has_proposal:
            raise ValueError("only a successful route can expose a proposal")


class CapabilityProposalRouter(Protocol):
    def route(self, user_input: str) -> ProposalRouteResult: ...


class ModelCapabilityProposalRouter:
    def __init__(self, model_provider: ModelProvider) -> None:
        self._model_provider = model_provider

    def route(self, user_input: str) -> ProposalRouteResult:
        response = self._model_provider.generate(
            [
                ModelMessage(ModelRole.SYSTEM, _ROUTER_INSTRUCTION),
                ModelMessage(ModelRole.USER, user_input),
            ]
        )
        return _parse_route(response)


def _parse_route(response: str) -> ProposalRouteResult:
    try:
        data = json.loads(response)
    except (json.JSONDecodeError, TypeError):
        return ProposalRouteResult(ProposalRouteStatus.INVALID_RESPONSE)
    if data == {"action": "none"}:
        return ProposalRouteResult(ProposalRouteStatus.NONE)
    if not isinstance(data, dict) or set(data) != {"action", "path"}:
        return ProposalRouteResult(ProposalRouteStatus.INVALID_RESPONSE)
    if data.get("action") != "open_workspace_location":
        return ProposalRouteResult(ProposalRouteStatus.INVALID_RESPONSE)
    path = _validated_path(data.get("path"))
    if path is None:
        return ProposalRouteResult(ProposalRouteStatus.INVALID_RESPONSE)
    return ProposalRouteResult(
        ProposalRouteStatus.PROPOSAL,
        OpenWorkspaceLocationProposal(path),
    )


def _validated_path(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    if not normalized or any(marker in normalized for marker in ("\0", "\n", "\r")):
        return None
    return normalized
