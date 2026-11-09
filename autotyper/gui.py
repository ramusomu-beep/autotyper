"""Modern PyQt5 Desktop GUI and System Tray application for AutoTyper."""

import os
import sys
import threading
from typing import Optional

from PyQt5 import QtCore, QtGui, QtWidgets

from . import config, hotkeys, notify
from .backends import get_backend
from .config import DEFAULT_FILE
from .engine import AutoTyper

DARK_STYLESHEET = """
QMainWindow, QWidget {
    background-color: #1e1e2e;
    color: #cdd6f4;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    font-size: 13px;
}

QGroupBox {
    border: 1px solid #313244;
    border-radius: 8px;
    margin-top: 14px;
    padding-top: 10px;
    font-weight: bold;
    color: #89b4fa;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    padding: 0 4px;
}

QPlainTextEdit {
    background-color: #181825;
    color: #cdd6f4;
    border: 1px solid #313244;
    border-radius: 6px;
    padding: 8px;
    font-family: "Cascadia Code", "Fira Code", "Consolas", "Courier New", monospace;
    font-size: 13px;
    selection-background-color: #45475a;
}

QPlainTextEdit:focus {
    border: 1px solid #89b4fa;
}

QPushButton {
    background-color: #313244;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 6px;
    padding: 6px 14px;
    font-weight: 600;
}

QPushButton:hover {
    background-color: #45475a;
}

QPushButton:pressed {
    background-color: #585b70;
}

QPushButton#btnStart {
    background-color: #a6e3a1;
    color: #11111b;
    border: none;
    font-size: 14px;
    font-weight: bold;
    padding: 10px 20px;
}

QPushButton#btnStart:hover {
    background-color: #94e2d5;
}

QPushButton#btnStart:pressed {
    background-color: #74c7ec;
}

QPushButton#btnCancel {
    background-color: #f38ba8;
    color: #11111b;
    border: none;
    font-size: 14px;
    font-weight: bold;
    padding: 10px 20px;
}

QPushButton#btnCancel:hover {
    background-color: #eba0ac;
}

QPushButton#btnCancel:pressed {
    background-color: #fab387;
}

QProgressBar {
    background-color: #181825;
    border: 1px solid #313244;
    border-radius: 6px;
    text-align: center;
    color: #cdd6f4;
    font-weight: bold;
    height: 20px;
}

QProgressBar::chunk {
    background-color: #89b4fa;
    border-radius: 5px;
}

QSlider::groove:horizontal {
    border: 1px solid #313244;
    height: 6px;
    background: #181825;
    margin: 2px 0;
    border-radius: 3px;
}

QSlider::handle:horizontal {
    background: #89b4fa;
    border: 1px solid #74c7ec;
    width: 16px;
    margin: -5px 0;
    border-radius: 8px;
}

QSlider::handle:horizontal:hover {
    background: #b4befe;
}

QCheckBox {
    spacing: 8px;
}

QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border-radius: 4px;
    border: 1px solid #45475a;
    background-color: #181825;
}

QCheckBox::indicator:checked {
    background-color: #89b4fa;
    border: 1px solid #89b4fa;
}

QComboBox {
    background-color: #181825;
    border: 1px solid #313244;
    border-radius: 6px;
    padding: 4px 8px;
    color: #cdd6f4;
}

QComboBox::drop-down {
    border: none;
    width: 20px;
}

QSpinBox {
    background-color: #181825;
    border: 1px solid #313244;
    border-radius: 6px;
    padding: 4px;
    color: #cdd6f4;
}

QLabel#statusPill {
    font-weight: bold;
    font-size: 13px;
    padding: 4px 12px;
    border-radius: 12px;
}

QLabel#hotkeyBadge {
    background-color: #313244;
    color: #f9e2af;
    border-radius: 4px;
    padding: 2px 6px;
    font-family: monospace;
    font-weight: bold;
}
"""


