import re

from packages.conversation.capability_router import RunProjectLintProposal

_EXPLICIT_PROJECT_LINT = re.compile(
    r"^(?:por favor[,.]?\s+)?(?:rode|roda|rodar|execute|executa|executar)\s+"
    r"(?:o\s+)?ruff(?:\s+(?:check|no projeto|do projeto))?[.!?]?$",
    re.IGNORECASE,
)


def detect_explicit_project_lint(user_input: str) -> RunProjectLintProposal | None:
    message = user_input.strip()
    if not message or "\n" in message or "\r" in message:
        return None
    return RunProjectLintProposal() if _EXPLICIT_PROJECT_LINT.fullmatch(message) else None
