from collections.abc import Sequence
from typing import Protocol

from packages.conversation.model import ModelMessage


class ModelProvider(Protocol):
    def generate(self, messages: Sequence[ModelMessage]) -> str: ...


class ModelProviderError(RuntimeError):
    """Raised when a model provider cannot generate a response."""
