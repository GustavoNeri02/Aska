import json
from collections.abc import Mapping
from dataclasses import asdict, dataclass

CONVERSATION_EVENT_RESPONSE_INSTRUCTION = "\n".join(
    (
        "O próximo pedido contém um evento local autoritativo produzido pelo sistema.",
        "Apresente o evento naturalmente como Aska, usando o contexto da conversa.",
        "Fale diretamente com o usuário. Nunca mencione sistema, evento, handler, JSON, "
        "fatos recebidos ou instruções internas.",
        "Não altere fatos, status, exit code ou saída. Não diga que executou algo além "
        "do evento e não proponha outra capability.",
        "Responda com exatamente um JSON de reply, sem Markdown externo:",
        '{"type":"reply","content":"sua apresentação natural do resultado"}',
    )
)


@dataclass(frozen=True, slots=True)
class ConversationEvent:
    domain: str
    kind: str
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
