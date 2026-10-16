"""Prepare activity-matched music near the end of each playing track."""

import argparse
import random
import subprocess
import time
from dataclasses import dataclass
from urllib.parse import urlparse

from context_reader import get_current_context, is_apple_music_app, is_music_switcher_url
from database import load_music_library
from Sensor.test_chrome_url import get_category, url_to_keyword
from Sync_library import CATEGORIES, sync_playlist_library


ALLOWED_KEYWORDS = set(CATEGORIES)
CATEGORY_ALIASES = {
    "creative": "creativity",
    "relax": "relaxation",
    "deep_thinking": "deepthinking",
}
WAITING_FOR_CONTEXT = object()
SONG_POOLS = {}
LAST_PLAYED = {}
DEFAULT_POLL_SECONDS = 0.25
PREPARE_SECONDS = 2.0
HANDOFF_SECONDS = 0.75


@dataclass(frozen=True) # make the instance immutable after creation.
class PlaybackSelection:
    # Stores information about the song this program chose to play.

    title: str
    track_id: str
    category: str

"""Stores Apple Music's current playback state at one moment in time."""
@dataclass(frozen=True)
class PlayerSnapshot:
  

    state: str
    track_id: str = ""
    title: str = ""
    position: float = 0.0
    duration: float = 0.0



"""Return the best music category for a context keyword.
If the keyword matches a known category and that category has songs, this
returns it. Otherwise, it randomly chooses any category that currently has
songs in the synced music library.
"""

def _choose_category(keyword, music_library):

    normalized = keyword.strip().casefold() if isinstance(keyword, str) else ""
    normalized = CATEGORY_ALIASES.get(normalized, normalized)
    if normalized in ALLOWED_KEYWORDS and music_library.get(normalized):
        return normalized

    available = [name for name in CATEGORIES if music_library.get(name)]
    return random.choice(available) if available else None



"""Choose a song for the given keyword and start it in Apple Music.

    This loads the local genre library, picks a category using the keyword,
    randomly selects a song from that category, then asks Apple Music to play
    that song from the requested playlist. It returns a PlaybackSelection when
    playback starts successfully, or None if something goes wrong.
    """
def _choose_song(playlist_name, category, songs):
    """Draw from a shuffled pool, exhausting it before repeating a song."""
    key = (playlist_name, category)
    songs = list(dict.fromkeys(songs))
    signature = tuple(songs)
    saved_signature, remaining = SONG_POOLS.get(key, (None, []))
    if saved_signature != signature or not remaining:
        remaining = songs.copy()
        random.shuffle(remaining)
        SONG_POOLS[key] = (signature, remaining)

    # Also avoid a repeat across pool resets or overlapping categories.
    last_song = LAST_PLAYED.get(playlist_name)
    if len(songs) > 1 and remaining[-1] == last_song:
        alternative = next(
            (index for index, song in enumerate(remaining) if song != last_song),
            None,
        )
        if alternative is not None:
            remaining[alternative], remaining[-1] = remaining[-1], remaining[alternative]
        else:
            # The only unplayed song was just heard in another category.
            remaining.clear()
            remaining.extend(song for song in songs if song != last_song)
            random.shuffle(remaining)
    return remaining.pop()


def prepare_song_for_keyword(keyword, playlist_name):
    """Choose the next song without sending any playback commands."""

    if not isinstance(playlist_name, str) or not playlist_name.strip():
        raise ValueError("playlist_name must be a non-empty string")

    music_library = load_music_library()

    category = _choose_category(keyword, music_library)
    if category is None:
        print("No songs were found in the five activity categories.")
        return None

    playlist_name = playlist_name.strip()
    song_name = _choose_song(playlist_name, category, music_library[category])
    return PlaybackSelection(song_name, "", category)


def start_song_for_keyword(keyword, playlist_name):
    selection = prepare_song_for_keyword(keyword, playlist_name)
    return play_prepared_song(selection, playlist_name) if selection else None


