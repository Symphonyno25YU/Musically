import json
import subprocess
import time
from pathlib import Path
from urllib.parse import urlparse


def normalize_name(name):
    # Ignore capitalization and normalize extra whitespace.
    return " ".join(name.split()).casefold()

JSON_PATH = Path(__file__).resolve().parent / "library" / "music_rules.json"
with open(JSON_PATH, "r", encoding="utf-8") as file:
    config = json.load(file)

# Read only context_rules -> websites.
website_categories = {
    normalize_name(name): category
    for name, category in config["context_rules"]["websites"].items()
}

def get_chrome_url():
    script = '''
    tell application "Google Chrome"
        if (count of windows) is 0 then
            return "NO_CHROME_WINDOW"
        end if

        return URL of active tab of front window
    end tell
    '''

    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        return None

    url = result.stdout.strip()

    if not url or url == "NO_CHROME_WINDOW":
        return None

    return url


def url_to_keyword(url):
    hostname = urlparse(url).hostname

    if not hostname:
        return None

    labels = hostname.casefold().split(".")

    if labels[0] == "www":
        labels = labels[1:]

    return labels[0] if labels else None


def get_category(keyword):
    if not keyword:
        return None

    keyword = normalize_name(keyword)
    return website_categories.get(keyword)


previous_url = None
current_category = None

try:
    while True:
        current_url = get_chrome_url()

        if current_url != previous_url:
            keyword = (
                url_to_keyword(current_url)
                if current_url
                else None
            )

            current_category = get_category(keyword)
            previous_url = current_url

            # Optional terminal output for testing.
            print(f"{keyword} → {current_category}")

        time.sleep(2)

except KeyboardInterrupt:
    pass