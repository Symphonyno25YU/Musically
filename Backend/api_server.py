"""Local HTTP API used by the Music Switcher browser interface.

The server intentionally listens only on loopback so it can control Apple
Music on this Mac without exposing the automation controls to the network.
"""

import json
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from Sync_library import get_playlist_tracks


HOST = "127.0.0.1"
PORT = 8000
BACKEND_DIRECTORY = Path(__file__).resolve().parent
player_process = None


def player_is_running():
    """Return whether the context-aware player subprocess is still running."""
    return player_process is not None and player_process.poll() is None


def pause_apple_music():
    """Pause Music after stopping the context-aware player monitor."""
    subprocess.run(
        ["osascript", "-e", 'tell application "Music" to pause'],
        capture_output=True,
        text=True,
        check=False,
    )


def stop_player():
    """Stop the active player process, if any, and pause Apple Music."""
    global player_process

    if player_is_running():
        player_process.terminate()
        try:
            player_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            player_process.kill()
            player_process.wait(timeout=5)

    player_process = None
    pause_apple_music()


def start_player(playlist_name):
    """Start a fresh context-aware player process for ``playlist_name``."""
    global player_process

    # Validate before reporting success or interrupting an existing session.
    if not get_playlist_tracks(playlist_name):
        raise ValueError(f'Apple Music playlist "{playlist_name}" contains no readable tracks.')
    stop_player()
    player_process = subprocess.Popen(
        [sys.executable, "playMusicofGenre.py", playlist_name],
        cwd=BACKEND_DIRECTORY,
    )


class MusicSwitcherRequestHandler(BaseHTTPRequestHandler):
    """Handle browser requests for local playback control."""

    def send_json(self, status_code, payload):
        response = json.dumps(payload).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(response)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(response)

    def read_json_body(self):
        try:
            content_length = int(self.headers.get("Content-Length", 0))
        except ValueError:
            raise ValueError("Content-Length must be a number.") from None

        if content_length > 10_000:
            raise ValueError("Request body is too large.")

        try:
            return json.loads(self.rfile.read(content_length) or b"{}")
        except json.JSONDecodeError:
            raise ValueError("Request body must contain valid JSON.") from None

    def do_OPTIONS(self):
        self.send_json(204, {})

    def do_GET(self):
        if self.path == "/api/status":
            self.send_json(200, {"running": player_is_running()})
            return

        self.send_json(404, {"error": "Endpoint not found."})

    def do_POST(self):
        try:
            payload = self.read_json_body()
        except ValueError as error:
            self.send_json(400, {"error": str(error)})
            return

        if self.path == "/api/play":
            playlist_name = payload.get("playlist", "")
            if not isinstance(playlist_name, str) or not playlist_name.strip():
                self.send_json(400, {"error": "A playlist name is required."})
                return

            try:
                start_player(playlist_name.strip())
            except ValueError as error:
                self.send_json(400, {"error": str(error)})
                return
            except RuntimeError as error:
                self.send_json(502, {"error": str(error)})
                return
            except OSError as error:
                self.send_json(500, {"error": f"Could not start the player: {error}"})
                return

            self.send_json(
                202,
                {
                    "message": "Music Switcher started.",
                    "playlist": playlist_name.strip(),
                    "running": True,
                },
            )
            return

        if self.path == "/api/stop":
            try:
                stop_player()
            except OSError as error:
                self.send_json(500, {"error": f"Could not stop the player: {error}"})
                return

            self.send_json(200, {"message": "Music Switcher stopped.", "running": False})
            return

        self.send_json(404, {"error": "Endpoint not found."})

    def log_message(self, format_string, *args):
        """Keep normal browser requests out of the terminal output."""


def run_server(host=HOST, port=PORT):
    """Run the loopback-only API server until interrupted."""
    server = ThreadingHTTPServer((host, port), MusicSwitcherRequestHandler)
    print(f"Music Switcher API is running at http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping Music Switcher API.")
    finally:
        stop_player()
        server.server_close()


if __name__ == "__main__":
    run_server()