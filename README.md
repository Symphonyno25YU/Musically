
# Music Switcher

Music Switcher selects Apple Music tracks for what you are doing on your Mac.
It supports five activity categories: work/study, creativity, deep thinking,
relaxation, and intense.

## Playback behavior

- Switching Chrome tabs does **not** interrupt the current song.
- Switching applications does **not** interrupt the current song.
- While Apple Music is the foreground app, automatic song selection waits and
  leaves playback unchanged. It resumes selecting when another app is foreground.
- Each selected song plays once and then stops, rather than letting Apple Music
  play its next queued track. A short silent gap may occur during activity detection.
- Songs are drawn from a shuffled pool per category, so all songs get a turn
  before the pool resets. Immediate repeats are avoided when alternatives exist.
- When the song ends, the program reads the currently active context. If
  Chrome is active it checks the current tab; otherwise it checks the
  foreground application. It then chooses the next song for that category.

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


