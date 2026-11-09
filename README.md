# AutoTyper (Universal Linux & Windows Desktop App)

[![Release AutoTyper](https://github.com/ramusomu-beep/autotyper/actions/workflows/release.yml/badge.svg)](https://github.com/ramusomu-beep/autotyper/actions/workflows/release.yml)
[![Platform](https://img.shields.io/badge/platform-Linux%20%7C%20Windows-blue.svg)](https://github.com/ramusomu-beep/autotyper)
[![Python](https://img.shields.io/badge/python-3.10+-brightgreen.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A high-speed (up to 1,000 chars/sec), remote-compatible **Auto-Typer Desktop Application** with a modern **PyQt5 Dark Mode GUI**, **System Tray integration**, and a **Universal Dual-Engine Backend** for both **Linux** and **Windows**.

Works locally and across remote keyboard/desktop software (AnyDesk, Parsec, GlideX, RDP, Bluetooth HID, KVM, VNC).

---

## ✨ Features

- 🖥️ **Modern Desktop GUI**:
  - Dark-themed visual interface with built-in code/text editor.
  - Multi-snippet presets (Python, Markdown, SQL, Fast Text).
  - Live progress bar, characters typed counter, and real-time CPS (chars/second) meter.
  - Open & Save files directly or sync with `~/autotype_text.txt`.
- 🚀 **Universal Dual-Engine**:
  - **Windows Backend**: Uses Win32 `SendInput` with real Virtual Keys (`wVk`) and Hardware Scan Codes (`wScan`) + Unicode fallback.
  - **Linux Backend**: Low-level X11 `XTEST` with dynamic layout resolution (handles internal laptop keyboards, external USB keyboards, US ANSI, and UK ISO).
- ⏱️ **Flexible Speed & Realism**:
  - Adjustable speed slider (1 ms to 150 ms per char; up to 1,000 chars/s).
  - **Human Jitter Mode**: Simulates realistic human typing rhythm with natural random variations (±40%).
  - **Smart Indent**: Intelligent handling of IDE auto-indentation and tab expansions.
  - Configurable countdown timer before typing starts.
- 📌 **System Tray & Background Daemon**:
  - Minimizes cleanly to the system tray; stays ready in background.
  - Global hotkeys work system-wide even when minimized or when other apps are focused.
  - Native desktop notifications on Start, Pause, Resume, and Finish.
- ⌨️ **CLI & Headless Mode**:
  - Can run headless via terminal (`python autotyper.py --cli`).

---

## 🚀 Quick Start

### 1. Installation

Clone the repository and install requirements:

```bash
git clone https://github.com/ramusomu-beep/autotyper.git
cd autotyper
pip install -r requirements.txt
```

*(On Linux, ensure `python3-pyqt5` and `python-xlib` are available; installed automatically via `requirements.txt`)*

### 2. Launch the Desktop App

Simply run:
```bash
python autotyper.py
```
Or run as a module:
```bash
python -m autotyper
```

### 3. Launch in Headless CLI Mode

If you prefer terminal-only operation:
```bash
python autotyper.py --cli
```
Or pass a custom text file:
```bash
python autotyper.py --cli /path/to/my_code.py
```

---

## ⌨️ Global Hotkeys

Hotkeys work system-wide regardless of whether the app window or another application has focus:

| Shortcut | Action | Notes |
| :--- | :--- | :--- |
| **`F8`** or **`F3`** | **Start / Pause / Resume** | Instant toggle |
| **`Ctrl + Alt + Space`** | **Start / Pause / Resume** | Universal remote shortcut |
| **`Win + Alt`** (or `Super + Alt`) | **Start / Pause / Resume** | Press in either order |
| **`Ctrl + Alt + Enter`** | **Start / Pause / Resume** | Alternative toggle |
| **`Ctrl + Alt + X`** / **`Z`** | **Start / Pause / Resume** | Alternative toggle |
| **`Esc`** or **`Page Down`** | **Emergency Stop / Cancel** | Immediately stops and resets to beginning |
| **`Alt + =`** | **Slower** | Increases character delay (+0.02s) |
| **`Alt + -`** | **Faster** | Decreases character delay down to 1 ms (1,000 chars/s) |

---

## 🛠️ Building Standalone Binaries (Executables)

You can generate standalone single-file executables with zero Python installation required by end users:

```bash
python build.py
```

- **On Windows**: Produces `dist/AutoTyper.exe`
- **On Linux**: Produces `dist/AutoTyper` (ELF binary)

---

## 📦 Automated Releases (GitHub Actions)

This repository includes a fully configured automated CI/CD pipeline (`.github/workflows/release.yml`):
- Pushing any git tag starting with `v` (e.g., `git tag v2.0.0 && git push origin v2.0.0`) automatically:
  1. Builds `AutoTyper-Windows-x64.zip` (containing `AutoTyper.exe`, scripts, and docs).
  2. Builds `AutoTyper-Linux-x86_64.tar.gz` (standalone Linux binary).
  3. Publishes a official GitHub Release with release notes and downloadable assets.

---

## 🧩 Windows Built-in Keyboard Lock (`HP_Keyboard_Lock.ahk`)

For Windows laptop users who want to disable their built-in keyboard while using an external USB keyboard:
- Run `HP_Keyboard_Lock.ahk` with **AutoHotkey v2** and **AutoHotInterception** (see pre-configured bundle in `AutoTyper_and_Keyboard_Lock_Bundle.zip`).
- Blocks typing on the internal keyboard while keeping external keyboards 100% active.

---

## 📂 Project Architecture

```text
autotyper/
├── autotyper/
│   ├── __init__.py           # Package exports
│   ├── __main__.py           # python -m autotyper entry point
│   ├── app.py / gui.py       # PyQt5 modern dark mode GUI & System Tray
│   ├── cli.py                # Unified CLI / GUI dispatcher
│   ├── config.py             # Default constants and configuration
│   ├── engine.py             # Thread-safe AutoTyper state machine
│   ├── hotkeys.py            # Global hotkey listener (pynput)
│   ├── notify.py             # Cross-platform desktop notification service
│   ├── pid.py                # Single-instance process lock manager
│   ├── selftest.py           # Automated self-test suite
│   ├── win32_input.py        # Windows SendInput definitions
│   └── backends/             # Dual-Engine Input Layer
│       ├── __init__.py       # Factory (auto-detects Linux vs Windows)
│       ├── base.py           # Abstract KeyboardBackend interface
│       ├── windows.py        # Win32 SendInput (VirtualKey + ScanCode)
│       └── linux_x11.py      # Linux X11 XTEST + Dynamic Keymap Resolver
├── .github/workflows/
│   └── release.yml           # Automated multi-platform GitHub Release workflow
├── autotyper.py              # Root launcher entry point
├── build.py                  # Standalone PyInstaller build script
├── pyproject.toml            # Modern Python packaging configuration
├── requirements.txt          # Python dependencies
└── HP_Keyboard_Lock.ahk      # Windows AHK keyboard lock script
```

---

## 🧪 Self-Test

To verify that the engine and mock backend pass all tests on your system:

```bash
python autotyper.py --self-test
```
