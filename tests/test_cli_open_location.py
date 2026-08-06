from pathlib import Path

from apps.cli.app import run_conversation_loop
from apps.cli.handlers import NaturalOpenLocationHandler
from capabilities.desktop import OpenWorkspaceLocationCapability
from packages.conversation import (
    OpenWorkspaceLocationProposal,
    ProposalRouteResult,
    ProposalRouteStatus,
)
from tests.cli_support import FakeProvider, create_input_reader, create_temp_memory_service


class RecordingLauncher:
    def __init__(self) -> None:
        self.paths: list[Path] = []

    def open(self, path: Path) -> None:
        self.paths.append(path)


class StaticRouter:
    def __init__(self, result: ProposalRouteResult | None = None) -> None:
        self.result = result or ProposalRouteResult(ProposalRouteStatus.NONE)
        self.inputs: list[str] = []

    def route(self, user_input: str) -> ProposalRouteResult:
        self.inputs.append(user_input)
        return self.result


def _create_handler(
    workspace: Path,
    router: StaticRouter | None = None,
) -> tuple[NaturalOpenLocationHandler, RecordingLauncher, list[str]]:
    launcher = RecordingLauncher()
    output: list[str] = []
    handler = NaturalOpenLocationHandler(
        OpenWorkspaceLocationCapability(workspace.resolve(), launcher),
        router or StaticRouter(),
        output.append,
    )
    return handler, launcher, output


def test_open_location_requires_confirmation_before_launch(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    handler, launcher, output = _create_handler(tmp_path)

    assert handler.handle("Abra a pasta docs no Explorador.") is True
    assert launcher.paths == []
    assert str(docs.resolve()) in output[-1]

    assert handler.handle("sim") is True
    assert launcher.paths == [docs.resolve()]
    assert output[-1] == "Pasta aberta no Explorador de Arquivos."


def test_open_explorer_defaults_to_workspace_root(tmp_path: Path) -> None:
    handler, launcher, output = _create_handler(tmp_path)

    assert handler.handle("Abra o Explorador.") is True
    assert launcher.paths == []
    assert str(tmp_path.resolve()) in output[-1]

    handler.handle("sim")

    assert launcher.paths == [tmp_path.resolve()]


def test_open_explorer_program_phrase_defaults_to_workspace_root(
    tmp_path: Path,
) -> None:
    handler, launcher, _ = _create_handler(tmp_path)

    assert handler.handle("abre o programa explorer") is True
    handler.handle("sim")

    assert launcher.paths == [tmp_path.resolve()]


def test_open_location_can_be_cancelled(tmp_path: Path) -> None:
    (tmp_path / "docs").mkdir()
    handler, launcher, output = _create_handler(tmp_path)

    handler.handle("Abra a pasta docs no Explorador.")
    handler.handle("não")

    assert launcher.paths == []
    assert output[-1] == "Abertura cancelada."


def test_unknown_confirmation_keeps_proposal_pending(tmp_path: Path) -> None:
    (tmp_path / "docs").mkdir()
    handler, launcher, output = _create_handler(tmp_path)

    handler.handle("Abra a pasta docs no Explorador.")
    handler.handle("talvez")
    handler.handle("sim")

    assert "Confirmação não reconhecida" in output[-2]
    assert len(launcher.paths) == 1


def test_changed_target_is_not_launched_after_confirmation(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    handler, launcher, output = _create_handler(tmp_path)

    handler.handle("Abra a pasta docs no Explorador.")
    docs.rename(tmp_path / "old-docs")
    docs.mkdir()
    handler.handle("sim")

    assert launcher.paths == []
    assert "mudou após a proposta" in output[-1]


def test_outside_workspace_is_rejected_without_launch(tmp_path: Path) -> None:
    handler, launcher, output = _create_handler(tmp_path)

    assert handler.handle("Abra a pasta ../fora no Explorador.") is True

    assert launcher.paths == []
    assert output[-1].startswith("Acesso negado")


def test_absolute_explorer_target_is_rejected_locally(tmp_path: Path) -> None:
    router = StaticRouter()
    handler, launcher, output = _create_handler(tmp_path, router)

    assert handler.handle("abra o explorer em c:/") is True

    assert router.inputs == []
    assert launcher.paths == []
    assert output[-1].startswith("Acesso negado")


def test_clear_desktop_request_does_not_fall_through_when_interpretation_fails(
    tmp_path: Path,
) -> None:
    router = StaticRouter(ProposalRouteResult(ProposalRouteStatus.INVALID_RESPONSE))
    handler, launcher, output = _create_handler(tmp_path, router)

    assert handler.handle("Inicia o Explorer de um jeito diferente.") is True

    assert router.inputs == ["Inicia o Explorer de um jeito diferente."]
    assert launcher.paths == []
    assert output[-1] == "Não foi possível interpretar uma proposta de ação com segurança."


def test_natural_request_uses_capability_router(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    router = StaticRouter(
        ProposalRouteResult(
            ProposalRouteStatus.PROPOSAL,
            OpenWorkspaceLocationProposal("docs"),
        )
    )
    handler, launcher, _ = _create_handler(tmp_path, router)

    assert handler.handle("Mostre a pasta de documentação no Explorer.") is True

    assert router.inputs == ["Mostre a pasta de documentação no Explorer."]
    assert launcher.paths == []


def test_router_can_leave_unrelated_message_for_conversation(tmp_path: Path) -> None:
    router = StaticRouter()
    handler, launcher, output = _create_handler(tmp_path, router)

    assert handler.handle("Onde fica a pasta docs?") is False

    assert router.inputs == ["Onde fica a pasta docs?"]
    assert launcher.paths == []
    assert output == []


def test_conversation_loop_routes_open_proposal_and_confirmation(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    launcher = RecordingLauncher()
    provider = FakeProvider()
    output: list[str] = []

    run_conversation_loop(
        provider,
        create_temp_memory_service(tmp_path),
        open_location_capability=OpenWorkspaceLocationCapability(
            tmp_path.resolve(), launcher
        ),
        capability_proposal_router=StaticRouter(),
        input_reader=create_input_reader(
            ["Abra a pasta docs no Explorador.", "sim", "sair"]
        ),
        output_writer=output.append,
    )

    assert launcher.paths == [docs.resolve()]
    assert provider.messages == []
    assert "Pasta aberta no Explorador de Arquivos." in output
