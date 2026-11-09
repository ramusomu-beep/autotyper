"""Cross-platform desktop notification service."""

import subprocess
import sys
from typing import Callable, Optional

_custom_notifier: Optional[Callable[[str, str], None]] = None


def set_custom_notifier(callback: Optional[Callable[[str, str], None]]) -> None:
    """Register a custom notification handler (e.g. PyQt QSystemTrayIcon)."""
    global _custom_notifier
    _custom_notifier = callback


def notify(msg: str, title: str = "AutoTyper") -> None:
    """Send a desktop notification across Linux and Windows."""
    if _custom_notifier is not None:
        try:
            _custom_notifier(title, msg)
            return
        except Exception:
            pass

    if sys.platform.startswith("linux"):
        try:
            subprocess.run(
                ["notify-send", "-t", "2000", "-a", title, title, msg],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            pass
    elif sys.platform == "win32":
        # Best effort on Windows without heavy external dependencies
        try:
            from win10toast import ToastNotifier
            toaster = ToastNotifier()
            toaster.show_toast(title, msg, duration=2, threaded=True)
        except Exception:
            pass
