import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

import Sync_library
import context_reader
import database
import playMusicofGenre as player


class LibraryTests(unittest.TestCase):
    def test_build_library_always_uses_five_categories(self):
        library = Sync_library.build_library(
            [
                ("Focus", "Classical"),
                ("Energy", "Hip-Hop/Rap"),
                ("Mystery", "Unmapped Genre"),
            ]
        )

        self.assertEqual(tuple(library), Sync_library.CATEGORIES)
        self.assertIn("Focus", library["workstudy"])
        self.assertIn("Energy", library["intense"])
        self.assertIn("Mystery", library["relaxation"])

    @patch("Sync_library.subprocess.run")
    def test_playlist_name_is_passed_as_an_argument(self, run):
        run.return_value = Mock(returncode=0, stdout="Song\tPop\n", stderr="")

        tracks = Sync_library.get_playlist_tracks('happy "mix"')

        self.assertEqual(tracks, [("Song", "Pop")])
        self.assertEqual(run.call_args.args[0][-1], 'happy "mix"')


class DatabaseTests(unittest.TestCase):
    def test_library_round_trip_uses_sqlite(self):
        library = {category: [] for category in database.CATEGORIES}
        library["workstudy"] = ["Focus"]
        library["intense"] = ["Energy"]

        with TemporaryDirectory() as directory:
            database_path = Path(directory) / "music_genre.db"
            with patch.object(database, "DATABASE_PATH", database_path):
                database.replace_music_library(library)
                saved_library = database.load_music_library()

        self.assertEqual(saved_library, library)


class ContextTests(unittest.TestCase):
    @patch("context_reader.get_current_chrome_context")
    @patch("context_reader.get_frontmost_app", return_value="Google Chrome")
    def test_chrome_uses_current_tab_category(self, _app, chrome):
        chrome.return_value = ("https://github.com", "deepthinking")
        self.assertEqual(
            context_reader.get_current_context(),
            ("https://github.com", "deepthinking"),
        )

    @patch("context_reader.get_current_chrome_context")
    @patch("context_reader.get_frontmost_app", return_value="Figma")
    def test_non_chrome_app_uses_app_category(self, _app, chrome):
        self.assertEqual(context_reader.get_current_context(), ("Figma", "creativity"))
        chrome.assert_not_called()


class CompletionTests(unittest.TestCase):
    def setUp(self):
        self.selection = player.PlaybackSelection("First", "id-1", "workstudy")

    def test_same_song_does_not_trigger_switch(self):
        previous = player.PlayerSnapshot("playing", "id-1", "First")
        current = player.PlayerSnapshot("playing", "id-1", "First")
        self.assertFalse(player.track_finished(self.selection, previous, current))

    def test_pause_does_not_trigger_switch(self):
        previous = player.PlayerSnapshot("playing", "id-1", "First")
        current = player.PlayerSnapshot("paused", "id-1", "First")
        self.assertFalse(player.track_finished(self.selection, previous, current))

    def test_auto_advance_triggers_switch(self):
        previous = player.PlayerSnapshot("playing", "id-1", "First")
        current = player.PlayerSnapshot("playing", "id-2", "Second")
        self.assertTrue(player.track_finished(self.selection, previous, current))

    def test_stopping_after_playing_triggers_switch(self):
        previous = player.PlayerSnapshot("playing", "id-1", "First")
        current = player.PlayerSnapshot("stopped")
        self.assertTrue(player.track_finished(self.selection, previous, current))

    @patch("playMusicofGenre.time.sleep")
    @patch("playMusicofGenre.get_player_snapshot")
    @patch("playMusicofGenre.start_song_for_keyword")
    @patch("playMusicofGenre.get_current_context")
    @patch("playMusicofGenre.sync_playlist_library")
    def test_context_is_read_only_at_start_and_after_completion(
        self, _sync, context, start, snapshot, sleep
    ):
        context.side_effect = [("first tab", "workstudy"), ("new app", "creativity")]
        start.side_effect = [
            self.selection,
            player.PlaybackSelection("Second", "id-2", "creativity"),
        ]
        snapshot.side_effect = [
            player.PlayerSnapshot("playing", "id-1", "First"),
            player.PlayerSnapshot("playing", "id-2", "Second"),
        ]
        sleep.side_effect = [None, None, KeyboardInterrupt]

        player.run_player("happy", poll_seconds=0.1)

        self.assertEqual(context.call_count, 2)
        start.assert_any_call("workstudy", "happy")
        start.assert_any_call("creativity", "happy")


if __name__ == "__main__":
    unittest.main()
