#!/usr/bin/env python3
"""Read the macOS foreground application without changing playback."""

import subprocess
import time


def get_frontmost_app():
    """Return the name of the foreground macOS application."""
    script = (
        'tell application "System Events" to get name of first application '
        "process whose frontmost is true"
    )
    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        return None

    return result.stdout.strip() or None


def main():
    """Print the foreground app every five seconds for manual testing."""
    print("Monitoring the foreground app. Press Control+C to stop.")
    try:
        while True:
            print("Foreground app:", get_frontmost_app())
            time.sleep(5)
    except KeyboardInterrupt:
        print("\nStopped monitoring.")


if __name__ == "__main__":
    main()
