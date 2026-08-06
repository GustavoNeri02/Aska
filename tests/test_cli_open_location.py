from collections.abc import Sequence
from pathlib import Path

from apps.cli.app import run_conversation_loop
from apps.cli.handlers import NaturalOpenLocationHandler
from capabilities.desktop import OpenWorkspaceLocationCapability
from packages.conversation import (
    ConversationService,
    ModelMessage,
    OpenWorkspaceLocationProposal,
)
from tests.cli_support import FakeProvider, create_input_reader, create_temp_memory_service


class RecordingLauncher:
    def __init__(self) -> None:
        self.paths: list[Path] = []

    def open(self, path: Path) -> None:
        self.paths.append(path)


class SequencedProvider:
    def __init__(self, responses: list[str]) -> None:
        self._responses = iter(responses)
        self.messages: list[list[ModelMessage]] = []

    def generate(self, messages: Sequence[ModelMessage]) -> str:
        self.messages.append(list(messages))
        return next(self._responses)


def _create_handler(
    workspace: Path,
) -> tuple[NaturalOpenLocationHandler, RecordingLauncher, list[str]]:
    launcher = RecordingLauncher()
    output: list[str] = []
    handler = NaturalOpenLocationHandler(
        OpenWorkspaceLocationCapability(workspace.resolve(), launcher),
        ConversationService(FakeProvider(), create_temp_memory_service(workspace)),
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
    assert output[-2] == "Sistema > open_workspace_location: success"
    assert output[-1] == "Aska > Resposta local"


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
    assert output[-2] == "Sistema > open_workspace_location: cancelled"
    assert output[-1] == "Aska > Resposta local"


def test_unknown_confirmation_keeps_proposal_pending(tmp_path: Path) -> None:
    (tmp_path / "docs").mkdir()
    handler, launcher, output = _create_handler(tmp_path)

    handler.handle("Abra a pasta docs no Explorador.")
    handler.handle("talvez")
    handler.handle("sim")

    assert any("Confirmação não reconhecida" in message for message in output)
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
    assert output[-2] == "Sistema > open_workspace_location: target_changed"


def test_outside_workspace_is_rejected_without_launch(tmp_path: Path) -> None:
    handler, launcher, output = _create_handler(tmp_path)

    assert handler.handle("Abra a pasta ../fora no Explorador.") is True

    assert launcher.paths == []
    assert output[-2] == "Sistema > open_workspace_location: outside_workspace"


def test_absolute_explorer_target_is_rejected_locally(tmp_path: Path) -> None:
    handler, launcher, output = _create_handler(tmp_path)

    assert handler.handle("abra o explorer em c:/") is True

    assert launcher.paths == []
    assert output[-2] == "Sistema > open_workspace_location: outside_workspace"


def test_typed_natural_proposal_is_prepared_by_handler(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    handler, launcher, _ = _create_handler(tmp_path)

    assert (
        handler.handle_proposal(
            OpenWorkspaceLocationProposal("docs"),
            "Mostre a documentação.",
        )
        is True
    )

    assert launcher.paths == []


def test_non_exact_message_is_left_for_conversation_decision(tmp_path: Path) -> None:
    handler, launcher, output = _create_handler(tmp_path)

    assert handler.handle("Onde fica a pasta docs?") is False

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
        input_reader=create_input_reader(
            ["Abra a pasta docs no Explorador.", "sim", "sair"]
        ),
        output_writer=output.append,
    )

    assert launcher.paths == [docs.resolve()]
    assert len(provider.messages) == 1
    assert "Aska > Resposta local" in output


def test_conversation_loop_uses_one_model_call_for_semantic_proposal(
    tmp_path: Path,
) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    launcher = RecordingLauncher()
    provider = SequencedProvider(
        [
            '{"type":"capability_proposal",'
            '"action":"open_workspace_location","path":"docs"}',
            '{"type":"reply","content":"Abri a pasta de documentação."}',
        ]
    )
    output: list[str] = []

    run_conversation_loop(
        provider,
        create_temp_memory_service(tmp_path),
        open_location_capability=OpenWorkspaceLocationCapability(
            tmp_path.resolve(), launcher
        ),
        input_reader=create_input_reader(
            ["Queria ver a documentação numa janela.", "sim", "sair"]
        ),
        output_writer=output.append,
    )

    assert len(provider.messages) == 2
    assert launcher.paths == [docs.resolve()]


def test_conversation_loop_uses_same_decision_call_for_normal_reply(
    tmp_path: Path,
) -> None:
    launcher = RecordingLauncher()
    provider = FakeProvider('{"type":"reply","content":"Olá por aqui."}')
    output: list[str] = []

    run_conversation_loop(
        provider,
        create_temp_memory_service(tmp_path),
        open_location_capability=OpenWorkspaceLocationCapability(
            tmp_path.resolve(), launcher
        ),
        input_reader=create_input_reader(["Como você está?", "sair"]),
        output_writer=output.append,
    )

    assert len(provider.messages) == 1
    assert launcher.paths == []
    assert "Aska > Olá por aqui." in output


def test_invalid_decision_envelope_is_reported_without_execution(tmp_path: Path) -> None:
    launcher = RecordingLauncher()
    output: list[str] = []

    run_conversation_loop(
        FakeProvider("resposta fora do envelope"),
        create_temp_memory_service(tmp_path),
        open_location_capability=OpenWorkspaceLocationCapability(
            tmp_path.resolve(), launcher
        ),
        input_reader=create_input_reader(["pedido", "sair"]),
        output_writer=output.append,
    )

    assert launcher.paths == []
    assert (
        "Sistema > Resposta do modelo inválida para o contrato esperado."
        in output
    )
