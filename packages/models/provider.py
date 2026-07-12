from typing import Protocol


class ModelProvider(Protocol):
    def generate(self, message: str) -> str: ...


class ModelProviderError(RuntimeError):
    """Raised when a model provider cannot generate a response."""
