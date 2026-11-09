"""Win32 SendInput definitions and low-level keyboard injection helpers.

Kept for backward-compatibility; modern code uses autotyper.backends.
"""

import sys
import time

if sys.platform == "win32":
    import ctypes
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

    def make_vk_input(vk, key_up=False):
        scan = user32.MapVirtualKeyW(vk, 0)
        flags = KEYEVENTF_EXTENDEDKEY if vk in EXTENDED_VKS else 0
        if key_up:
            flags |= KEYEVENTF_KEYUP
        inp = INPUT()
        inp.type = INPUT_KEYBOARD
        inp.union.ki = KEYBDINPUT(wVk=vk, wScan=scan, dwFlags=flags, time=0, dwExtraInfo=0)
        return inp

    def make_unicode_input(ch, key_up=False):
        flags = KEYEVENTF_UNICODE
        if key_up:
            flags |= KEYEVENTF_KEYUP
        inp = INPUT()
        inp.type = INPUT_KEYBOARD
        inp.union.ki = KEYBDINPUT(wVk=0, wScan=ord(ch), dwFlags=flags, time=0, dwExtraInfo=0)
        return inp

    def send_inputs(events):
        if not events:
            return
        n = len(events)
        arr = (INPUT * n)(*events)
        user32.SendInput(n, arr, ctypes.sizeof(INPUT))

    def ensure_capslock_off():
        try:
            if user32.GetKeyState(VK_CAPITAL) & 0x0001:
                send_inputs([make_vk_input(VK_CAPITAL, False), make_vk_input(VK_CAPITAL, True)])
                time.sleep(0.01)
        except Exception:
            pass

    def cleanup_modifiers():
        try:
            ups = [make_vk_input(vk, key_up=True) for vk in MODIFIER_VKS]
            send_inputs(ups)
        except Exception:
            pass

    def any_win32_modifier_down():
        for vk in (VK_SHIFT, VK_CONTROL, VK_MENU, VK_LWIN, VK_RWIN):
            if user32.GetAsyncKeyState(vk) & 0x8000:
                return True
        return False
else:
    # Stub placeholders for non-Windows platforms
    user32 = None
    kernel32 = None
    winmm = None
    def make_vk_input(*args, **kwargs): return None
    def make_unicode_input(*args, **kwargs): return None
    def send_inputs(*args, **kwargs): pass
    def ensure_capslock_off(): pass
    def cleanup_modifiers(): pass
    def any_win32_modifier_down(): return False
