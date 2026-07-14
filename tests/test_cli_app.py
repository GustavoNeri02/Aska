from io import StringIO
from pathlib import Path

import pytest

from apps.cli.app import build_banner, main
from apps.cli.loading import run_with_loading
from capabilities.filesystem import TextFileReader
from packages.conversation import ModelProviderError


def test_build_banner_contains_application_name() -> None:
    banner = build_banner()

    assert "Aska" in banner


def test_loading_displays_message_and_clears_line() -> None:
    output = StringIO()

    run_with_loading(lambda: None, "Carregando modelo...", stream=output)

    assert output.getvalue() == "| Carregando modelo...\r\033[K"


def test_main_unloads_ollama_model_on_exit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ASKA_MODEL", "custom-model")
    monkeypatch.setattr("apps.cli.app.OllamaProvider.warm_up", lambda self: None)
    monkeypatch.setattr("apps.cli.app.run_with_loading", lambda action, message: action())
    monkeypatch.setattr("apps.cli.app.run_conversation_loop", lambda *args, **kwargs: None)
    unloaded: list[object] = []
    monkeypatch.setattr(
        "apps.cli.app.OllamaProvider.unload", lambda provider: unloaded.append(provider)
    )

    main()

    assert len(unloaded) == 1


def test_main_unloads_ollama_model_when_conversation_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail(*args: object, **kwargs: object) -> None:
        raise RuntimeError("unexpected failure")

    unloaded: list[object] = []
    monkeypatch.setattr("apps.cli.app.OllamaProvider.warm_up", lambda self: None)
    monkeypatch.setattr("apps.cli.app.run_with_loading", lambda action, message: action())
    monkeypatch.setattr("apps.cli.app.run_conversation_loop", fail)
    monkeypatch.setattr(
        "apps.cli.app.OllamaProvider.unload", lambda provider: unloaded.append(provider)
    )

    with pytest.raises(RuntimeError, match="unexpected failure"):
        main()

    assert len(unloaded) == 1


def test_main_reports_ollama_warm_up_error_and_does_not_start_conversation(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fail_warm_up(self: object) -> None:
        raise ModelProviderError("Modelo indisponível")

    conversation_started = False

    def start_conversation(*args: object, **kwargs: object) -> None:
        nonlocal conversation_started
        conversation_started = True

    monkeypatch.setattr("apps.cli.app.OllamaProvider.warm_up", fail_warm_up)
    monkeypatch.setattr("apps.cli.app.run_with_loading", lambda action, message: action())
    monkeypatch.setattr("apps.cli.app.run_conversation_loop", start_conversation)
    monkeypatch.setattr("apps.cli.app.OllamaProvider.unload", lambda self: None)

    main()

    assert "Aska > Modelo indisponível" in capsys.readouterr().out
    assert conversation_started is False


def test_main_configures_file_reader_with_allowed_workspace(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "README.md").write_text("contexto", encoding="utf-8")
    configured: dict[str, object] = {}

    def capture_configuration(*args: object, **kwargs: object) -> None:
        del args
        configured.update(kwargs)

    monkeypatch.setenv("ASKA_WORKSPACE", str(workspace))
    monkeypatch.setattr("apps.cli.app.OllamaProvider.warm_up", lambda self: None)
    monkeypatch.setattr("apps.cli.app.run_with_loading", lambda action, message: action())
    monkeypatch.setattr("apps.cli.app.run_conversation_loop", capture_configuration)
    monkeypatch.setattr("apps.cli.app.OllamaProvider.unload", lambda self: None)

    main()

    file_reader = configured["file_reader"]
    assert isinstance(file_reader, TextFileReader)
    assert file_reader.read("README.md").content == "contexto"
    assert configured["file_intent_interpreter"] is not None
