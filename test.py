import subprocess

script = '''
tell application "Music"
    set out to ""
    repeat with t in tracks of playlist "collab"
        set out to out & (name of t) & " | " & (genre of t) & "\n"
    end repeat
    return out
end tell
'''
result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
print(result.stdout)
