#!/usr/bin/env python3
"""Build standalone AutoTyper executable using PyInstaller."""

import os
import platform
import shutil
import subprocess
import sys


def build():
    print("=" * 60)
    print(f"Building AutoTyper Standalone Executable on {platform.system()} ({platform.machine()})")
    print("=" * 60)

    # Check if pyinstaller is installed
    try:
        import PyInstaller
    except ImportError:
        print("PyInstaller not found. Installing pyinstaller...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
        except subprocess.CalledProcessError:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "--break-system-packages", "pyinstaller"])

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--name=AutoTyper",
        "--onefile",
        "--windowed",
        "--clean",
        "--hidden-import=PyQt5",
        "--hidden-import=pynput",
        "--hidden-import=pynput.keyboard",
        "--hidden-import=pynput.mouse",
    ]

    if sys.platform == "win32":
        cmd.extend([
            "--hidden-import=autotyper.backends.windows",
            "--hidden-import=autotyper.win32_input",
        ])
    elif sys.platform.startswith("linux"):
        cmd.extend([
            "--hidden-import=autotyper.backends.linux_x11",
            "--hidden-import=Xlib",
            "--hidden-import=Xlib.ext.xtest",
        ])

    cmd.append("autotyper.py")

    print(f"Running command: {' '.join(cmd)}")
    result = subprocess.run(cmd)

    if result.returncode == 0:
        dist_dir = os.path.abspath("dist")
        bin_name = "AutoTyper.exe" if sys.platform == "win32" else "AutoTyper"
        output_path = os.path.join(dist_dir, bin_name)
        print("=" * 60)
        print(f"BUILD SUCCESS! Executable created at:\n  {output_path}")
        print("=" * 60)
    else:
        print("Build failed with return code:", result.returncode)
        sys.exit(result.returncode)


if __name__ == "__main__":
    build()
