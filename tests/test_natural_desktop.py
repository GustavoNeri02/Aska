import pytest

from packages.conversation import (
    OpenWorkspaceLocationProposal,
    detect_explicit_open_location,
)


@pytest.mark.parametrize(
    ("message", "path"),
    [
        ("Abra a pasta docs no Explorador.", "docs"),
        ("Abra o diretório docs/project no Explorer", "docs/project"),
        ("Abra o Explorador.", "."),
        ("abra o explorer", "."),
        ("abre o programa explorer", "."),
        ("abra o programa Explorador de Arquivos", "."),
        ("abra o explorer em docs", "docs"),
        ("abra o explorer em c:/", "c:/"),
    ],
)
def test_explicit_open_location_is_detected_deterministically(
    message: str,
    path: str,
) -> None:
    assert detect_explicit_open_location(message) == OpenWorkspaceLocationProposal(path)


@pytest.mark.parametrize(
    "message",
    [
        "Abra sua mente.",
        "Onde fica a pasta docs?",
        "Explique o Windows Explorer.",
        "O Explorer está aberto?",
        "Gosto do Explorador de Arquivos.",
        "Abra README.md.",
    ],
)
def test_non_exact_open_location_is_left_for_capability_router(message: str) -> None:
    assert detect_explicit_open_location(message) is None
