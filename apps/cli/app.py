import os
from contextlib import suppress
from pathlib import Path

from apps.cli.confirmation import ModelConfirmationInterpreter
from apps.cli.conversation_loop import build_banner, run_conversation_loop
from apps.cli.loading import run_with_loading
from capabilities.desktop import OpenWorkspaceLocationCapability, WindowsExplorerLauncher
from capabilities.filesystem import (
    ListFilesCapability,
    ReadTextFileCapability,
    SearchTextCapability,
)
from capabilities.terminal import (
    PythonModuleRunner,
    PythonProjectTestRunner,
    RunProjectLintCapability,
    RunProjectTestsCapability,
)
from packages.conversation import (
    ModelFileIntentInterpreter,
    ModelMemoryIntentInterpreter,
    ModelProviderError,
    ModelTextSearchIntentInterpreter,
)
from packages.inference import OllamaProvider
from packages.memory import JsonMemoryDataSource, LocalMemoryRepository, MemoryService

__all__ = ["build_banner", "main", "run_conversation_loop"]


def main() -> None:
    try:
        workspace_root = Path(os.getenv("ASKA_WORKSPACE_ROOT", str(Path.cwd()))).resolve(
            strict=True
        )
        file_reader = ReadTextFileCapability(workspace_root)
        file_lister = ListFilesCapability(workspace_root)
        file_searcher = SearchTextCapability(workspace_root)
    except (OSError, ValueError):
        print("Erro > Workspace de leitura inválido.")
        return

    open_location_capability = _optional_open_location(workspace_root)
    project_tests_capability = _optional_project_tests(workspace_root)
    project_lint_capability = _optional_project_lint(workspace_root)
    model = os.getenv("ASKA_MODEL", "gemma3:12b")
    model_provider = OllamaProvider(
        model=model,
        base_url=os.getenv("ASKA_OLLAMA_URL", "http://localhost:11434"),
    )
    memory_service = MemoryService(
        LocalMemoryRepository(JsonMemoryDataSource("data/memory/memories.json"))
    )

    try:
        try:
            run_with_loading(model_provider.warm_up, f"Carregando {model}...")
        except ModelProviderError as error:
            print(f"Erro > Provider indisponível: {error}")
            return
        run_conversation_loop(
            model_provider,
            memory_service=memory_service,
            memory_intent_interpreter=ModelMemoryIntentInterpreter(model_provider),
            file_reader=file_reader,
            file_lister=file_lister,
            file_intent_interpreter=ModelFileIntentInterpreter(model_provider),
            file_searcher=file_searcher,
            text_search_intent_interpreter=ModelTextSearchIntentInterpreter(model_provider),
            open_location_capability=open_location_capability,
            project_tests_capability=project_tests_capability,
            project_lint_capability=project_lint_capability,
            confirmation_interpreter=ModelConfirmationInterpreter(model_provider),
        )
    finally:
        with suppress(ModelProviderError):
            model_provider.unload()


def _optional_open_location(
    workspace_root: Path,
) -> OpenWorkspaceLocationCapability | None:
    try:
        return OpenWorkspaceLocationCapability(workspace_root, WindowsExplorerLauncher())
    except ValueError:
        return None


def _optional_project_tests(workspace_root: Path) -> RunProjectTestsCapability | None:
    try:
        return RunProjectTestsCapability(workspace_root, PythonProjectTestRunner())
    except ValueError:
        return None


def _optional_project_lint(workspace_root: Path) -> RunProjectLintCapability | None:
    try:
        return RunProjectLintCapability(
            workspace_root,
            PythonModuleRunner("ruff", ("check", ".")),
        )
    except ValueError:
        return None


if __name__ == "__main__":
    main()
