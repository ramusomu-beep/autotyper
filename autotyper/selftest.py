"""Cross-platform built-in self-test for the AutoTyper engine."""

import os
import tempfile
import time

from . import config, notify
from .backends.base import KeyboardBackend
from .engine import AutoTyper


class MockBackend(KeyboardBackend):
    def __init__(self):
        self.typed = []

    def cleanup_modifiers(self) -> None:
        pass

    def wait_for_modifiers_release(self, timeout: float = 1.5) -> None:
        pass

    def type_char(self, ch: str) -> bool:
        self.typed.append(ch)
        return True

    def newline(self, smart_indent: bool = True) -> None:
        self.typed.append("\n")


def run_self_test():
    orig_countdown = config.COUNTDOWN_SECONDS
    orig_notify = notify.notify
    config.COUNTDOWN_SECONDS = 0.05
    notify.notify = lambda msg, title="AutoTyper": None

    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
        f.write("ab\nc")
        path = f.name

    try:
        mock = MockBackend()
        t = AutoTyper(file_path=path, backend=mock, countdown_seconds=0.05)

        # Test normal typing
        t.toggle()
        t.worker_thread.join(timeout=5)
        assert mock.typed == ["a", "b", "\n", "c"], f"Unexpected typing: {mock.typed}"
        assert t.state == "STOPPED", f"Unexpected state: {t.state}"

        # Test cancel during countdown
        mock.typed.clear()
        t.countdown_seconds = 2.0
        t.toggle()
        time.sleep(0.05)
        t.cancel()
        if t.worker_thread:
            t.worker_thread.join(timeout=5)
        assert mock.typed == [], f"Expected empty after cancel, got {mock.typed}"
        assert t.state == "STOPPED", f"Unexpected state after cancel: {t.state}"

        # Test delay clamping
        t.adjust_delay(+10.0)
        assert t.delay == 1.0, f"Expected 1.0, got {t.delay}"
        t.adjust_delay(-10.0)
        assert t.delay == 0.001, f"Expected 0.001, got {t.delay}"

        print("Self-test: ALL TESTS PASSED SUCCESSFULLY! (Windows + Linux OK)")
    finally:
        os.remove(path)
        config.COUNTDOWN_SECONDS = orig_countdown
        notify.notify = orig_notify
