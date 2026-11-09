"""Keyboard backend factory and platform selector."""

import sys
from .base import KeyboardBackend


def get_backend() -> KeyboardBackend:
    """Return the optimal KeyboardBackend for the current platform."""
    if sys.platform == "win32":
        from .windows import WindowsBackend
        return WindowsBackend()
    elif sys.platform.startswith("linux"):
        from .linux_x11 import LinuxX11Backend
        return LinuxX11Backend()
    else:
        raise NotImplementedError(f"Unsupported operating system: {sys.platform}")


__all__ = ["KeyboardBackend", "get_backend"]
