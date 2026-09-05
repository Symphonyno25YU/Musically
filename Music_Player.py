import subprocess

# @input: Name of a specific Playlist
# This function calls Apple music to play the playlist
def play_playlist(name):
    script = f'''
    tell application "Music" 
        if exists (playlist "{name}") then
            play playlist "{name}"
        else
            return "NOT_FOUND"
        end if
    end tell
    '''
    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True, text=True
    )
    print("stdout:", result.stdout)
    print("stderr:", result.stderr)



play_playlist("Classical")   # ← 输入你库里真实存在的歌单名