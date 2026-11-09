"""Windows Win32 SendInput keyboard injection backend."""

import ctypes
import sys
import time
from typing import Optional

from .base import KeyboardBackend

# Guard Windows ctypes definitions so importing does not fail on Linux/macOS
if sys.platform == "win32":
    from ctypes import wintypes
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    winmm = ctypes.windll.winmm
    ULONG_PTR = wintypes.WPARAM

    try:
        winmm.timeBeginPeriod(1)
    except Exception:
        pass

    INPUT_KEYBOARD = 1
    KEYEVENTF_EXTENDEDKEY = 0x0001
    KEYEVENTF_KEYUP = 0x0002
    KEYEVENTF_UNICODE = 0x0004
    KEYEVENTF_SCANCODE = 0x0008

    VK_TAB = 0x09
    VK_RETURN = 0x0D
    VK_SHIFT = 0x10
    VK_CONTROL = 0x11
    VK_MENU = 0x12
    VK_CAPITAL = 0x14
    VK_END = 0x23
    VK_HOME = 0x24
    VK_LWIN = 0x5B
    VK_RWIN = 0x5C
    VK_LSHIFT = 0xA0
    VK_RSHIFT = 0xA1
    VK_LCONTROL = 0xA2
    VK_RCONTROL = 0xA3
    VK_LMENU = 0xA4
    VK_RMENU = 0xA5

    EXTENDED_VKS = {VK_HOME, VK_END, VK_LWIN, VK_RWIN, VK_RCONTROL, VK_RMENU}
    MODIFIER_VKS = (
        VK_SHIFT, VK_LSHIFT, VK_RSHIFT,
        VK_CONTROL, VK_LCONTROL, VK_RCONTROL,
        VK_MENU, VK_LMENU, VK_RMENU,
        VK_LWIN, VK_RWIN,
    )

    class MOUSEINPUT(ctypes.Structure):
        _fields_ = [
            ("dx", wintypes.LONG),
            ("dy", wintypes.LONG),
            ("mouseData", wintypes.DWORD),
            ("dwFlags", wintypes.DWORD),
            ("time", wintypes.DWORD),
            ("dwExtraInfo", ULONG_PTR),
        ]

    class KEYBDINPUT(ctypes.Structure):
        _fields_ = [
            ("wVk", wintypes.WORD),
            ("wScan", wintypes.WORD),
            ("dwFlags", wintypes.DWORD),
            ("time", wintypes.DWORD),
            ("dwExtraInfo", ULONG_PTR),
        ]

    class HARDWAREINPUT(ctypes.Structure):
        _fields_ = [
            ("uMsg", wintypes.DWORD),
            ("wParamL", wintypes.WORD),
            ("wParamH", wintypes.WORD),
        ]

    class _INPUT_UNION(ctypes.Union):
        _fields_ = [
            ("mi", MOUSEINPUT),
            ("ki", KEYBDINPUT),
            ("hi", HARDWAREINPUT),
        ]

    class INPUT(ctypes.Structure):
        _fields_ = [
            ("type", wintypes.DWORD),
            ("union", _INPUT_UNION),
        ]

    def _make_vk_input(vk, key_up=False):
        scan = user32.MapVirtualKeyW(vk, 0)
        flags = KEYEVENTF_EXTENDEDKEY if vk in EXTENDED_VKS else 0
        if key_up:
            flags |= KEYEVENTF_KEYUP
        inp = INPUT()
        inp.type = INPUT_KEYBOARD
        inp.union.ki = KEYBDINPUT(wVk=vk, wScan=scan, dwFlags=flags, time=0, dwExtraInfo=0)
        return inp

    def _make_unicode_input(ch, key_up=False):
        flags = KEYEVENTF_UNICODE
        if key_up:
            flags |= KEYEVENTF_KEYUP
        inp = INPUT()
        inp.type = INPUT_KEYBOARD
        inp.union.ki = KEYBDINPUT(wVk=0, wScan=ord(ch), dwFlags=flags, time=0, dwExtraInfo=0)
        return inp

    def _send_inputs(events):
        if not events:
            return
        n = len(events)
        arr = (INPUT * n)(*events)
        user32.SendInput(n, arr, ctypes.sizeof(INPUT))

    def _any_win32_modifier_down():
        for vk in (VK_SHIFT, VK_CONTROL, VK_MENU, VK_LWIN, VK_RWIN):
            if user32.GetAsyncKeyState(vk) & 0x8000:
                return True
        return False


