from pathlib import Path
from typing import cast

import pytest

from apps.cli.action_coordinator import CliActionCoordinator
from capabilities.desktop import OpenWorkspaceFileCapability, OpenWorkspaceLocationCapability
from capabilities.filesystem import ListFilesCapability
from capabilities.terminal import (
    ProjectTestProcessResult,
    RunProjectLintCapability,
    RunProjectTestsCapability,
)
from packages.conversation import (
    CapabilityProposal,
    OpenWorkspaceFileProposal,
    OpenWorkspaceLocationProposal,
    RunProjectLintProposal,
    RunProjectTestsProposal,
)


class Runner:
    def run(self, workspace_root: Path, timeout_seconds: float) -> ProjectTestProcessResult:
        del workspace_root, timeout_seconds
        return ProjectTestProcessResult(0, "", "")


class Launcher:
    def open(self, path: Path) -> None:
        del path


def build_coordinator(tmp_path: Path) -> CliActionCoordinator:
    workspace = tmp_path.resolve()
    return CliActionCoordinator.compose(
        OpenWorkspaceLocationCapability(workspace, Launcher()),
        OpenWorkspaceFileCapability(workspace, Launcher()),
        ListFilesCapability(workspace),
        RunProjectTestsCapability(workspace, Runner()),
        RunProjectLintCapability(workspace, Runner()),
        None,
    )


@pytest.mark.parametrize(
    ("proposal", "domain"),
    [
        (OpenWorkspaceLocationProposal("."), "desktop"),
        (OpenWorkspaceFileProposal("README.md"), "desktop"),
        (RunProjectTestsProposal(), "project_tests"),
        (RunProjectLintProposal(), "project_lint"),
    ],
)
def test_dispatch_routes_closed_proposal_catalog(
    tmp_path: Path,
    proposal: CapabilityProposal,
    domain: str,
) -> None:
    (tmp_path / "README.md").write_text("Aska", encoding="utf-8")
    result = build_coordinator(tmp_path).dispatch(proposal, "pedido")

    assert result.domain == domain
    assert result.kind == "confirmation_required"


@pytest.mark.parametrize(
    ("proposal", "domain"),
    [
        (OpenWorkspaceLocationProposal("."), "desktop"),
        (OpenWorkspaceFileProposal("README.md"), "desktop"),
        (RunProjectTestsProposal(), "project_tests"),
        (RunProjectLintProposal(), "project_lint"),
    ],
)
def test_dispatch_reports_unavailable_capability(
    proposal: CapabilityProposal,
    domain: str,
) -> None:
    coordinator = CliActionCoordinator(None, None, None, None)

    assert coordinator.dispatch(proposal, "pedido").kind == "unavailable"
    assert coordinator.dispatch(proposal, "pedido").domain == domain


def test_dispatch_rejects_unknown_proposal() -> None:
    coordinator = CliActionCoordinator(None, None, None, None)

    with pytest.raises(TypeError, match="unknown capability proposal"):
        coordinator.dispatch(cast(CapabilityProposal, object()), "pedido")


def test_cancel_pending_collects_every_interrupted_operation(tmp_path: Path) -> None:
    coordinator = build_coordinator(tmp_path)
    (tmp_path / "README.md").write_text("Aska", encoding="utf-8")
    coordinator.dispatch(OpenWorkspaceLocationProposal("."), "abra")
    coordinator.dispatch(OpenWorkspaceFileProposal("README.md"), "abra arquivo")
    coordinator.dispatch(RunProjectTestsProposal(), "teste")
    coordinator.dispatch(RunProjectLintProposal(), "lint")

    assert coordinator.cancel_pending() == (
        "open_workspace_location",
        "open_workspace_file",
        "run_project_tests",
        "run_project_lint",
    )
    assert coordinator.cancel_pending() == ()
