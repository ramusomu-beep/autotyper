"""Keyboard backend factory and platform selector."""

import sys
from .base import DummyBackend, KeyboardBackend


def get_backend() -> KeyboardBackend:
    """Return the optimal KeyboardBackend for the current platform."""
    if sys.platform == "win32":
        from .windows import WindowsBackend
        return WindowsBackend()
    elif sys.platform.startswith("linux"):
        try:
            from .linux_x11 import LinuxX11Backend
            return LinuxX11Backend()
        except Exception as e:
            print(f"[AutoTyper] Notice: Low-level X11 backend unavailable ({e}). Using headless backend.")
            return DummyBackend()
    else:
        return DummyBackend()


__all__ = ["KeyboardBackend", "DummyBackend", "get_backend"]
