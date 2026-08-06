import pytest

from packages.conversation import RunProjectLintProposal, detect_explicit_project_lint


@pytest.mark.parametrize(
    "message",
    ["rode o Ruff no projeto", "Execute Ruff check.", "rodar ruff"],
)
def test_explicit_lint_request_uses_fixed_proposal(message: str) -> None:
    assert detect_explicit_project_lint(message) == RunProjectLintProposal()


@pytest.mark.parametrize(
    "message",
    ["o que é Ruff?", "o Ruff passou?", "rode Ruff --fix", "analise este arquivo com Ruff"],
)
def test_lint_mentions_and_unsupported_options_are_not_fast_paths(message: str) -> None:
    assert detect_explicit_project_lint(message) is None
