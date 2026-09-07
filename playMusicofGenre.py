import json
import random
import subprocess
import time
from pathlib import Path

from test_chrome_url import get_current_chrome_context, url_to_keyword
from pathlib import Path

LIBRARY_PATH = Path(__file__).parent / "library" / "music_genre.json"

ALLOWED_KEYWORDS = {
    "workstudy",
    "creativity",
    "deepthinking",
    "relaxation",
    "intense",
    "None"
}


def play_song_for_keyword(keyword):
    """Choose a song from a keyword group and play it in 'collab'.

    The JSON file must use the five activity keywords as keys, with a list of
    song names as each value.
    """
    keyword = keyword.strip().casefold()

    if keyword not in ALLOWED_KEYWORDS:
        allowed = ", ".join(sorted(ALLOWED_KEYWORDS))
        raise ValueError(f"Unknown keyword: {keyword}. Use one of: {allowed}")

    with LIBRARY_PATH.open(encoding="utf-8") as file:
        music_library = json.load(file)

    is_random_request = keyword is None or (
        isinstance(keyword, str) and keyword.strip().casefold() == "none"
    )

    if is_random_request:
        available_keywords = [
            library_keyword
            for library_keyword, library_songs in music_library.items()
            if library_songs
        ]
        if not available_keywords:
            print(f"No keyword groups with songs found in {LIBRARY_PATH}.")
            return None
        keyword = random.choice(available_keywords)
    else:
        if not isinstance(keyword, str):
            raise TypeError("keyword must be a string or None")

        keyword = keyword.strip().casefold()
        if keyword not in ALLOWED_KEYWORDS:
            allowed = ", ".join(sorted(ALLOWED_KEYWORDS))
            raise ValueError(f"Unknown keyword: {keyword}. Use one of: {allowed}")


    songs = music_library.get(keyword, [])
    if not songs:
        print(f'No songs found for "{keyword}" in {LIBRARY_PATH}.')
        return None

    

    song_name = random.choice(songs)

    # Passing the song as an osascript argument avoids quote-escaping issues.
    script = f'''
    on run argv
        set songName to item 1 of argv

        tell application "Music"
             if player state is playing then
                return "ALREADY_PLAYING"
            end if

            if not (exists playlist "collab") then
                return "PLAYLIST_NOT_FOUND"
            end if
            set matchingTracks to (every track of playlist "collab" whose name is songName)

            if (count of matchingTracks) is 0 then
                return "NOT_FOUND"
            end if

            set targetTrack to item 1 of matchingTracks
            play targetTrack
            return "PLAYING"
        end tell
    end run
    '''
    result = subprocess.run(
        ["osascript", "-e", script, "--", song_name],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        print("Apple Music error:", result.stderr.strip())
        return None

    if result.stdout.strip() == "ALREADY_PLAYING":
        print("A song is already playing in Apple Music; leaving it unchanged.")
        return None

    if result.stdout.strip() == "NOT_FOUND":
        print(f'Apple Music could not find "{song_name}" in your "collab" library.')
        return None

    print(f'Playing "{song_name}" from the "{keyword}" group.')
    return song_name


def main():
    """Check Chrome every two seconds and play on each detected URL change."""
    previous_url = None
    print("Monitoring Chrome. Press Control+C to stop.")
    try:
        while True:
            current_url, category = get_current_chrome_context()
            if current_url != previous_url:
                previous_url = current_url
                print(f"Current category: {category}")
                play_song_for_keyword(category)
            time.sleep(2)
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":

