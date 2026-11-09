"""CLI and GUI launcher for AutoTyper."""

import argparse
import os
import signal
import sys
import threading

from . import hotkeys, pid
from .config import DEFAULT_FILE, PID_FILE
from .engine import AutoTyper
from .selftest import run_self_test


def run_app(file_path):
    typer = AutoTyper(file_path=file_path)

    print("=" * 60)
    print("AutoTyper Active & Listening (Linux + Windows Universal)")
    print("=" * 60)
    print(f"Reading from : {file_path}")
    print("Hotkeys:")
    print("  - F8 / F3            : Toggle (Start / Pause / Resume)")
    print("  - Ctrl + Alt + Space : Toggle Alternative")
    print("  - Win + Alt          : Toggle Alternative")
    print("  - Esc / PgDown       : Emergency Stop & Reset")
    print("  - Alt + =            : Slower (+0.02s delay)")
    print("  - Alt + -            : Faster (-0.02s delay)")
    print("=" * 60)
    print("Tip: Edit the text file anytime; it re-reads on every Start!")
    print("Press Ctrl+C in this terminal to exit.\n")

    listener = hotkeys.start_listener(typer)
    stop_event = threading.Event()

    def _handle_signal(signum, frame):
        stop_event.set()

    previous_term = signal.signal(signal.SIGTERM, _handle_signal)
    previous_int = signal.signal(signal.SIGINT, _handle_signal)

    try:
        while not stop_event.wait(0.5):
            pass
    finally:
        typer.cancel()
        listener.stop()
        signal.signal(signal.SIGTERM, previous_term)
        signal.signal(signal.SIGINT, previous_int)


def _has_display():
    if sys.platform == "win32":
        return True
    return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv

    # Handle quick command shortcuts
    if len(argv) > 0:
        first = argv[0].lower()
        if first in ("stop", "kill", "cancel"):
            pid.stop_existing()
            return
        elif first == "--self-test":
            run_self_test()
            return

    parser = argparse.ArgumentParser(
        description="AutoTyper: High-speed universal keyboard automation app for Linux & Windows."
    )
    parser.add_argument("file", nargs="?", default=DEFAULT_FILE, help="Path to text file to type")
    parser.add_argument("--cli", action="store_true", help="Force headless CLI mode")
    parser.add_argument("--gui", action="store_true", help="Force GUI mode")
    parser.add_argument("--self-test", action="store_true", help="Run automated self-tests")

    args = parser.parse_args(argv)

    if args.self_test:
        run_self_test()
        return

    target_file = os.path.abspath(args.file) if os.path.isfile(args.file) else args.file

    # Decide whether to launch GUI or CLI
    use_gui = False
    if args.gui:
        use_gui = True
    elif not args.cli and _has_display():
        try:
            import PyQt5  # noqa: F401
            use_gui = True
        except ImportError:
            use_gui = False

    if use_gui:
        try:
            from .gui import run_gui
            run_gui(file_path=target_file)
            return
        except Exception as e:
            print(f"[AutoTyper] Warning: Could not launch GUI ({e}), falling back to CLI mode...")

    # CLI daemon single-instance check
    existing = pid.read_pid()
    if existing and existing != os.getpid() and pid.pid_alive(existing) and pid.is_autotyper(existing):
        print(f"AutoTyper is already running (PID {existing}). Use 'stop' first.")
        return

    with open(PID_FILE, "w") as f:
        f.write(str(os.getpid()))

    try:
        run_app(target_file)
    finally:
        pid.remove_pid_file()
