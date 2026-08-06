from collections.abc import Mapping
from dataclasses import dataclass, field

from packages.conversation import ContextDocument


@dataclass(frozen=True, slots=True)
class HandlerResult:
    domain: str
    kind: str
    facts: Mapping[str, object] = field(default_factory=dict)
    context_document: ContextDocument | None = None
    original_request: str | None = None
