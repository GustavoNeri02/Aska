import sys
from collections.abc import Callable
from itertools import cycle
from threading import Event, Thread
from typing import TextIO


def run_with_loading(
    action: Callable[[], None],
    message: str,
    stream: TextIO = sys.stdout,
    interval: float = 0.1,
) -> None:
    finished = Event()

    def animate() -> None:
        for frame in cycle("|/-\\"):
            if finished.wait(interval):
                break
            stream.write(f"\r{frame} {message}")
            stream.flush()

    stream.write(f"| {message}")
    stream.flush()
    animation = Thread(target=animate, daemon=True)
    animation.start()

    try:
        action()
    finally:
        finished.set()
        animation.join()
        stream.write("\r\033[K")
        stream.flush()