def play_prepared_song(selection, playlist_name):
    """Start the prepared choice, unless Music is now under manual control."""
    song_name = selection.title
    category = selection.category
    script = '''
    on run argv
        set songName to item 1 of argv
        set playlistName to item 2 of argv
        tell application "System Events"
            set foregroundName to name of first application process whose frontmost is true
        end tell
        if foregroundName is "Music" or foregroundName is "Apple Music" then
            return "WAITING_FOR_CONTEXT"
        end if
        tell application "Music"
            if not (exists playlist playlistName) then
                return "PLAYLIST_NOT_FOUND"
            end if
            set matchingTracks to (every track of playlist playlistName whose name is songName)
            if (count of matchingTracks) is 0 then
                return "TRACK_NOT_FOUND"
            end if
            set selectedTrack to item 1 of matchingTracks
            play selectedTrack with once
            set trackID to ""
            try
                set trackID to persistent ID of selectedTrack as text
            end try
            return "PLAYING" & tab & trackID & tab & (name of selectedTrack as text)
        end tell
    end run
    '''
    result = subprocess.run(
        ["osascript", "-e", script, "--", song_name, playlist_name.strip()],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        print("Apple Music error:", result.stderr.strip())
        return None

    fields = result.stdout.strip().split("\t", 2)
    status = fields[0]
    if status == "WAITING_FOR_CONTEXT":
        return WAITING_FOR_CONTEXT
    if status == "PLAYLIST_NOT_FOUND":
        print(f'Apple Music playlist "{playlist_name}" was not found.')
        return None
    if status == "TRACK_NOT_FOUND":
        print(f'"{song_name}" was not found in "{playlist_name}".')
        return None
    if status != "PLAYING":
        print("Apple Music returned an unexpected response:", result.stdout.strip())
        return None

    track_id = fields[1] if len(fields) > 1 else ""
    title = fields[2] if len(fields) > 2 else song_name
    LAST_PLAYED[playlist_name] = song_name
    print(f'Playing "{title}" from "{category}" in "{playlist_name}".')
    return PlaybackSelection(title=title, track_id=track_id, category=category)


def play_song_for_keyword(keyword=None, playlist_name="collab"):
    """Play a song for a keyword and return only the selected song title.

    This wrapper keeps older code working by calling start_song_for_keyword()
    but returning the title string instead of the full PlaybackSelection object.
    """
    selection = start_song_for_keyword(keyword, playlist_name)
    return selection.title if selection else None


def get_player_snapshot(selection=None):
    """Return Apple Music's current playback state and current track identity.

    The returned PlayerSnapshot includes whether Music is playing, paused,
    stopped, or unknown, plus the current track's persistent ID and title when
    they are available.
    """
    # Check and pause in the same AppleScript invocation: otherwise an unwanted
    # queued track keeps playing throughout foreground-app/Chrome detection.
    script = '''
    on run argv
    set expectedID to item 1 of argv
    set expectedName to item 2 of argv
    tell application "Music"
        set stateText to player state as text
        if stateText is "stopped" then return stateText
        set trackID to ""
        set trackName to ""
        set positionSeconds to 0
        set durationSeconds to 0
        try
            set trackID to persistent ID of current track as text
        end try
        try
            set trackName to name of current track as text
        end try
        try
            set positionSeconds to player position
        end try
        try
            set durationSeconds to duration of current track
        end try
        set unexpectedTrack to false
        if expectedID is not "" and trackID is not "" then
            set unexpectedTrack to trackID is not expectedID
        else if expectedName is not "" and trackName is not "" then
            set unexpectedTrack to trackName is not expectedName
        end if
        if stateText is "playing" and unexpectedTrack then
            -- Do not interfere with manual control while Music is foreground.
            tell application "System Events"
                set foregroundName to name of first application process whose frontmost is true
            end tell
            if foregroundName is not "Music" and foregroundName is not "Apple Music" then
                pause
            end if
        end if
        -- Return the observed state, so the loop still detects the transition.
        return stateText & tab & trackID & tab & trackName & tab & (positionSeconds as text) & tab & (durationSeconds as text)
    end tell
    end run
    '''
    result = subprocess.run(
        [
            "osascript", "-e", script, "--",
            selection.track_id if selection else "",
            selection.title if selection else "",
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return PlayerSnapshot("unknown")

    fields = result.stdout.strip().split("\t")
    try:
        position = float(fields[3].replace(",", ".")) if len(fields) > 3 else 0.0
        duration = float(fields[4].replace(",", ".")) if len(fields) > 4 else 0.0
    except ValueError:
        position, duration = 0.0, 0.0
    return PlayerSnapshot(
        state=fields[0].casefold() if fields and fields[0] else "unknown",
        track_id=fields[1] if len(fields) > 1 else "",
        title=fields[2] if len(fields) > 2 else "",
        position=position,
        duration=duration,
    )


def track_finished(selection, previous_snapshot, current_snapshot):
    """Return whether the selected song ended since the previous poll.

    A tab or application change is intentionally absent from this decision.
    Music may either stop or auto-advance at the end, so both transitions are
    treated as completion. Pausing is not.
    """
    if previous_snapshot.state == "playing" and current_snapshot.state == "stopped":
        return True

    if selection.track_id and current_snapshot.track_id:
        selected_key = selection.track_id
        current_key = current_snapshot.track_id
    else:
        selected_key = selection.title
        current_key = current_snapshot.title
    return bool(
        previous_snapshot.state == "playing"
        and current_snapshot.state == "playing"
        and selected_key
        and current_key
        and current_key != selected_key
    )


def _start_for_current_context(playlist_name, prepare_only=False):
    """Read the user's current context and start a matching song.

    The context reader decides what activity/category the user is currently in,
    and this function passes that category to start_song_for_keyword(). When
    the local Music Switcher browser page is active, it signals that playback
    should wait instead of choosing a random song.
    """
    description, category = get_current_context()
    if is_apple_music_app(description):
        print("Apple Music is foreground. Leaving playback unchanged.")
        return WAITING_FOR_CONTEXT
    if is_music_switcher_url(description):
        print("Music Switcher is open. Waiting for another tab or app before playback.")
        return WAITING_FOR_CONTEXT

    keyword = description
    hostname = urlparse(description or "").hostname
    if hostname:
        keyword = next(
            (label for label in hostname.casefold().split(".")[:-1] if get_category(label)),
            url_to_keyword(description),
        )


    print(f"Current website: {description or 'unknown'}")
    print(f"{keyword or 'unknown'} -> {category or 'random'}")
    if prepare_only:
        return prepare_song_for_keyword(category, playlist_name)
    return start_song_for_keyword(category, playlist_name)


def run_player(playlist_name, poll_seconds=DEFAULT_POLL_SECONDS):
    """Run the main context-aware music loop for the selected playlist.

    First, this syncs the playlist into the local genre library. If the local
    Music Switcher browser page is active, it waits without playing anything
    until the user changes tabs or applications. It then starts a song based on
    the current context. Prepare the next choice with two seconds remaining,
    then hand off near the end instead of waiting for queue advancement.
    """
    sync_playlist_library(playlist_name)
    SONG_POOLS.clear()
    LAST_PLAYED.clear()
    selection = _start_for_current_context(playlist_name)
    try:
        while selection is WAITING_FOR_CONTEXT:
            time.sleep(poll_seconds)
            selection = _start_for_current_context(playlist_name)
    except KeyboardInterrupt:
        print("\nStopped monitoring.")
        return

    if selection is None:
        return

    previous_snapshot = PlayerSnapshot(
        state="playing",
        track_id=selection.track_id,
        title=selection.title,
    )
    print("Monitoring song completion. Press Control+C to stop.")
    prepared = None
    timing_reported = False
    timing_warning_reported = False

    try:
        while True:
            time.sleep(poll_seconds)
            snapshot_started = time.monotonic()
            current_snapshot = get_player_snapshot(selection)
            snapshot_latency = time.monotonic() - snapshot_started
            finished = track_finished(selection, previous_snapshot, current_snapshot)
            remaining = current_snapshot.duration - current_snapshot.position
            timed_playback = (
                not finished
                and current_snapshot.state == "playing"
                and current_snapshot.duration > 0
                and current_snapshot.position >= 0
            )
            if timed_playback and not timing_reported:
                print(
                    f'Track timing: "{selection.title}" '
                    f'{current_snapshot.position:.2f}/{current_snapshot.duration:.2f}s; '
                    f'playback check {snapshot_latency:.2f}s.'
                )
                timing_reported = True
            if (
                not finished and current_snapshot.state == "playing"
                and current_snapshot.duration <= 0 and not timing_warning_reported
            ):
                print("Warning: track duration unavailable; two-second preparation cannot run yet.")
                timing_warning_reported = True
            if timed_playback and remaining > PREPARE_SECONDS:
                # A backward seek invalidates the activity sampled near the end.
                prepared = None
            if timed_playback and 0 <= remaining <= PREPARE_SECONDS and prepared is None:
                print("Preparing next song: about two seconds remaining.")
                prepared = _start_for_current_context(playlist_name, prepare_only=True)

            handoff = (
                timed_playback
                # Allow for the next poll and automation overhead. A fixed
                # 0.3-second window can fall entirely between playback checks.
                and 0 <= remaining <= max(HANDOFF_SECONDS, poll_seconds + 2 * snapshot_latency)
                and isinstance(prepared, PlaybackSelection)
            )
            if finished or handoff:
                if handoff:
                    print(f"Starting prepared song with {remaining:.2f}s reported remaining.")
                if finished and current_snapshot.state == "playing":
                    print(
                        f'Unexpected track advance: "{selection.title}" -> '
                        f'"{current_snapshot.title}". Resolving current activity.'
                    )
                # Reuse the activity sampled near the end. Only resolve it here
                # if preparation was unavailable or automatic control was deferred.
                if isinstance(prepared, PlaybackSelection):
                    next_selection = play_prepared_song(prepared, playlist_name)
                else:
                    next_selection = _start_for_current_context(playlist_name)
                while next_selection is WAITING_FOR_CONTEXT:
                    time.sleep(poll_seconds)
                    next_selection = _start_for_current_context(playlist_name)
                if next_selection is None:
                    # Do not remain stuck monitoring the already finished song.
                    return
                if next_selection is not None:
                    selection = next_selection
                    prepared = None
                    timing_reported = False
                    timing_warning_reported = False
                    current_snapshot = PlayerSnapshot(
                        state="playing",
                        track_id=selection.track_id,
                        title=selection.title,
                    )
            previous_snapshot = current_snapshot
    except KeyboardInterrupt:
        print("\nStopped monitoring.")


def main():
    """Parse command-line arguments and start the context-aware player."""
    parser = argparse.ArgumentParser()
    parser.add_argument("playlist", help="Apple Music playlist name received from the frontend")
    parser.add_argument("--poll-seconds", type=float, default=DEFAULT_POLL_SECONDS)
    args = parser.parse_args()
    try:
        run_player(args.playlist, max(0.1, args.poll_seconds))
    except (ValueError, RuntimeError, OSError) as error:
        parser.exit(1, f"Music Switcher: {error}\n")


if __name__ == "__main__":
    main()
