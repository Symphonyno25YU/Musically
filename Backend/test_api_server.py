import subprocess
import unittest
import json
import threading
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from unittest.mock import Mock, patch

import api_server


class ApiServerTests(unittest.TestCase):
    def setUp(self):
        api_server.player_process = None

    def tearDown(self):
        api_server.player_process = None

    @patch("api_server.get_playlist_tracks", side_effect=ValueError('Playlist "happy" was not found.'))
    def test_http_returns_missing_playlist_error(self, tracks):
        server = api_server.ThreadingHTTPServer(
            ("127.0.0.1", 0), api_server.MusicSwitcherRequestHandler
        )
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            request = Request(
                f"http://127.0.0.1:{server.server_port}/api/play",
                data=json.dumps({"playlist": "happy"}).encode(),
                headers={"Content-Type": "application/json"},
            )
            with self.assertRaises(HTTPError) as caught:
                urlopen(request, timeout=3)
            self.assertEqual(caught.exception.code, 400)
            self.assertIn("was not found", json.load(caught.exception)["error"])
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)

    @patch("api_server.subprocess.Popen")
    @patch("api_server.stop_player")
    @patch("api_server.get_playlist_tracks", return_value=[("Song", "Pop")])
    def test_start_player_passes_playlist_as_an_argument(self, tracks, stop_player, popen):
        process = Mock()
        popen.return_value = process

        api_server.start_player('happy "mix"')

        stop_player.assert_called_once_with()
        self.assertEqual(
            popen.call_args.args[0],
            [api_server.sys.executable, "playMusicofGenre.py", 'happy "mix"'],
        )
        self.assertEqual(popen.call_args.kwargs["cwd"], api_server.BACKEND_DIRECTORY)
        self.assertIs(api_server.player_process, process)
        tracks.assert_called_once_with('happy "mix"')

    @patch("api_server.subprocess.Popen")
    @patch("api_server.stop_player")
    @patch("api_server.get_playlist_tracks", side_effect=ValueError('Playlist not found.'))
    def test_missing_playlist_does_not_start_or_stop_player(self, tracks, stop, popen):
        with self.assertRaisesRegex(ValueError, "Playlist not found"):
            api_server.start_player("missing")
        stop.assert_not_called()
        popen.assert_not_called()

    @patch("api_server.subprocess.Popen")
    @patch("api_server.stop_player")
    @patch("api_server.get_playlist_tracks", return_value=[])
    def test_empty_playlist_is_rejected(self, tracks, stop, popen):
        with self.assertRaisesRegex(ValueError, "contains no readable tracks"):
            api_server.start_player("empty")
        stop.assert_not_called()
        popen.assert_not_called()

    @patch("api_server.pause_apple_music")
    def test_stop_player_terminates_a_running_process(self, pause_apple_music):
        process = Mock()
        process.poll.return_value = None
        api_server.player_process = process

        api_server.stop_player()

        process.terminate.assert_called_once_with()
        process.wait.assert_called_once_with(timeout=5)
        pause_apple_music.assert_called_once_with()
        self.assertIsNone(api_server.player_process)

    @patch("api_server.pause_apple_music")
    def test_stop_player_kills_a_process_that_does_not_terminate(self, pause_apple_music):
        process = Mock()
        process.poll.return_value = None
        process.wait.side_effect = [subprocess.TimeoutExpired("player", 5), None]
        api_server.player_process = process

        api_server.stop_player()

        process.kill.assert_called_once_with()
        self.assertEqual(process.wait.call_count, 2)
        pause_apple_music.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()