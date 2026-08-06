import json
from collections.abc import Mapping
from dataclasses import asdict, dataclass

EXTERNAL_EVENT_RESPONSE_INSTRUCTION = "\n".join(
    (
        "O próximo pedido contém um evento local autoritativo produzido pelo sistema.",
        "Apresente o evento naturalmente como Aska, usando o contexto da conversa.",
        "Não altere fatos, status, exit code ou saída. Não diga que executou algo além "
        "do evento e não proponha outra capability.",
        "Responda com exatamente um JSON de reply, sem Markdown externo:",
        '{"type":"reply","content":"sua apresentação natural do resultado"}',
    )
)


@dataclass(frozen=True, slots=True)
class ExternalActionEvent:
    action: str
    event: str
    facts: Mapping[str, object]

    def to_context_message(self, original_request: str) -> str:
        payload = asdict(self)
        return "\n".join(
            (
                "Evento local autoritativo para apresentação.",
                f"Pedido original: {original_request}",
                f"Evento JSON: {json.dumps(payload, ensure_ascii=False)}",
            )
        )
