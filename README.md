
# Music Switcher

Music Switcher selects Apple Music tracks for what you are doing on your Mac.
It supports five activity categories: work/study, creativity, deep thinking,
relaxation, and intense.

## Playback behavior

- Switching Chrome tabs does **not** interrupt the current song.
- Switching applications does **not** interrupt the current song.
- When the song ends, the program reads the currently active context. If
  Chrome is active it checks the current tab; otherwise it checks the
  foreground application. It then chooses the next song for that category.

## Run

Pass the Apple Music playlist name supplied by the frontend as the first
argument. The playlist is indexed into the five categories before playback:

```sh
python3 playMusicofGenre.py "happy"
```

To build or refresh only the local category index:

```sh
python3 Sync_library.py "happy"
```

Playlist names are passed to Apple Music as arguments rather than inserted
into AppleScript, so names containing quotes and other punctuation are safe.

macOS may ask for Automation permission to control Music and Accessibility


