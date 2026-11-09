"""Global hotkey listener and modifier state across Windows and Linux."""

from pynput import keyboard
from . import notify

typer = None
_listener = None
_pressed = set()


def _norm(key):
    return _listener.canonical(key) if _listener else key


def _is_cmd(k):
    if k is None:
        return False
    k = _norm(k)
    return k in (keyboard.Key.cmd, keyboard.Key.cmd_l, keyboard.Key.cmd_r)


def _is_alt(k):
    if k is None:
        return False
    k = _norm(k)
    return k in (keyboard.Key.alt, keyboard.Key.alt_l, keyboard.Key.alt_r, keyboard.Key.alt_gr)


def _is_ctrl(k):
    if k is None:
        return False
    k = _norm(k)
    return k in (keyboard.Key.ctrl, keyboard.Key.ctrl_l, keyboard.Key.ctrl_r)


def has_cmd():
    return any(_is_cmd(k) for k in _pressed)


def has_alt():
    return any(_is_alt(k) for k in _pressed)


def has_ctrl():
    return any(_is_ctrl(k) for k in _pressed)


def clear_pressed():
    _pressed.clear()


def _is_key(k, chars, vks):
    if k is None:
        return False
    vk = getattr(k, "vk", None)
    ch = getattr(k, "char", None)
    if vk in vks or (ch and ch in chars):
        return True
    nk = _norm(k)
    return getattr(nk, "vk", None) in vks or getattr(nk, "char", None) in chars


def on_press(key, injected=False):
    if injected or key is None or (typer and typer._typing):
        return
    norm_key = _norm(key)
    if norm_key in _pressed:  # ignore auto-repeat
        return
    _pressed.add(norm_key)

    # Cancel Hotkeys: Escape or Page Down
    if norm_key in (_norm(keyboard.Key.esc), _norm(keyboard.Key.page_down), keyboard.Key.esc, keyboard.Key.page_down):
        if typer:
            typer.cancel()
        return

    # Toggle Shortcuts:
    # 1. Ctrl + Alt + Space / Enter / X / Z
    if has_ctrl() and has_alt():
        if norm_key in (_norm(keyboard.Key.space), _norm(keyboard.Key.enter)) or _is_key(
            key, ("x", "X", "\x18", "z", "Z", "\x1a"), (0x58, 0x5A)
        ):
            if typer:
                typer.toggle()
            return
        elif _is_key(key, ("c", "C", "\x03"), (0x43,)):
            if typer:
                typer.cancel()
            return

    # 2. Windows / Super + Alt
    if (_is_alt(norm_key) and has_cmd()) or (_is_cmd(norm_key) and has_alt()):
        if typer:
            typer.toggle()
        return

    # 3. Function keys: F8 or F3
    if norm_key in (_norm(keyboard.Key.f8), _norm(keyboard.Key.f3), keyboard.Key.f8, keyboard.Key.f3):
        if typer:
            typer.toggle()
        return

    # Speed adjustments: Alt + = (Slower) / Alt + - (Faster)
    if _is_key(key, ("=", "+"), (0xBB, 0x6B)):
        if has_alt() and typer and not typer._typing:
            typer.adjust_delay(+0.02)
    elif _is_key(key, ("-", "_"), (0xBD, 0x6D)):
        if has_alt() and typer and not typer._typing:
            typer.adjust_delay(-0.02)


def on_release(key, injected=False):
    if injected or key is None:
        return
    _pressed.discard(_norm(key))


def start_listener(auto_typer):
    global typer, _listener
    typer = auto_typer
    _listener = keyboard.Listener(on_press=on_press, on_release=on_release)
    _listener.start()
    return _listener
