
# Music Switcher

Music Switcher selects Apple Music tracks for what you are doing on your Mac.
It supports five activity categories: work/study, creativity, deep thinking,
relaxation, and intense.

## Playback behavior

- Switching Chrome tabs does **not** interrupt the current song.
- Switching applications does **not** interrupt the current song.
- While Apple Music is the foreground app, automatic song selection waits and
  leaves playback unchanged. It resumes selecting when another app is foreground.
- The monitor reads playback position and duration. With about two seconds left,
  it samples the foreground app/Chrome tab and prepares a matching next song.
- The prepared song starts with about 0.75 seconds remaining (or earlier if
  measured automation latency requires a larger margin) to reduce the chance
  of Apple Music advancing its own queue. This may trim the current song's ending;
  polling and automation latency mean timing is approximate, not gapless.
- Songs are drawn from a shuffled pool per category, so all songs get a turn
  before the pool resets. Immediate repeats are avoided when alternatives exist.
- The choice reflects activity sampled near the end, not subsequent changes in
  the final two seconds. Seeking backward clears that prepared choice. If timing
  metadata is unavailable, the monitor falls back to selecting after completion.

## Run the web app

Start both the browser frontend and the local Apple Music backend:

```sh
cd /Users/symphonyno25/Desktop/Music_switcher
python3 start_music_switcher.py
```

Then open `http://127.0.0.1:5500`, enter the exact Apple Music playlist name,
and click **Play**. Press `Control+C` in the terminal to stop both services.

macOS may ask for Automation permission to control Music and Accessibility
permission for context detection.

## Run the backend directly

Pass the Apple Music playlist name supplied by the frontend as the first
argument. The playlist is indexed into the five categories before playback:

```sh
cd /Users/symphonyno25/Desktop/Music_switcher/Backend
python3 playMusicofGenre.py "collab"
```

To build or refresh only the local category index:

```sh
python3 Sync_library.py "collab"
```

Playlist names are passed to Apple Music as arguments rather than inserted
into AppleScript, so names containing quotes and other punctuation are safe.