class WindowsBackend(KeyboardBackend):
    """Win32 SendInput backend with virtual key and scan code resolution."""

    def __init__(self):
        if sys.platform != "win32":
            raise RuntimeError("WindowsBackend can only be used on Windows systems.")
        self._charcache = {}

    def ensure_ready(self) -> None:
        self._charcache.clear()
        self._ensure_capslock_off()
        self.cleanup_modifiers()

    def _ensure_capslock_off(self) -> None:
        try:
            if user32.GetKeyState(VK_CAPITAL) & 0x0001:
                _send_inputs([_make_vk_input(VK_CAPITAL, False), _make_vk_input(VK_CAPITAL, True)])
                time.sleep(0.01)
        except Exception:
            pass

    def cleanup_modifiers(self) -> None:
        try:
            ups = [_make_vk_input(vk, key_up=True) for vk in MODIFIER_VKS]
            _send_inputs(ups)
        except Exception:
            pass

    def wait_for_modifiers_release(self, timeout: float = 1.5) -> None:
        t_end = time.monotonic() + timeout
        while time.monotonic() < t_end:
            if not _any_win32_modifier_down():
                break
            time.sleep(0.02)
        self.cleanup_modifiers()
        time.sleep(0.03)

    def _resolve(self, ch: str):
        if ch in self._charcache:
            return self._charcache[ch]
        if ch in ("\n", "\r"):
            res = (VK_RETURN, 0)
        elif ch == "\t":
            res = (VK_TAB, 0)
        else:
            try:
                raw = user32.VkKeyScanW(ch)
            except ctypes.ArgumentError:
                raw = user32.VkKeyScanW(ord(ch))
            vk_scan = ctypes.c_short(raw).value
            if vk_scan == -1:
                res = None
            else:
                vk = vk_scan & 0xFF
                shift_state = (vk_scan >> 8) & 0xFF
                res = (vk, shift_state)
        self._charcache[ch] = res
        return res

    def _tap_vk(self, vk: int) -> None:
        _send_inputs([_make_vk_input(vk, False), _make_vk_input(vk, True)])

    def type_char(self, ch: str) -> bool:
        resolved = self._resolve(ch)
        try:
            if resolved is not None:
                vk, shift_state = resolved
                need_shift = bool(shift_state & 1)
                need_ctrl = bool(shift_state & 2)
                need_alt = bool(shift_state & 4)
                events = []
                if need_ctrl:
                    events.append(_make_vk_input(VK_LCONTROL, False))
                if need_alt:
                    events.append(_make_vk_input(VK_LMENU, False))
                if need_shift:
                    events.append(_make_vk_input(VK_LSHIFT, False))

                events.append(_make_vk_input(vk, False))
                events.append(_make_vk_input(vk, True))

                if need_shift:
                    events.append(_make_vk_input(VK_LSHIFT, True))
                if need_alt:
                    events.append(_make_vk_input(VK_LMENU, True))
                if need_ctrl:
                    events.append(_make_vk_input(VK_LCONTROL, True))

                _send_inputs(events)
                return True
            else:
                _send_inputs([_make_unicode_input(ch, False), _make_unicode_input(ch, True)])
                return True
        except Exception as e:
            print(f"[AutoTyper-Win32] Error typing {ch!r}: {e}")
            return False

    def newline(self, smart_indent: bool = True) -> None:
        self._tap_vk(VK_RETURN)
        if smart_indent:
            time.sleep(0.003)
            for _ in range(2):
                self._tap_vk(VK_HOME)
                time.sleep(0.001)
            # Shift+End to select any auto-indented whitespace, then Backspace/delete
            _send_inputs([_make_vk_input(VK_LSHIFT, False)])
            self._tap_vk(VK_END)
            _send_inputs([_make_vk_input(VK_LSHIFT, True)])
            # Tap backspace or delete if selection exists
            _send_inputs([_make_vk_input(0x08, False), _make_vk_input(0x08, True)]) # VK_BACK
