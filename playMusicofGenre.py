import json
import random
import subprocess
import time
from pathlib import Path

from test_chrome_url import get_current_chrome_context


LIBRARY_PATH = Path(__file__).resolve().parent / "library" / "music_genre.json"

ALLOWED_KEYWORDS = {
    "workstudy",
    "creativity",
    "deepthinking",
    "relaxation",
    "intense",
}

    
# Given the KeyWords(The Scene), automatically play a song the that library. 
def play_song_for_keyword(keyword=None):
    """Choose and play a song from the matching collab playlist category."""

    with LIBRARY_PATH.open(encoding="utf-8") as file:
        music_library = json.load(file)

    # None or "none" means choose a random category.
    if keyword is None or (
        isinstance(keyword, str) and keyword.strip().casefold() == "none"
    ):
        available_keywords = [
            name for name, songs in music_library.items() if songs
        ]

        if not available_keywords:
            print("No non-empty categories found.")
            return None

        keyword = random.choice(available_keywords)
    else:
        keyword = keyword.strip().casefold()

        if keyword not in ALLOWED_KEYWORDS:
            print(f'Unknown keyword: "{keyword}"')
            return None

    songs = music_library.get(keyword, [])

    if not songs:
        print(f'No songs found for "{keyword}".')
        return None

    song_name = random.choice(songs)

    script = '''
    on run argv
        set songName to item 1 of argv

        tell application "Music"
            if not (exists playlist "collab") then
                return "PLAYLIST_NOT_FOUND"
            end if

            set matchingTracks to (every track of playlist "collab" whose name is songName)

            if (count of matchingTracks) is 0 then
                return "NOT_FOUND"
            end if

            play (item 1 of matchingTracks)
            return "PLAYING"
        end tell
    end run
    '''

    result = subprocess.run(
        ["osascript", "-e", script, "--", song_name],
        capture_output=True,
        text=True,
    )

    status = result.stdout.strip()

    if result.returncode != 0:
        print("Apple Music error:", result.stderr.strip())
        return None

    if status == "PLAYLIST_NOT_FOUND":
        print('Apple Music playlist "collab" was not found.')
        return None

    if status == "NOT_FOUND":
        print(f'"{song_name}" was not found in "collab".')
        return None

    print(f'Playing "{song_name}" from "{keyword}".')
    return song_name


def main():

    previous_url = None
    print("Monitoring Chrome. Press Control+C to stop.")

    try:
        while True:
            current_url, category = get_current_chrome_context()

            # Runs on every URL change, even if the category stays the same.
            if current_url and current_url != previous_url:
                previous_url = current_url
                print(f"Chrome changed: {current_url}")
                print(f"Category: {category}")
                play_song_for_keyword(category)

            time.sleep(2)

    except KeyboardInterrupt:
        print("\nStopped monitoring.")


if __name__ == "__main__":
    main()