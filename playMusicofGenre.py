import subprocess


def escape_applescript(value):
    return value.replace("\\", "\\\\").replace('"', '\\"')


def play_genre(genre):
    """Play the Apple Music playlist whose name matches the genre."""
    playlist_name = escape_applescript(genre)

    script = f'''
    tell application "Music"
        if exists playlist "{playlist_name}" then
            play playlist "{playlist_name}"
            return "PLAYING"
        else
            return "NOT_FOUND"
        end if
    end tell
    '''

    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print("Apple Music error:", result.stderr.strip())
        return False

    status = result.stdout.strip()

    if status == "NOT_FOUND":
        print(f'Playlist not found: "{genre}"')
        return False

    print(f'Now playing the "{genre}" playlist.')
    return True

