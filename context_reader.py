"""Resolve the current browser tab or foreground app to a music category."""

import json
from pathlib import Path

from Sensor.APPreader import get_frontmost_app
from test_chrome_url import get_current_chrome_context, normalize_name


RULES_PATH = Path(__file__).resolve().parent / "library" / "music_rules.json"
CHROME_APP_NAMES = {"google chrome", "chrome", "chromium"}


def _load_rules():
    with RULES_PATH.open(encoding="utf-8") as file:
        return json.load(file)


def get_current_context():
    """Return ``(description, category)`` for the context active right now.

    Website rules take priority only while Chrome is the foreground app.
    Unknown apps/sites return the configured default category.
    """
    rules = _load_rules()
    app_name = get_frontmost_app()

    if app_name and normalize_name(app_name) in CHROME_APP_NAMES:
        url, website_category = get_current_chrome_context()
        if website_category:
            return url, website_category

    app_categories = {
        normalize_name(name): category
        for name, category in rules["context_rules"]["apps"].items()
    }
    category = app_categories.get(
        normalize_name(app_name) if app_name else "",
        rules.get("default_category"),
    )
    return app_name, category
