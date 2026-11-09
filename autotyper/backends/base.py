"""Abstract base class for keyboard injection backends."""

from abc import ABC, abstractmethod


class KeyboardBackend(ABC):
    """Platform-independent interface for low-level keyboard input injection."""

    @abstractmethod
    def cleanup_modifiers(self) -> None:
        """Release any stuck modifier keys (Ctrl, Alt, Shift, Super)."""
        pass

    @abstractmethod
    def wait_for_modifiers_release(self, timeout: float = 1.5) -> None:
        """Wait until physical modifier keys are released before typing starts."""
        pass

    @abstractmethod
    def type_char(self, ch: str) -> bool:
        """Type a single character. Return True on success."""
        pass

    @abstractmethod
    def newline(self, smart_indent: bool = True) -> None:
        """Inject a Return/Enter key, with optional indentation handling."""
        pass

    def ensure_ready(self) -> None:
        """Perform any runtime readiness checks or layout cache refreshes."""
        pass
