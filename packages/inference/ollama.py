import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from packages.conversation.provider import ModelProviderError


class OllamaProvider:
    def __init__(
        self,
        model: str,
        base_url: str = "http://localhost:11434",
        timeout: float = 120.0,
    ) -> None:
        self._model = model
        self._chat_url = f"{base_url.rstrip('/')}/api/chat"
        self._timeout = timeout

    def generate(self, prompt: str) -> str:
        payload = json.dumps(
            {
                "model": self._model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
            }
        ).encode("utf-8")
        request = Request(
            self._chat_url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urlopen(request, timeout=self._timeout) as response:
                response_data = json.load(response)
        except HTTPError as error:
            detail = self._read_error_detail(error)
            raise ModelProviderError(f"Ollama respondeu com erro {error.code}: {detail}") from error
        except URLError as error:
            raise ModelProviderError(
                "Não foi possível conectar ao Ollama. Verifique se ele está em execução."
            ) from error
        except TimeoutError as error:
            raise ModelProviderError("O Ollama demorou demais para responder.") from error
        except (json.JSONDecodeError, UnicodeDecodeError) as error:
            raise ModelProviderError("Ollama retornou uma resposta inválida.") from error

        if not isinstance(response_data, dict):
            raise ModelProviderError(f"Resposta inválida: {response_data}")

        assistant_message_data = response_data.get("message")
        if not isinstance(assistant_message_data, dict):
            raise ModelProviderError("resposta inválida")

        content = assistant_message_data.get("content")
        if not isinstance(content, str) or not content.strip():
            raise ModelProviderError("Ollama retornou uma resposta vazia.")

        return content.strip()

    @staticmethod
    def _read_error_detail(error: HTTPError) -> str:
        try:
            response = error.read().decode("utf-8")
            error_data = json.loads(response)
            detail = error_data.get("error", response)
            return detail if isinstance(detail, str) else response
        except (json.JSONDecodeError, UnicodeDecodeError):
            return error.reason
