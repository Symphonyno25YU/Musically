import subprocess
import time
from urllib.parse import urlparse


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

    return result.stdout.strip()


def url_to_keyword(url):
    netloc = urlparse(url).netloc.lower()   # 'mail.google.com'
    labels = netloc.split(".")
    if labels and labels[0] == "www":
        labels = labels[1:]
    return labels[0] if labels else None    # 'mail'


previous_url = None

print("Monitoring Chrome. Press Control+C to stop.")

while True:
    current_url = get_chrome_url()

    if current_url and current_url != previous_url:
        keyword = url_to_keyword(current_url)
        print(keyword)
        previous_url = current_url

    time.sleep(2)



