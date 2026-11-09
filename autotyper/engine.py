"""Cross-platform AutoTyper engine with thread-safe state machine."""

import os
import random
import threading
import time
from typing import Callable, Optional

from . import config, notify
from .backends import KeyboardBackend, get_backend


class AutoTyper:
    """State machine and typing engine for automating keystroke injection."""

    def __init__(
        self,
        file_path: Optional[str] = None,
        delay: Optional[float] = None,
        backend: Optional[KeyboardBackend] = None,
        human_jitter: bool = config.HUMAN_JITTER,
        smart_indent: bool = config.SMART_INDENT,
        countdown_seconds: float = config.COUNTDOWN_SECONDS,
    ):
        self.file_path = file_path if file_path is not None else config.DEFAULT_FILE
        self.delay = delay if delay is not None else config.CHAR_DELAY
        self.human_jitter = human_jitter
        self.smart_indent = smart_indent
        self.countdown_seconds = countdown_seconds

        self._backend = backend or get_backend()
        self.text = ""
        self._custom_text: Optional[str] = None
        self.state = "STOPPED"  # STOPPED / COUNTDOWN / RUNNING / PAUSED / RESUMING
        self.index = 0
        self.gen = 0
        self._paused_from = None
        self._typing = False
        self.cond = threading.Condition()
        self.worker_thread: Optional[threading.Thread] = None

        # UI / observer callbacks
        self.on_state_change: Optional[Callable[[str], None]] = None
        self.on_progress: Optional[Callable[[int, int, str], None]] = None
        self.on_countdown: Optional[Callable[[float], None]] = None

    def set_custom_text(self, text: Optional[str]) -> None:
        """Set explicit text directly (e.g. from GUI editor) bypassing file IO."""
        with self.cond:
            self._custom_text = text

    def load_text(self) -> str:
        """Load text from custom buffer or configured file path."""
        if self._custom_text is not None and self._custom_text.strip():
            return self._custom_text

        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    content = f.read().replace("\r\n", "\n")
                if content.strip():
                    return content
                print(f"[AutoTyper] Warning: {self.file_path} is empty; using fallback text.")
            except Exception as e:
                print(f"[AutoTyper] Warning: Could not read {self.file_path}: {e}")
        else:
            print(f"[AutoTyper] Warning: {self.file_path} not found; using fallback text.")
        return config.FALLBACK_TEXT

    def _set_state(self, new_state: str) -> None:
        self.state = new_state
        if self.on_state_change:
            try:
                self.on_state_change(new_state)
            except Exception:
                pass

    def _type_char(self, ch: str) -> bool:
        return self._backend.type_char(ch)

    def _newline(self) -> None:
        self._backend.newline(smart_indent=self.smart_indent)

    def _wait_for_modifiers_release(self) -> None:
        self._backend.wait_for_modifiers_release(timeout=1.5)

    def _worker(self, gen: int) -> None:
        remaining = float(self.countdown_seconds)
        with self.cond:
            while remaining > 0:
                while self.state == "PAUSED":
                    self.cond.wait()
                if self.gen != gen or self.state != "COUNTDOWN":
                    return

                if self.on_countdown:
                    try:
                        self.on_countdown(round(remaining, 1))
                    except Exception:
                        pass

                t0 = time.monotonic()
                step = min(0.1, remaining)
                self.cond.wait(timeout=step)
                remaining -= time.monotonic() - t0

            while self.state == "PAUSED":
                self.cond.wait()
            if self.gen != gen or self.state != "COUNTDOWN":
                return

            self._wait_for_modifiers_release()
            self._set_state("RUNNING")
            total = len(self.text)

        print(f"[AutoTyper] Typing started ({total} characters)...")
        notify.notify("Typing started")

        resumed_from_pause = False
        while True:
            with self.cond:
                while self.state == "PAUSED":
                    self.cond.wait()
                if self.gen != gen or self.state not in ("RUNNING", "RESUMING"):
                    return

                if self.state == "RESUMING":
                    rem = 0.5
                    while rem > 0 and self.state == "RESUMING":
                        t0 = time.monotonic()
                        self.cond.wait(timeout=min(0.1, rem))
                        rem -= time.monotonic() - t0
                    if self.gen != gen or self.state != "RESUMING":
                        continue
                    self._set_state("RUNNING")
                    resumed_from_pause = True

                if self.index >= len(self.text):
                    self._set_state("STOPPED")
                    self.cond.notify_all()
                    done, ch, line_start = True, None, False
                else:
                    done, ch = False, self.text[self.index]
                    line_start = self.index == 0 or self.text[self.index - 1] == "\n"

            if done:
                print("[AutoTyper] Finished typing!")
                notify.notify("Finished typing!")
                if self.on_progress:
                    try:
                        self.on_progress(total, total, "")
                    except Exception:
                        pass
                return

            if resumed_from_pause:
                self._wait_for_modifiers_release()
                resumed_from_pause = False

            self._typing = True
            try:
                if ch == "\n":
                    self._newline()
                    ok = True
                elif ch == "\t" and line_start:
                    ok = True
                    for _ in range(config.TAB_WIDTH):
                        ok = self._type_char(" ") and ok
                else:
                    ok = self._type_char(ch)
            finally:
                self._typing = False

            if not ok:
                print(f"[AutoTyper] Could not type {ch!r}; skipping.")

            with self.cond:
                if self.gen == gen and self.state in ("RUNNING", "PAUSED", "RESUMING"):
                    self.index += 1
                    curr_idx = self.index

            if self.on_progress:
                try:
                    self.on_progress(curr_idx, total, ch)
                except Exception:
                    pass

            nap = self.delay
            if self.human_jitter:
                nap *= random.uniform(0.6, 1.4)

            with self.cond:
                if self.gen == gen and self.state == "RUNNING":
                    self.cond.wait(timeout=nap)

    def toggle(self) -> None:
        """Toggle Start / Pause / Resume."""
        if self.state == "STOPPED":
            text = self.load_text()
            self._backend.ensure_ready()
            with self.cond:
                if self.state != "STOPPED":
                    return
                self.text = text
                self.index = 0
                self.gen += 1
                self._paused_from = None
                self._set_state("COUNTDOWN")
                self.worker_thread = threading.Thread(
                    target=self._worker, args=(self.gen,), daemon=True
                )
                self.worker_thread.start()
                self.cond.notify_all()
                chars, lines = len(self.text), len(self.text.splitlines())
            print(f"[AutoTyper] Loaded {chars} chars ({lines} lines)")
            print(f"[AutoTyper] Starting in {self.countdown_seconds}s...")
            notify.notify(f"Starting in {self.countdown_seconds}s...")
            return

        with self.cond:
            if self.state in ("COUNTDOWN", "RUNNING", "RESUMING"):
                self._paused_from = self.state
                self._set_state("PAUSED")
                self.cond.notify_all()
                action = "paused"
            elif self.state == "PAUSED":
                self._set_state("RESUMING")
                self.cond.notify_all()
                action = "resumed"
            else:
                return

        if action == "paused":
            self._backend.cleanup_modifiers()
            print("[AutoTyper] Paused.")
            notify.notify("Paused (Trigger hotkey to resume)")
        else:
            print("[AutoTyper] Resuming in 0.5s...")
            notify.notify("Resuming in 0.5s...")

    def cancel(self) -> None:
        """Cancel and reset current typing job."""
        was_active = False
        with self.cond:
            if self.state != "STOPPED":
                was_active = True
                self.gen += 1
                self._set_state("STOPPED")
                self.index = 0
                self.cond.notify_all()
        self._backend.cleanup_modifiers()
        if was_active:
            notify.notify("Stopped & Reset")
            print("[AutoTyper] Cancelled & Reset.")

    def adjust_delay(self, delta: float) -> None:
        """Dynamically increase or decrease per-character delay."""
        with self.cond:
            self.delay = round(max(0.001, min(1.0, self.delay + delta)), 4)
            current_delay = self.delay
        cps = 1.0 / current_delay if current_delay > 0 else 0
        direction = "Slower" if delta > 0 else "Faster"
        msg = f"Delay: {current_delay:.3f}s (~{cps:.0f} chars/s) [{direction}]"
        print(f"[AutoTyper] {msg}")
        notify.notify(msg)
