"""Configuration constants for AutoTyper."""

import os

# Default file location to read text from:
DEFAULT_FILE = os.path.expanduser("~/autotype_text.txt")

# Fallback text if the file doesn't exist:
FALLBACK_TEXT = """def hello():
    print("Hello, World!")

hello()"""

# Delay between characters in seconds (0.04 = fast, 0.06 = moderate, 0.10 = slow)
CHAR_DELAY = 0.001

# Countdown in seconds before typing starts
COUNTDOWN_SECONDS = 5

PID_FILE = os.path.expanduser("~/.autotyper.pid")

# Spaces per indent level (used when the file uses tabs)
TAB_WIDTH = 4

# After Enter, delete the IDE's auto-inserted indentation so the file's own
# leading whitespace is used instead. Set False if your editor misbehaves.
SMART_INDENT = True

# Slightly vary the delay between keys so typing looks less mechanical.
HUMAN_JITTER = True
