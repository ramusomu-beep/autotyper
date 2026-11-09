"""Linux X11 keyboard injection backend using Xlib/XTEST."""

import subprocess
import sys
import threading
import time
from typing import Optional

from .base import KeyboardBackend

# Guard Xlib imports so importing does not crash on platforms without Xlib
try:
    from Xlib import X, XK, display as xdisplay
    from Xlib.ext import xtest
    HAS_XLIB = True
except ImportError:
    HAS_XLIB = False


class LinuxX11Backend(KeyboardBackend):
    """Linux X11 backend with low-level XTEST injection and dynamic keymap resolution."""

    def __init__(self):
        if not HAS_XLIB:
            raise RuntimeError("python-xlib is required for the Linux X11 backend.")
        try:
            self._display = xdisplay.Display()
        except Exception as e:
            raise RuntimeError(f"Could not connect to X11 display: {e}")

        self._xlock = threading.Lock()
        self._charcache = {}
        self._keysym_map = {}
        self._shift_kc = 50
        self._altgr_kc = 0
        self.ensure_ready()

    def ensure_ready(self) -> None:
        self._rebuild_keymap()
        self.cleanup_modifiers()

    def _rebuild_keymap(self) -> None:
        d = self._display
        min_kc = d.display.info.min_keycode
        max_kc = d.display.info.max_keycode
        mapping_table = {}

        # Priority 1: Primary standard typing keys (keycodes 8 to 86)
        for kc in range(8, min(87, max_kc + 1)):
            try:
                syms = list(d.get_keyboard_mapping(kc, 1)[0])
            except Exception:
                continue
            for lvl, sym in enumerate(syms):
                if sym == 0:
                    continue
                if sym not in mapping_table or (lvl == 0 and mapping_table[sym][1] != 0):
                    mapping_table[sym] = (kc, lvl)

        # Priority 2: Other keys excluding problematic ghost/ISO keys
        problematic_kcs = {94, 187, 188}
        for kc in range(87, max_kc + 1):
            if kc in problematic_kcs:
                continue
            try:
                syms = list(d.get_keyboard_mapping(kc, 1)[0])
            except Exception:
                continue
            for lvl, sym in enumerate(syms):
                if sym == 0:
                    continue
                if sym not in mapping_table:
                    mapping_table[sym] = (kc, lvl)

        # Priority 3: Fallback for any remaining unmapped keys
        for kc in problematic_kcs:
            if kc > max_kc:
                continue
            try:
                syms = list(d.get_keyboard_mapping(kc, 1)[0])
            except Exception:
                continue
            for lvl, sym in enumerate(syms):
                if sym != 0 and sym not in mapping_table:
                    mapping_table[sym] = (kc, lvl)

        self._keysym_map = mapping_table
        self._charcache.clear()
        shift_sym = XK.string_to_keysym("Shift_L")
        shift_kc = mapping_table.get(shift_sym, (d.keysym_to_keycode(shift_sym), 0))[0]
        self._shift_kc = shift_kc if shift_kc else 50
        altgr_sym = XK.string_to_keysym("ISO_Level3_Shift")
        self._altgr_kc = mapping_table.get(altgr_sym, (d.keysym_to_keycode(altgr_sym), 0))[0]

    def cleanup_modifiers(self) -> None:
        d = self._display
        try:
            with self._xlock:
                for sym_name in (
                    "Shift_L", "Shift_R", "Control_L", "Control_R",
                    "Alt_L", "Alt_R", "Super_L", "Super_R",
                ):
                    sym = XK.string_to_keysym(sym_name)
                    kc = d.keysym_to_keycode(sym)
                    if kc:
                        xtest.fake_input(d, X.KeyRelease, kc)
                d.flush()
        except Exception:
            pass

        try:
            subprocess.run(
                ["xdotool", "keyup", "Shift_L", "Shift_R", "Control_L", "Control_R",
                 "Alt_L", "Alt_R", "Super_L", "Super_R"],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            pass

    def wait_for_modifiers_release(self, timeout: float = 1.5) -> None:
        t_end = time.monotonic() + timeout
        while time.monotonic() < t_end:
            try:
                with self._xlock:
                    qp = self._display.screen().root.query_pointer()
                if not (qp.mask & (1 | 4 | 8 | 64)):  # Shift, Control, Alt, Super
                    break
            except Exception:
                break
            time.sleep(0.03)
        self.cleanup_modifiers()
        time.sleep(0.04)

    @staticmethod
    def _keysym_for(ch: str) -> int:
        if ch in ("\n", "\r"):
            return XK.string_to_keysym("Return")
        if ch == "\t":
            return XK.string_to_keysym("Tab")
        cp = ord(ch)
        if cp <= 0x7F or 0xA0 <= cp <= 0xFF:
            return cp
        return 0x01000000 | cp

    def _resolve(self, ch: str):
        cached = self._charcache.get(ch)
        if cached is not None:
            return cached
        keysym = self._keysym_for(ch)
        result = self._keysym_map.get(keysym)
        if result is None:
            kc = self._display.keysym_to_keycode(keysym)
            if kc:
                try:
                    mapping = list(self._display.get_keyboard_mapping(kc, 1)[0])
                    level = mapping.index(keysym)
                except Exception:
                    level = 0
                result = (kc, level)
        if result is not None:
            self._charcache[ch] = result
        return result

    def _tap(self, keycode: int) -> None:
        # Caller holds self._xlock
        xtest.fake_input(self._display, X.KeyPress, keycode)
        self._display.flush()
        time.sleep(0.001)
        xtest.fake_input(self._display, X.KeyRelease, keycode)
        self._display.flush()

    def type_char(self, ch: str) -> bool:
        resolved = self._resolve(ch)
        if resolved is not None:
            keycode, level = resolved
            shift = level in (1, 3)
            altgr = level in (2, 3)
            d = self._display
            try:
                with self._xlock:
                    try:
                        if altgr and self._altgr_kc:
                            xtest.fake_input(d, X.KeyPress, self._altgr_kc)
                            d.flush()
                            time.sleep(0.001)
                        if shift and self._shift_kc:
                            xtest.fake_input(d, X.KeyPress, self._shift_kc)
                            d.flush()
                            time.sleep(0.001)
                        self._tap(keycode)
                    finally:
                        if shift and self._shift_kc:
                            xtest.fake_input(d, X.KeyRelease, self._shift_kc)
                            d.flush()
                            time.sleep(0.001)
                        if altgr and self._altgr_kc:
                            xtest.fake_input(d, X.KeyRelease, self._altgr_kc)
                            d.flush()
                            time.sleep(0.001)
                return True
            except Exception as e:
                print(f"[AutoTyper-Linux] Error typing {ch!r}: {e}")
                return False

        # Fallback for keysyms missing from current keymap
        try:
            result = subprocess.run(
                ["xdotool", "type", "--clearmodifiers", "--delay", "0", "--", ch],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return result.returncode == 0
        except Exception as e:
            print(f"[AutoTyper-Linux] Error fallback typing {ch!r}: {e}")
            return False

    def newline(self, smart_indent: bool = True) -> None:
        d = self._display
        with self._xlock:
            ret_sym = XK.string_to_keysym("Return")
            ret_kc = self._keysym_map.get(ret_sym, (d.keysym_to_keycode(ret_sym), 0))[0]
            if ret_kc:
                self._tap(ret_kc)
            if smart_indent:
                home_sym = XK.string_to_keysym("Home")
                end_sym = XK.string_to_keysym("End")
                home_kc = self._keysym_map.get(home_sym, (d.keysym_to_keycode(home_sym), 0))[0]
                end_kc = self._keysym_map.get(end_sym, (d.keysym_to_keycode(end_sym), 0))[0]
                time.sleep(0.003)
                if home_kc:
                    for _ in range(2):
                        self._tap(home_kc)
                        time.sleep(0.001)
                if end_kc:
                    try:
                        if self._shift_kc:
                            xtest.fake_input(d, X.KeyPress, self._shift_kc)
                            d.flush()
                            time.sleep(0.001)
                        self._tap(end_kc)
                    finally:
                        if self._shift_kc:
                            xtest.fake_input(d, X.KeyRelease, self._shift_kc)
                            d.flush()
                            time.sleep(0.001)
            d.flush()