class AutoTyperBridge(QtCore.QObject):
    """Thread-safe bridge between AutoTyper engine worker and Qt GUI."""
    stateChanged = QtCore.pyqtSignal(str)
    progressUpdated = QtCore.pyqtSignal(int, int, str)
    countdownTick = QtCore.pyqtSignal(float)
    notificationTriggered = QtCore.pyqtSignal(str, str)


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, file_path=DEFAULT_FILE):
        super().__init__()
        self.file_path = file_path
        self.bridge = AutoTyperBridge()
        self.typer = AutoTyper(file_path=self.file_path)

        # Connect bridge callbacks to engine
        self.typer.on_state_change = lambda s: self.bridge.stateChanged.emit(s)
        self.typer.on_progress = lambda cur, tot, ch: self.bridge.progressUpdated.emit(cur, tot, ch)
        self.typer.on_countdown = lambda rem: self.bridge.countdownTick.emit(rem)

        # Wire notification hook to system tray
        notify.set_custom_notifier(lambda title, msg: self.bridge.notificationTriggered.emit(title, msg))

        self.setWindowTitle("AutoTyper Desktop")
        self.setMinimumSize(780, 620)
        self.setStyleSheet(DARK_STYLESHEET)

        self.init_ui()
        self.init_tray()
        self.init_hotkeys()
        self.connect_signals()

        self.load_initial_content()

    def init_ui(self):
        central_widget = QtWidgets.QWidget(self)
        self.setCentralWidget(central_widget)
        main_layout = QtWidgets.QVBoxLayout(central_widget)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        # --- Top Header & Status Banner ---
        top_bar = QtWidgets.QHBoxLayout()

        title_label = QtWidgets.QLabel("AutoTyper", self)
        title_label.setStyleSheet("font-size: 20px; font-weight: bold; color: #cdd6f4;")
        top_bar.addWidget(title_label)

        sub_label = QtWidgets.QLabel("High-Speed & Remote Keyboard Engine", self)
        sub_label.setStyleSheet("color: #a6adc8; font-size: 12px; margin-left: 6px;")
        top_bar.addWidget(sub_label)

        top_bar.addStretch()

        self.lbl_status = QtWidgets.QLabel("STOPPED", self)
        self.lbl_status.setObjectName("statusPill")
        self.lbl_status.setStyleSheet("background-color: #45475a; color: #cdd6f4;")
        top_bar.addWidget(self.lbl_status)

        main_layout.addLayout(top_bar)

        # --- Progress Bar & Real-time Stats ---
        stats_layout = QtWidgets.QHBoxLayout()
        self.lbl_chars = QtWidgets.QLabel("Chars: 0 / 0 (0%)", self)
        self.lbl_chars.setStyleSheet("color: #a6adc8; font-size: 12px;")
        self.lbl_cps = QtWidgets.QLabel("Speed: ~1000 chars/s", self)
        self.lbl_cps.setStyleSheet("color: #89b4fa; font-weight: bold; font-size: 12px;")
        stats_layout.addWidget(self.lbl_chars)
        stats_layout.addStretch()
        stats_layout.addWidget(self.lbl_cps)
        main_layout.addLayout(stats_layout)

        self.progress_bar = QtWidgets.QProgressBar(self)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        main_layout.addWidget(self.progress_bar)

        # --- Editor Area with Snippets and Controls ---
        editor_group = QtWidgets.QGroupBox("Text to Type", self)
        editor_layout = QtWidgets.QVBoxLayout(editor_group)

        # Toolbar above editor
        tb_layout = QtWidgets.QHBoxLayout()

        self.combo_presets = QtWidgets.QComboBox(self)
        self.combo_presets.addItems([
            "Quick Presets...",
            "Python: Hello World",
            "Python: Fibonacci Generator",
            "Markdown: Project Notes",
            "SQL: Table Creation",
            "Fast Lorem Ipsum",
        ])
        self.combo_presets.currentIndexChanged.connect(self.on_preset_selected)
        tb_layout.addWidget(self.combo_presets)

        btn_open = QtWidgets.QPushButton("Open File...", self)
        btn_open.clicked.connect(self.open_file_dialog)
        tb_layout.addWidget(btn_open)

        btn_save = QtWidgets.QPushButton("Save to File...", self)
        btn_save.clicked.connect(self.save_file_dialog)
        tb_layout.addWidget(btn_save)

        btn_sync_default = QtWidgets.QPushButton("Save to ~/autotype_text.txt", self)
        btn_sync_default.clicked.connect(self.save_to_default_file)
        tb_layout.addWidget(btn_sync_default)

        tb_layout.addStretch()

        btn_clear = QtWidgets.QPushButton("Clear", self)
        btn_clear.clicked.connect(self.clear_text)
        tb_layout.addWidget(btn_clear)

        editor_layout.addLayout(tb_layout)

        self.editor = QtWidgets.QPlainTextEdit(self)
        self.editor.setPlaceholderText("Paste or type the text you want AutoTyper to inject...")
        self.editor.textChanged.connect(self.on_editor_text_changed)
        editor_layout.addWidget(self.editor)

        main_layout.addWidget(editor_group, stretch=1)

        # --- Settings & Configuration Panel ---
        settings_group = QtWidgets.QGroupBox("Typing Settings", self)
        settings_layout = QtWidgets.QGridLayout(settings_group)
        settings_layout.setHorizontalSpacing(16)
        settings_layout.setVerticalSpacing(8)

        # Delay Slider (1ms to 200ms)
        lbl_delay = QtWidgets.QLabel("Delay per Character:", self)
        self.slider_delay = QtWidgets.QSlider(QtCore.Qt.Horizontal, self)
        self.slider_delay.setRange(1, 150)  # 1ms to 150ms
        self.slider_delay.setValue(1)
        self.slider_delay.valueChanged.connect(self.on_delay_slider_changed)

        self.lbl_delay_val = QtWidgets.QLabel("1 ms (~1000 cps)", self)
        self.lbl_delay_val.setStyleSheet("font-weight: bold; color: #89b4fa;")

        settings_layout.addWidget(lbl_delay, 0, 0)
        settings_layout.addWidget(self.slider_delay, 0, 1)
        settings_layout.addWidget(self.lbl_delay_val, 0, 2)

        # Countdown Seconds
        lbl_countdown = QtWidgets.QLabel("Countdown Delay:", self)
        self.spin_countdown = QtWidgets.QSpinBox(self)
        self.spin_countdown.setRange(0, 30)
        self.spin_countdown.setValue(int(config.COUNTDOWN_SECONDS))
        self.spin_countdown.setSuffix(" sec")
        self.spin_countdown.valueChanged.connect(self.on_countdown_changed)

        settings_layout.addWidget(lbl_countdown, 1, 0)
        settings_layout.addWidget(self.spin_countdown, 1, 1)

        # Toggles
        toggles_layout = QtWidgets.QHBoxLayout()
        self.chk_jitter = QtWidgets.QCheckBox("Human Jitter (±40% realistic variation)", self)
        self.chk_jitter.setChecked(config.HUMAN_JITTER)
        self.chk_jitter.toggled.connect(lambda v: setattr(self.typer, "human_jitter", v))

        self.chk_smart_indent = QtWidgets.QCheckBox("Smart Indent (cleans IDE auto-tabs)", self)
        self.chk_smart_indent.setChecked(config.SMART_INDENT)
        self.chk_smart_indent.toggled.connect(lambda v: setattr(self.typer, "smart_indent", v))

        toggles_layout.addWidget(self.chk_jitter)
        toggles_layout.addWidget(self.chk_smart_indent)
        toggles_layout.addStretch()

        settings_layout.addLayout(toggles_layout, 2, 0, 1, 3)

        main_layout.addWidget(settings_group)

        # --- Hotkeys Reference Card ---
        hotkeys_box = QtWidgets.QHBoxLayout()
        hotkeys_box.setSpacing(10)
        hk_items = [
            ("Start / Pause", "F8 / F3"),
            ("Universal Toggle", "Ctrl+Alt+Space"),
            ("Emergency Stop", "Esc / PgDown"),
            ("Speed Up/Down", "Alt +/-"),
        ]
        for name, key in hk_items:
            pill = QtWidgets.QWidget(self)
            pill.setStyleSheet("background-color: #181825; border-radius: 6px; padding: 4px 8px;")
            p_layout = QtWidgets.QHBoxLayout(pill)
            p_layout.setContentsMargins(6, 4, 6, 4)
            lbl_n = QtWidgets.QLabel(f"{name}:", pill)
            lbl_n.setStyleSheet("color: #a6adc8; font-size: 11px;")
            lbl_k = QtWidgets.QLabel(key, pill)
            lbl_k.setObjectName("hotkeyBadge")
            p_layout.addWidget(lbl_n)
            p_layout.addWidget(lbl_k)
            hotkeys_box.addWidget(pill)

        main_layout.addLayout(hotkeys_box)

        # --- Big Action Buttons ---
        btn_layout = QtWidgets.QHBoxLayout()
        btn_layout.setSpacing(16)

        self.btn_start = QtWidgets.QPushButton("START TYPING", self)
        self.btn_start.setObjectName("btnStart")
        self.btn_start.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.btn_start.clicked.connect(self.on_start_toggle_clicked)
        btn_layout.addWidget(self.btn_start, stretch=2)

        self.btn_cancel = QtWidgets.QPushButton("STOP & CANCEL", self)
        self.btn_cancel.setObjectName("btnCancel")
        self.btn_cancel.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.btn_cancel.clicked.connect(self.on_cancel_clicked)
        btn_layout.addWidget(self.btn_cancel, stretch=1)

        main_layout.addLayout(btn_layout)

    def init_tray(self):
        self.tray_icon = QtWidgets.QSystemTrayIcon(self)
        # Create standard icon or fallback colored circle pixmap
        pixmap = QtGui.QPixmap(32, 32)
        pixmap.fill(QtCore.Qt.transparent)
        painter = QtGui.QPainter(pixmap)
        painter.setBrush(QtGui.QBrush(QtGui.QColor("#89b4fa")))
        painter.setPen(QtCore.Qt.NoPen)
        painter.drawRoundedRect(2, 2, 28, 28, 6, 6)
        painter.setPen(QtGui.QColor("#11111b"))
        painter.setFont(QtGui.QFont("Arial", 16, QtGui.QFont.Bold))
        painter.drawText(pixmap.rect(), QtCore.Qt.AlignCenter, "AT")
        painter.end()

        self.icon = QtGui.QIcon(pixmap)
        self.tray_icon.setIcon(self.icon)
        self.setWindowIcon(self.icon)

        # Tray Context Menu
        menu = QtWidgets.QMenu()
        act_show = menu.addAction("Show AutoTyper")
        act_show.triggered.connect(self.show_normal_window)

        act_toggle = menu.addAction("Start / Pause / Resume")
        act_toggle.triggered.connect(self.on_start_toggle_clicked)

        act_stop = menu.addAction("Emergency Stop")
        act_stop.triggered.connect(self.on_cancel_clicked)

        menu.addSeparator()
        act_quit = menu.addAction("Quit")
        act_quit.triggered.connect(QtWidgets.qApp.quit)

        self.tray_icon.setContextMenu(menu)
        self.tray_icon.activated.connect(self.on_tray_activated)
        self.tray_icon.show()

    def init_hotkeys(self):
        """Start background global hotkey listener with pynput."""
        self.hotkey_listener = hotkeys.start_listener(self.typer)

    def connect_signals(self):
        self.bridge.stateChanged.connect(self.update_ui_state)
        self.bridge.progressUpdated.connect(self.update_progress)
        self.bridge.countdownTick.connect(self.update_countdown_label)
        self.bridge.notificationTriggered.connect(self.show_tray_notification)

    def show_tray_notification(self, title: str, msg: str):
        if self.tray_icon.isVisible():
            self.tray_icon.showMessage(title, msg, QtWidgets.QSystemTrayIcon.Information, 1800)

    def on_tray_activated(self, reason):
        if reason == QtWidgets.QSystemTrayIcon.Trigger:
            if self.isVisible():
                self.hide()
            else:
                self.show_normal_window()

    def show_normal_window(self):
        self.show()
        self.raise_()
        self.activateWindow()

    def closeEvent(self, event):
        """Minimize to tray on window close button."""
        if self.tray_icon.isVisible():
            self.hide()
            self.tray_icon.showMessage(
                "AutoTyper Active",
                "AutoTyper is running in the background. Trigger your hotkeys or click tray icon to restore.",
                QtWidgets.QSystemTrayIcon.Information,
                2000,
            )
            event.ignore()
        else:
            self.typer.cancel()
            if self.hotkey_listener:
                self.hotkey_listener.stop()
            event.accept()

    def load_initial_content(self):
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    self.editor.setPlainText(content)
                    return
            except Exception:
                pass
        self.editor.setPlainText(config.FALLBACK_TEXT)

    def on_editor_text_changed(self):
        text = self.editor.toPlainText()
        self.typer.set_custom_text(text)
        total = len(text)
        self.lbl_chars.setText(f"Chars: 0 / {total} (0%)")

    def on_delay_slider_changed(self, value):
        delay_sec = value / 1000.0
        self.typer.delay = delay_sec
        cps = 1.0 / delay_sec if delay_sec > 0 else 0
        self.lbl_delay_val.setText(f"{value} ms (~{cps:.0f} cps)")
        self.lbl_cps.setText(f"Speed: ~{cps:.0f} chars/s")

    def on_countdown_changed(self, value):
        self.typer.countdown_seconds = float(value)

    def on_start_toggle_clicked(self):
        self.typer.set_custom_text(self.editor.toPlainText())
        self.typer.toggle()

    def on_cancel_clicked(self):
        self.typer.cancel()

    def on_preset_selected(self, index):
        presets = {
            1: "def hello():\n    print(\"Hello, World!\")\n\nhello()\n",
            2: "def fibonacci(n):\n    a, b = 0, 1\n    for _ in range(n):\n        yield a\n        a, b = b, a + b\n\nprint(list(fibonacci(10)))\n",
            3: "# Project Architecture\n\n- Dual-Engine Backend (Linux + Windows)\n- Low-Latency Keystroke Injection\n- Cross-Platform Release\n",
            4: "CREATE TABLE users (\n    id SERIAL PRIMARY KEY,\n    username VARCHAR(50) NOT NULL UNIQUE,\n    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP\n);\n",
            5: "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.\n",
        }
        if index in presets:
            self.editor.setPlainText(presets[index])

    def open_file_dialog(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Open Text File", "", "Text Files (*.txt *.py *.md *.json *.sh *.cpp *.c);;All Files (*)")
        if path:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    self.editor.setPlainText(f.read())
                self.file_path = path
                self.typer.file_path = path
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "Error", f"Failed to open file: {e}")

    def save_file_dialog(self):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save Text File", "", "Text Files (*.txt);;All Files (*)")
        if path:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(self.editor.toPlainText())
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "Error", f"Failed to save file: {e}")

    def save_to_default_file(self):
        try:
            with open(DEFAULT_FILE, "w", encoding="utf-8") as f:
                f.write(self.editor.toPlainText())
            QtWidgets.QMessageBox.information(self, "Saved", f"Successfully synced to {DEFAULT_FILE}")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", f"Failed to write default file: {e}")

    def clear_text(self):
        self.editor.clear()

    def update_ui_state(self, state: str):
        if state == "STOPPED":
            self.lbl_status.setText("STOPPED")
            self.lbl_status.setStyleSheet("background-color: #45475a; color: #cdd6f4;")
            self.btn_start.setText("START TYPING")
            self.btn_start.setStyleSheet("")
            self.progress_bar.setValue(0)
        elif state == "COUNTDOWN":
            self.lbl_status.setText(f"STARTING IN {self.typer.countdown_seconds}s...")
            self.lbl_status.setStyleSheet("background-color: #f9e2af; color: #11111b;")
            self.btn_start.setText("PAUSE")
        elif state == "RUNNING":
            self.lbl_status.setText("TYPING ACTIVE")
            self.lbl_status.setStyleSheet("background-color: #a6e3a1; color: #11111b;")
            self.btn_start.setText("PAUSE")
        elif state == "PAUSED":
            self.lbl_status.setText("PAUSED")
            self.lbl_status.setStyleSheet("background-color: #89dceb; color: #11111b;")
            self.btn_start.setText("RESUME")
        elif state == "RESUMING":
            self.lbl_status.setText("RESUMING...")
            self.lbl_status.setStyleSheet("background-color: #fab387; color: #11111b;")

    def update_countdown_label(self, rem: float):
        if self.typer.state == "COUNTDOWN":
            self.lbl_status.setText(f"STARTING IN {rem:.1f}s...")

    def update_progress(self, current: int, total: int, ch: str):
        pct = int((current / total) * 100) if total > 0 else 0
        self.progress_bar.setValue(pct)
        self.lbl_chars.setText(f"Chars: {current} / {total} ({pct}%)")


def run_gui(file_path=DEFAULT_FILE):
    if sys.platform.startswith("linux"):
        os.environ.setdefault("QT_XCB_GL_INTEGRATION", "none")
    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName("AutoTyper")
    window = MainWindow(file_path=file_path)
    window.show()
    sys.exit(app.exec_())
