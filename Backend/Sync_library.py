"""Build the five activity song groups from any Apple Music playlist."""

import argparse
import re
import subprocess
import time

from database import CATEGORIES, replace_music_library

# Apple Music genres are free-form. These terms provide a deterministic,
# editable mapping into the application's five activity categories.
GENRE_CATEGORY_TERMS = {
    "workstudy": (
        "classical", "instrumental", "piano", "soundtrack", "score",
        "new age", "study",
    ),
    "creativity": (
        "pop", "k-pop", "kpop", "dance", "electronic", "indie",
        "experimental", "world",
    ),
    "deepthinking": (
        "alternative", "r&b", "rnb", "soul", "blues", "downtempo",
        "jazz",
    ),
    "relaxation": (
        "acoustic", "folk", "country", "ambient", "easy listening",
        "singer/songwriter", "reggae", "chill",
    ),
    "intense": (
        "rock", "metal", "punk", "hip-hop", "hip hop", "hiphop", "rap",
        "trap", "hardcore",
    ),
}


def _normalized_genre(genre):
    return " ".join((genre or "").casefold().split())


def genre_to_categories(genre):
    """Return every activity category matched by an Apple Music genre.

    Commas and semicolons may separate multiple genres. A slash remains part
    of a genre (for example, ``Hip-Hop/Rap``), matching music_rules.json.
    Unrecognized genres are kept in relaxation so every playlist track is
    available to the application.
    """
    parts = [part.strip() for part in re.split(r"[;,]", _normalized_genre(genre))]
    matches = []
    for part in parts:
        for category in CATEGORIES:
            if any(term in part for term in GENRE_CATEGORY_TERMS[category]):
                if category not in matches:
                    matches.append(category)
    return matches or ["relaxation"]


def genre_to_keyword(genre):
    """Backward-compatible single-category genre helper."""
    return genre_to_categories(genre)[0]


def get_playlist_tracks(playlist_name):
    """Return ``(title, genre)`` pairs from an Apple Music playlist."""
    if not isinstance(playlist_name, str) or not playlist_name.strip():
        raise ValueError("playlist_name must be a non-empty string")

    script = '''
    on run argv
        set playlistName to item 1 of argv
        tell application "Music"
            if not (exists playlist playlistName) then
                return "PLAYLIST_NOT_FOUND"
            end if
            set output to ""
            repeat with t in tracks of playlist playlistName
                set output to output & (name of t as text) & tab & (genre of t as text) & linefeed
            end repeat
            return output
        end tell
    end run
    '''
    result = subprocess.run(
        ["osascript", "-e", script, "--", playlist_name.strip()],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        message = result.stderr.strip() or f'Unable to read playlist "{playlist_name}".'
        raise RuntimeError(message)
    if result.stdout.strip() == "PLAYLIST_NOT_FOUND":
        raise ValueError(f'Apple Music playlist "{playlist_name}" was not found.')

    tracks = []
    for line in result.stdout.splitlines():
        title, separator, genre = line.partition("\t")
        if separator and title.strip():
            tracks.append((title.strip(), genre.strip()))
    return tracks


def get_collab_tracks():
    """Backward-compatible wrapper for the original fixed playlist."""
    return get_playlist_tracks("collab")


def build_library(tracks):
    """Classify all tracks into the application's five categories."""
    library = {category: [] for category in CATEGORIES}
    for title, genre in tracks:
        for category in genre_to_categories(genre):
            if title not in library[category]:
                library[category].append(title)
    return library


def sync_playlist_library(playlist_name):
    """Replace the SQLite category index with data from ``playlist_name``."""
    library = build_library(get_playlist_tracks(playlist_name))
    replace_music_library(library)
    return library


def sync_collab_library():
    """Backward-compatible wrapper for callers using ``collab``."""
    return sync_playlist_library("collab")


def watch_playlist(playlist_name, interval_seconds=5):
    """Refresh the local category index when the playlist changes."""
    print(f'Watching Apple Music playlist "{playlist_name}". Press Control+C to stop.')
    previous = None
    try:
        while True:
            library = sync_playlist_library(playlist_name)
            if library != previous:
                count = len({song for songs in library.values() for song in songs})
                print(f"Indexed {count} tracks into five categories.")
                previous = library
            time.sleep(interval_seconds)
    except KeyboardInterrupt:
        print("\nStopped watching.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("playlist", help="Apple Music playlist name from the frontend")
    parser.add_argument("--watch", action="store_true", help="keep the index synchronized")
    args = parser.parse_args()
    if args.watch:
        watch_playlist(args.playlist)
    else:
        sync_playlist_library(args.playlist)


if __name__ == "__main__":
    main()
