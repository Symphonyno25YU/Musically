"""Synchronize Apple Music's `collab` playlist with music_genre.json."""

import json
import re
import subprocess
import time
from pathlib import Path




LIBRARY_PATH = Path(__file__).parent / "library" / "music_genre.json"
PLAYLIST_NAME = "collab"


def genre_to_keyword(genre):
    """Reduce an Apple Music genre to the library's main genre keyword.

    Examples:
        "Chinese Hip-Hop" -> "hiphop"
        "Hip-Hop/Rap"     -> "hiphop"
        "Classical Crossover" -> "classical"
    """
    raw = " ".join(genre.casefold().split())
    compact = re.sub(r"[^a-z0-9]+", "", raw)

    if "hiphop" in compact or re.search(r"\brap\b", raw):
        return "hiphop"
    if re.search(r"r\s*&\s*b", raw) or "rnb" in compact or "soul" in compact:
        return "rnb"
    if "kpop" in compact:
        return "kpop"
    if "classical" in compact:
        return "classical"
    if "alternative" in compact:
        return "alternative"
    if "rock" in compact:
        return "rock"
    if "pop" in compact:
        return "pop"
    if "soundtrack" in compact:
        return "soundtrack"
    if "downtempo" in compact:
        return "downtempo"
    if "dance" in compact:
        return "dance"

    # Keep an unfamiliar genre rather than discarding the song.
    return compact or "unknown"


def get_collab_tracks():
    """Return (song_title, Apple Music genre) pairs from the collab playlist."""
    script = f'''
    tell application "Music"
        set output to ""
        repeat with t in tracks of playlist "{PLAYLIST_NAME}"
            set output to output & (name of t as text) & tab & (genre of t as text) & linefeed
        end repeat
        return output
    end tell
    '''
    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        message = result.stderr.strip() or "Unable to read the collab playlist."
        raise RuntimeError(message)

    tracks = []
    for line in result.stdout.splitlines():
        title, separator, genre = line.partition("\t")
        if separator and title.strip():
            tracks.append((title.strip(), genre.strip()))
    return tracks


def normalize_library(library):
    """Merge existing detailed genre groups into the main-keyword groups."""
    normalized = {}

    for genre, songs in library.items():
        keyword = genre_to_keyword(genre)
        normalized.setdefault(keyword, [])

        for song in songs:
            if song not in normalized[keyword]:
                normalized[keyword].append(song)

    return normalized


def sync_collab_library():
    """Add any songs in `collab` that are not already in the JSON library."""
    with LIBRARY_PATH.open(encoding="utf-8") as file:
        original_library = json.load(file)

    library = normalize_library(original_library)
    added = []

    for title, genre in get_collab_tracks():
        keyword = genre_to_keyword(genre)
        songs = library.setdefault(keyword, [])

        if title not in songs:
            songs.append(title)
            added.append((title, keyword))

    if library != original_library:
        with LIBRARY_PATH.open("w", encoding="utf-8") as file:
            json.dump(library, file, ensure_ascii=False, indent=2)
            file.write("\n")

    return added


def watch_collab_playlist(interval_seconds=5):
    """Continuously check for songs newly added to the collab playlist."""
    print(f'Watching Apple Music playlist "{PLAYLIST_NAME}". Press Control+C to stop.')

    try:
        while True:
            for title, keyword in sync_collab_library():
                print(f'Added "{title}" to the "{keyword}" set.')
            time.sleep(interval_seconds)
    except KeyboardInterrupt:
        print("\nStopped watching.")


if __name__ == "__main__":
    watch_collab_playlist()