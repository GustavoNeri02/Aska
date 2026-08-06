from collections.abc import Callable

from packages.conversation import ConversationEvent, ConversationService


class TurnOutput:
    def __init__(
        self,
        conversation_service: ConversationService,
        output_writer: Callable[[str], None],
        *,
        conversational_events: bool,
    ) -> None:
        self._conversation_service = conversation_service
        self._output_writer = output_writer
        self._conversational_events = conversational_events
        self._local_facts: list[str] = []
        self._aska_spoke = False

    def write(self, message: str) -> None:
        if message.startswith("Aska >"):
            self._aska_spoke = True
            self._output_writer(message)
            return
        if not self._conversational_events:
            self._output_writer(message)
            return
        if message.startswith("Sistema >"):
            self._local_facts.append(message.removeprefix("Sistema >").strip())
            self._output_writer(message)
        else:
            self._local_facts.append(message)
            self._output_writer(f"Sistema > {message}")

    def finish(self, user_message: str, *, domain: str) -> None:
        try:
            if (
                self._conversational_events
                and self._local_facts
                and not self._aska_spoke
            ):
                response = self._conversation_service.present_event(
                    user_message,
                    ConversationEvent(
                        domain=domain,
                        kind="local_handler_result",
                        facts={"system_output": tuple(self._local_facts)},
                    ),
                )
                self._output_writer(f"Aska > {response}")
        finally:
            self._local_facts.clear()
            self._aska_spoke = False
