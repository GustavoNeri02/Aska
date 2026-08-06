from collections.abc import Sequence

import pytest

from packages.conversation import (
    ListFilesIntent,
    ModelFileIntentInterpreter,
    ModelMessage,
    ReadTextFileIntent,
    detect_explicit_file_location,
    detect_explicit_file_read,
    detect_known_document_query,
    detect_known_memory_file_location,
    should_interpret_file_read,
)


class StaticProvider:
    def __init__(self, response: str) -> None:
        self.response = response
        self.requests: list[list[ModelMessage]] = []

    def generate(self, messages: Sequence[ModelMessage]) -> str:
        self.requests.append(list(messages))
        return self.response


@pytest.mark.parametrize(
    "message",
    [
        "Leia AGENTS.md e resuma as instruções principais.",
        "Quero ler AGENTS.md.",
        "Abra o arquivo docs/README.md e explique.",
        "Pode abrir pyproject.toml?",
        "Consulte pyproject.toml para responder.",
        "Quero consultar docs/README.md.",
        "Veja o arquivo AGENTS.md.",
        "Resuma docs/product/vision.md.",
        "Mostre o conteúdo de docs/project/roadmap.md.",
        r"Retorne exatamente o que está em D:\Projetos\Aska\README.md.",
    ],
)
def test_file_read_gate_accepts_explicit_requests(message: str) -> None:
    assert should_interpret_file_read(message) is True


@pytest.mark.parametrize(
    "message",
    [
        "Quais arquivos existem no projeto?",
        "Localize o roadmap.",
        "Consulte a documentação do projeto.",
        "Veja quais arquivos Python existem.",
    ],
)
def test_file_gate_accepts_listing_requests(message: str) -> None:
    assert should_interpret_file_read(message) is True


@pytest.mark.parametrize(
    ("message", "path"),
    [
        ("Leia docs/project/roadmap.md", "docs/project/roadmap.md"),
        ("Abra o arquivo AGENTS.md e resuma.", "AGENTS.md"),
        ("CONSULTE pyproject.toml.", "pyproject.toml"),
        ("Resuma docs/product/vision.md", "docs/product/vision.md"),
        ("Mostre o conteúdo de docs/project/roadmap.md", "docs/project/roadmap.md"),
        (
            r"Retorne exatamente o que está em D:\Projetos\Aska\docs\README.md",
            r"D:\Projetos\Aska\docs\README.md",
        ),
    ],
)
def test_explicit_file_path_is_extracted_deterministically(
    message: str,
    path: str,
) -> None:
    assert detect_explicit_file_read(message) == ReadTextFileIntent(path)


@pytest.mark.parametrize(
    ("message", "path"),
    [
        ("Qual fase está em progresso no roadmap?", "roadmap.md"),
        ("O que o AGENTS diz sobre testes?", "AGENTS.md"),
        ("O README fala o quê sobre memória?", "README.md"),
        ("O que está definido no roadmap.md?", "roadmap.md"),
        (
            "Leia o documento de decisões e diga quais decisões estão relacionadas a ferramentas.",
            "decisions.md",
        ),
    ],
)
def test_known_document_content_query_is_detected_deterministically(
    message: str,
    path: str,
) -> None:
    assert detect_known_document_query(message) == ReadTextFileIntent(path)


@pytest.mark.parametrize(
    "message",
    [
        "Qual fase está em progresso?",
        "Você gosta de roadmaps?",
        "Como escrever um README?",
        "O que o documento diz?",
        "README é um formato comum.",
    ],
)
def test_known_document_query_rejects_ambiguous_conversation(message: str) -> None:
    assert detect_known_document_query(message) is None


def test_file_gate_accepts_clear_file_location_request() -> None:
    assert (
        should_interpret_file_read("Onde está o arquivo de memória em json no projeto Aska?")
        is True
    )


def test_explicit_file_location_is_detected_deterministically() -> None:
    assert detect_explicit_file_location("Onde está o arquivo memory.json?") == ListFilesIntent(
        name_contains="memory.json"
    )


@pytest.mark.parametrize(
    "message",
    [
        "Algum arquivo de memória aqui do projeto?",
        "Onde fica o arquivo das memórias?",
        "Existe um ficheiro de memoria?",
    ],
)
def test_known_memory_file_location_is_detected_deterministically(message: str) -> None:
    assert detect_known_memory_file_location(message) == ListFilesIntent(
        name_contains="memories.json",
        extension=".json",
    )


@pytest.mark.parametrize(
    "message",
    [
        "Como arquivos funcionam em Python?",
        "Leia isso para mim.",
        "Leia minha mensagem.",
        "Abra sua mente.",
        "Consulte sua memória.",
        "Veja o arquivo.",
        "O AGENTS.md é importante?",
        "Localize meu celular.",
        "Liste minhas compras.",
        "Leia AGENTS.md\ne README.md.",
    ],
)
def test_file_read_gate_rejects_common_or_ambiguous_messages(message: str) -> None:
    assert should_interpret_file_read(message) is False


def test_model_file_interpreter_returns_typed_intent() -> None:
    provider = StaticProvider('{"action":"read_text_file","path":"AGENTS.md"}')
    interpreter = ModelFileIntentInterpreter(provider)

    result = interpreter.interpret("Leia AGENTS.md e resuma.")

    assert result == ReadTextFileIntent("AGENTS.md")
    assert len(provider.requests) == 1
    assert "não leia arquivos" in provider.requests[0][0].content
    assert provider.requests[0][-1].content == "Leia AGENTS.md e resuma."


def test_model_file_interpreter_returns_typed_listing_intent() -> None:
    provider = StaticProvider(
        '{"action":"list_files","directory":".","name_contains":"roadmap","extension":".md"}'
    )

    result = ModelFileIntentInterpreter(provider).interpret("Localize o roadmap.")

    assert result == ListFilesIntent(".", "roadmap", ".md")


def test_model_file_interpreter_describes_memory_json_location_example() -> None:
    provider = StaticProvider(
        '{"action":"list_files","directory":".","name_contains":"memori","extension":".json"}'
    )

    result = ModelFileIntentInterpreter(provider).interpret(
        "Onde está o arquivo de memória em json no projeto Aska?"
    )

    assert result == ListFilesIntent(".", "memori", ".json")
    assert "arquivo de memória em JSON" in provider.requests[0][0].content


@pytest.mark.parametrize(
    "response",
    [
        '{"action":"none"}',
        '```json\n{"action":"read_text_file","path":"AGENTS.md"}\n```',
        'Texto {"action":"read_text_file","path":"AGENTS.md"}',
        '{"action":"read_text_file","path":"AGENTS.md","extra":true}',
        '{"action":"read_text_file","path":""}',
        '{"action":"read_text_file","path":42}',
        '{"action":"read_text_file","path":"AGENTS.md\nREADME.md"}',
        '{"action":"delete_file","path":"AGENTS.md"}',
        '{"action":"list_files","directory":".","name_contains":null}',
        '{"action":"list_files","directory":".","name_contains":"","extension":null}',
        '{"action":"list_files","directory":".","name_contains":null,'
        '"extension":null,"extra":true}',
        "not-json",
    ],
)
def test_model_file_interpreter_rejects_none_or_invalid_json(response: str) -> None:
    interpreter = ModelFileIntentInterpreter(StaticProvider(response))

    assert interpreter.interpret("Leia AGENTS.md.") is None
