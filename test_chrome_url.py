import subprocess
import time


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


previous_url = None

print("Monitoring Chrome. Press Control+C to stop.")

while True:
    current_url = get_chrome_url()

    if current_url and current_url != previous_url:
        print("Chrome URL changed:", current_url)
        previous_url = current_url

    time.sleep(2)