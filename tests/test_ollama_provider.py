import json
from email.message import Message
from io import BytesIO
from unittest.mock import patch
from urllib.error import HTTPError, URLError

import pytest

from packages.conversation import ASKA_IDENTITY, ModelMessage, ModelProviderError, ModelRole
from packages.inference import OllamaProvider


class FakeHttpResponse(BytesIO):
    def __enter__(self) -> "FakeHttpResponse":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()


def test_ollama_provider_generates_chat_response() -> None:
    response = FakeHttpResponse(b'{"message":{"role":"assistant","content":"Ola!"}}')

    with patch("packages.inference.ollama.urlopen", return_value=response) as urlopen_mock:
        provider = OllamaProvider(model="test-model")

        result = provider.generate(
            [
                ModelMessage(ModelRole.SYSTEM, ASKA_IDENTITY),
                ModelMessage(ModelRole.USER, "Olá"),
                ModelMessage(ModelRole.ASSISTANT, "Olá, Gustavo"),
                ModelMessage(ModelRole.USER, "Como vai?"),
            ]
        )

    request = urlopen_mock.call_args.args[0]
    payload = json.loads(request.data)

    assert result == "Ola!"
    assert payload == {
        "model": "test-model",
        "messages": [
            {"role": "system", "content": ASKA_IDENTITY},
            {"role": "user", "content": "Olá"},
            {"role": "assistant", "content": "Olá, Gustavo"},
            {"role": "user", "content": "Como vai?"},
        ],
        "stream": False,
    }


def test_ollama_provider_reports_connection_error() -> None:
    with patch("packages.inference.ollama.urlopen", side_effect=URLError("offline")):
        provider = OllamaProvider(model="test-model")

        with pytest.raises(ModelProviderError, match="conectar ao Ollama"):
            provider.generate([ModelMessage(ModelRole.USER, "Olá")])


def test_ollama_provider_reports_api_error() -> None:
    error = HTTPError(
        url="http://localhost:11434/api/chat",
        code=404,
        msg="Not Found",
        hdrs=Message(),
        fp=BytesIO(b'{"error":"model not found"}'),
    )

    with patch("packages.inference.ollama.urlopen", side_effect=error):
        provider = OllamaProvider(model="missing-model")

        with pytest.raises(ModelProviderError, match="erro 404: model not found"):
            provider.generate([ModelMessage(ModelRole.USER, "Olá")])


def test_ollama_provider_rejects_invalid_response() -> None:
    response = FakeHttpResponse(b'{"done":true}')

    with patch("packages.inference.ollama.urlopen", return_value=response):
        provider = OllamaProvider(model="test-model")

        with pytest.raises(ModelProviderError, match="resposta inválida"):
            provider.generate([ModelMessage(ModelRole.USER, "Olá")])


def test_ollama_provider_warms_up_configured_model() -> None:
    response = FakeHttpResponse(b"")

    with patch("packages.inference.ollama.urlopen", return_value=response) as urlopen_mock:
        provider = OllamaProvider(model="test-model")

        provider.warm_up()

    request = urlopen_mock.call_args.args[0]
    assert request.full_url == "http://localhost:11434/api/generate"
    assert json.loads(request.data) == {"model": "test-model"}


def test_ollama_provider_unloads_model_from_configured_server() -> None:
    response = FakeHttpResponse(b"")

    with patch("packages.inference.ollama.urlopen", return_value=response) as urlopen_mock:
        provider = OllamaProvider(model="test-model", base_url="http://remote:11434")

        provider.unload()

    request = urlopen_mock.call_args.args[0]
    assert request.full_url == "http://remote:11434/api/generate"
    assert json.loads(request.data) == {"model": "test-model", "keep_alive": 0}
