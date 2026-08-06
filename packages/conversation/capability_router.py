import json
from dataclasses import dataclass

CONVERSATION_DECISION_INSTRUCTION = "\n".join(
    (
        "Para este turno, responda com exatamente um objeto JSON, sem Markdown ou "
        "texto adicional.",
        "Escolha entre responder normalmente e propor uma capability do catálogo fechado.",
        "Formatos permitidos:",
        '{"type":"reply","content":"sua resposta ao usuário"}',
        '{"type":"capability_proposal","action":"open_workspace_location",'
        '"path":"docs"}',
        '{"type":"capability_proposal","action":"run_project_tests"}',
        "Capability disponível:",
        "- open_workspace_location: abre uma pasta relativa do workspace no Explorador "
        "de Arquivos. Use path='.' quando o pedido for apenas abrir o Explorador.",
        "- run_project_tests: executa a operação fixa python -m pytest -q na raiz do "
        "workspace e sempre roda a suíte inteira. Não aceita subconjunto, arquivo, nome "
        "de teste, comando, caminho, opção ou argumento do usuário.",
        "Entenda paráfrases usando o histórico e as memórias disponíveis.",
        "Escolha capability_proposal somente quando houver um pedido explícito para a "
        "ação acontecer agora. Mencionar uma capability ou perguntar sobre ela não é "
        "um pedido de execução.",
        "Em caso de dúvida entre conversar e agir, escolha reply.",
        "Uma capability_proposal é apenas uma sugestão: não execute, não conceda "
        "permissões e não afirme que a ação aconteceu.",
        "Preserve no path o caminho solicitado, mesmo se parecer inseguro; a política "
        "local fará a validação.",
        "Não invente actions ou mais de uma ação.",
        "Exemplos obrigatórios de distinção:",
        'Entrada: sabe o Explorer? Saída: {"type":"reply","content":"Sim, conheço o '
        'Explorador de Arquivos do Windows."}',
        'Entrada: o que é o Explorer? Saída: {"type":"reply","content":"É o '
        'gerenciador de arquivos do Windows."}',
        'Entrada: quais pastas o Explorer abre? Saída: {"type":"reply",'
        '"content":"Depende do caminho escolhido pelo usuário."}',
        'Entrada: abra o Explorer. Saída: {"type":"capability_proposal",'
        '"action":"open_workspace_location","path":"."}',
        'Entrada: rode os testes do projeto. Saída: {"type":"capability_proposal",'
        '"action":"run_project_tests"}',
        'Entrada: rode o primeiro teste do projeto. Saída: {"type":"reply",'
        '"content":"A capability atual só pode executar a suíte inteira."}',
        'Entrada: rode tests/test_app.py. Saída: {"type":"reply",'
        '"content":"A capability atual não aceita arquivo ou subconjunto de testes."}',
    )
)


@dataclass(frozen=True, slots=True)
class OpenWorkspaceLocationProposal:
    path: str


@dataclass(frozen=True, slots=True)
class RunProjectTestsProposal:
    pass


CapabilityProposal = OpenWorkspaceLocationProposal | RunProjectTestsProposal


@dataclass(frozen=True, slots=True)
class ReplyDecision:
    content: str


ConversationDecision = ReplyDecision | CapabilityProposal


class ConversationDecisionError(ValueError):
    """Raised when a model response is not a valid conversation decision."""


def _validated_path(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    if not normalized or any(marker in normalized for marker in ("\0", "\n", "\r")):
        return None
    return normalized


def parse_conversation_decision(response: str) -> ConversationDecision:
    try:
        data = json.loads(response)
    except (json.JSONDecodeError, TypeError) as error:
        raise ConversationDecisionError("invalid decision JSON") from error
    if not isinstance(data, dict):
        raise ConversationDecisionError("decision must be an object")
    if set(data) == {"type", "content"} and data.get("type") == "reply":
        content = _validated_reply(data.get("content"))
        if content is None:
            raise ConversationDecisionError("reply content must be valid text")
        return ReplyDecision(content)
    if set(data) == {"type", "action", "path"} and data.get(
        "type"
    ) == "capability_proposal":
        if data.get("action") != "open_workspace_location":
            raise ConversationDecisionError("unknown capability action")
        path = _validated_path(data.get("path"))
        if path is None:
            raise ConversationDecisionError("proposal path must be valid text")
        return OpenWorkspaceLocationProposal(path)
    if data == {
        "type": "capability_proposal",
        "action": "run_project_tests",
    }:
        return RunProjectTestsProposal()
    raise ConversationDecisionError("unknown conversation decision")


def _validated_reply(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    if not normalized or "\0" in normalized:
        return None
    return normalized
