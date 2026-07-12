import json
from email.message import Message
from io import BytesIO
from unittest.mock import patch
from urllib.error import HTTPError, URLError

import pytest

from packages.models import ModelProviderError, OllamaProvider


class FakeHttpResponse(BytesIO):
    def __enter__(self) -> "FakeHttpResponse":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()


def test_ollama_provider_generates_chat_response() -> None:
    response = FakeHttpResponse(b'{"message":{"role":"assistant","content":"Ola!"}}')

    with patch("packages.models.ollama.urlopen", return_value=response) as urlopen_mock:
        provider = OllamaProvider(model="test-model")

        result = provider.generate("Olá")

    request = urlopen_mock.call_args.args[0]
    payload = json.loads(request.data)

    assert result == "Ola!"
    assert payload == {
        "model": "test-model",
        "messages": [{"role": "user", "content": "Olá"}],
        "stream": False,
    }


def test_ollama_provider_reports_connection_error() -> None:
    with patch("packages.models.ollama.urlopen", side_effect=URLError("offline")):
        provider = OllamaProvider(model="test-model")

        with pytest.raises(ModelProviderError, match="conectar ao Ollama"):
            provider.generate("Olá")


def test_ollama_provider_reports_api_error() -> None:
    error = HTTPError(
        url="http://localhost:11434/api/chat",
        code=404,
        msg="Not Found",
        hdrs=Message(),
        fp=BytesIO(b'{"error":"model not found"}'),
    )

    with patch("packages.models.ollama.urlopen", side_effect=error):
        provider = OllamaProvider(model="missing-model")

        with pytest.raises(ModelProviderError, match="erro 404: model not found"):
            provider.generate("Olá")


def test_ollama_provider_rejects_invalid_response() -> None:
    response = FakeHttpResponse(b'{"done":true}')

    with patch("packages.models.ollama.urlopen", return_value=response):
        provider = OllamaProvider(model="test-model")

        with pytest.raises(ModelProviderError, match="resposta inválida"):
            provider.generate("Olá")
