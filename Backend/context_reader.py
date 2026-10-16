"""Resolve the current browser tab or foreground app to a music category."""

import json
from pathlib import Path
from urllib.parse import urlparse

from Sensor.APPreader import get_frontmost_app
from Sensor.test_chrome_url import get_current_chrome_context, normalize_name


RULES_PATH = Path(__file__).resolve().parent / "library" / "music_rules.json"
CHROME_APP_NAMES = {"google chrome", "chrome", "chromium"}
APPLE_MUSIC_APP_NAMES = {"music", "apple music"}
MUSIC_SWITCHER_HOST = "127.0.0.1"
MUSIC_SWITCHER_PORT = 5500


def _load_rules():
    with RULES_PATH.open(encoding="utf-8") as file:
        return json.load(file)


def is_music_switcher_url(url):
    """Return whether ``url`` is the locally served Music Switcher page."""
    parsed = urlparse(url or "")
    return (
        parsed.scheme == "http"
        and parsed.hostname == MUSIC_SWITCHER_HOST
        and parsed.port == MUSIC_SWITCHER_PORT
    )


def is_apple_music_app(app_name):
    """Identify Music without confusing a website URL with an app name."""
    return isinstance(app_name, str) and normalize_name(app_name) in APPLE_MUSIC_APP_NAMES


def get_current_context():
    """Return ``(description, category)`` for the context active right now.

    Website rules take priority only while Chrome is the foreground app. The
    local Music Switcher UI deliberately has no category so playback can wait
    until the user switches to a different tab or foreground application.
    Unknown apps/sites return the configured default category.
    """
    rules = _load_rules()
    app_name = get_frontmost_app()

    # Leave manual music control alone instead of using the random fallback.
    if is_apple_music_app(app_name):
        return app_name, None

    if app_name and normalize_name(app_name) in CHROME_APP_NAMES:
        url, website_category = get_current_chrome_context()
        if is_music_switcher_url(url):
            return url, None
        if url:
            return url, website_category or rules.get("default_category")

    app_categories = {
        normalize_name(name): category
        for name, category in rules["context_rules"]["apps"].items()
    }
    category = app_categories.get(
        normalize_name(app_name) if app_name else "",
        rules.get("default_category"),
    )
    return app_name, category
