import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

import Sync_library
import context_reader
import database
import playMusicofGenre as player
from Sensor import test_chrome_url as chrome_reader


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
    @patch("context_reader.get_frontmost_app")
    def test_apple_music_has_no_category_and_does_not_read_chrome(self, app, chrome):
        for name in ("Music", "Apple Music", "  APPLE   MUSIC  "):
            with self.subTest(name=name):
                app.return_value = name
                self.assertEqual(context_reader.get_current_context(), (name, None))
        chrome.assert_not_called()

    @patch("context_reader.get_current_chrome_context")
    @patch("context_reader.get_frontmost_app", return_value="Google Chrome")
    def test_unknown_site_preserves_detected_url(self, _app, chrome):
        chrome.return_value = ("https://example.com/page", None)
        self.assertEqual(
            context_reader.get_current_context(),
            ("https://example.com/page", "others"),
        )

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

    @patch("context_reader.get_current_chrome_context")
    @patch("context_reader.get_frontmost_app", return_value="Google Chrome")
    def test_music_switcher_tab_has_no_playback_category(self, _app, chrome):
        chrome.return_value = ("http://127.0.0.1:5500", None)

        self.assertEqual(
            context_reader.get_current_context(),
            ("http://127.0.0.1:5500", None),
        )


class ChromeReaderTests(unittest.TestCase):
    @patch.object(chrome_reader, "get_chrome_url")
    def test_site_categories_include_subdomains(self, read_url):
        cases = [
            ("https://github.com/project", "deepthinking"),
            ("https://en.wikipedia.org/wiki/Music", "deepthinking"),
            ("https://docs.google.com/document/d/123", "workstudy"),
            ("https://school.instructure.com/courses", None),
            ("https://example.com/", None),
            ("http://127.0.0.1:5500/", None),
        ]
        for url, category in cases:
            with self.subTest(url=url):
                read_url.return_value = url
                self.assertEqual(chrome_reader.get_current_chrome_context(), (url, category))

    @patch.object(chrome_reader.subprocess, "run")
    def test_url_reader_returns_active_tab_url(self, run):
        run.return_value = Mock(returncode=0, stdout="https://github.com/\n", stderr="")
        self.assertEqual(chrome_reader.get_chrome_url(), "https://github.com/")

    @patch.object(chrome_reader.subprocess, "run")
    def test_url_reader_reports_automation_failure(self, run):
        run.return_value = Mock(returncode=1, stdout="", stderr="Not authorized (-1743)")
        with self.assertWarnsRegex(RuntimeWarning, "Not authorized"):
            self.assertIsNone(chrome_reader.get_chrome_url())


class SongSelectionTests(unittest.TestCase):
    def setUp(self):
        player.SONG_POOLS.clear()
        player.LAST_PLAYED.clear()

    def tearDown(self):
        player.SONG_POOLS.clear()
        player.LAST_PLAYED.clear()

    def draw(self, songs, category="workstudy", playlist="mix"):
        song = player._choose_song(playlist, category, songs)
        player.LAST_PLAYED[playlist] = song
        return song

    def test_every_song_plays_before_pool_repeats(self):
        songs = ["First", "Second", "Third"]
        with patch.object(player.random, "shuffle") as shuffle:
            chosen = [self.draw(songs) for _ in songs]
        self.assertEqual(set(chosen), set(songs))
        self.assertEqual(len(set(chosen)), len(songs))
        self.assertEqual(chosen[0], "Third")
        shuffle.assert_called_once()

    def test_pool_reset_does_not_repeat_last_song(self):
        songs = ["First", "Second"]
        with patch.object(player.random, "shuffle", side_effect=lambda pool: pool.reverse()):
            chosen = [self.draw(songs) for _ in range(6)]
        self.assertTrue(all(a != b for a, b in zip(chosen, chosen[1:])))

    def test_single_song_category_can_repeat(self):
        self.assertEqual([self.draw(["Only"]) for _ in range(3)], ["Only"] * 3)

    def test_changed_library_rebuilds_pool(self):
        self.draw(["Old"])
        self.assertEqual(self.draw(["New"]), "New")

    def test_overlapping_categories_do_not_immediately_repeat(self):
        with patch.object(player.random, "shuffle"):
            self.assertEqual(self.draw(["First", "Shared"]), "Shared")
            self.assertEqual(self.draw(["Other", "Shared"], "creativity"), "Other")

    @patch.object(player.subprocess, "run")
    @patch.object(player, "load_music_library", return_value={"workstudy": ["First", "Second"]})
    def test_play_command_stops_after_one_track_and_varies_selection(self, _library, run):
        run.return_value = Mock(returncode=0, stdout="PLAYING\tid-1\tSelected", stderr="")
        with patch.object(player.random, "shuffle"):
            player.start_song_for_keyword("workstudy", 'mix "quoted"')
            player.start_song_for_keyword("workstudy", 'mix "quoted"')

        calls = run.call_args_list
        self.assertIn("play selectedTrack with once", calls[0].args[0][2])
        self.assertEqual(calls[0].args[0][-2:], ["Second", 'mix "quoted"'])
        self.assertEqual(calls[1].args[0][-2:], ["First", 'mix "quoted"'])


class CompletionTests(unittest.TestCase):
    @patch("builtins.print")
    @patch("playMusicofGenre.start_song_for_keyword")
    @patch("playMusicofGenre.get_current_context")
    def test_context_log_shows_keyword_instead_of_url(self, context, start, output):
        cases = [
            ("https://www.reddit.com/r/CLine/submit/", "relaxation", "reddit"),
            ("https://en.wikipedia.org/wiki/Music", "deepthinking", "wikipedia"),
            ("https://docs.google.com/document/d/123", "workstudy", "docs"),
            ("https://www.example.com/private/path", "others", "example"),
            ("Figma", "creativity", "Figma"),
            (None, None, "unknown"),
        ]
        for description, category, keyword in cases:
            with self.subTest(description=description):
                context.return_value = (description, category)
                player._start_for_current_context("mix")
                output.assert_called_with(f"{keyword} -> {category or 'random'}")
                start.assert_called_with(category, "mix")

    def setUp(self):
        self.selection = player.PlaybackSelection("First", "id-1", "workstudy")

    @patch("playMusicofGenre.start_song_for_keyword")
    @patch("playMusicofGenre.get_current_context", return_value=("Music", None))
    def test_apple_music_context_does_not_issue_playback_commands(self, _context, start):
        self.assertIs(player._start_for_current_context("mix"), player.WAITING_FOR_CONTEXT)
        start.assert_not_called()

    @patch("playMusicofGenre.time.sleep")
    @patch("playMusicofGenre.get_player_snapshot")
    @patch("playMusicofGenre.start_song_for_keyword")
    @patch("playMusicofGenre.get_current_context")
    @patch("playMusicofGenre.sync_playlist_library")
    def test_apple_music_waits_at_startup_and_after_completion(
        self, _sync, context, start, snapshot, sleep
    ):
        context.side_effect = [
            ("Music", None),
            ("Figma", "creativity"),
            ("Music", None),
            ("Apple Music", None),
            ("Editor", "workstudy"),
        ]
        start.return_value = self.selection
        snapshot.return_value = player.PlayerSnapshot("stopped")
        sleep.side_effect = [None, None, None, None, KeyboardInterrupt]

        player.run_player("mix")

        self.assertEqual(start.call_count, 2)
        start.assert_any_call("creativity", "mix")
        start.assert_any_call("workstudy", "mix")
        self.assertEqual(context.call_count, 5)

    @patch("playMusicofGenre.sync_playlist_library")
    @patch("playMusicofGenre.get_current_context")
    @patch("playMusicofGenre.start_song_for_keyword")
    @patch("playMusicofGenre.get_player_snapshot")
    @patch("playMusicofGenre.time.sleep")
    def test_completion_waits_on_app_page_until_another_app_is_active(
        self, sleep, snapshot, start, context, sync
    ):
        context.side_effect = [
            ("Figma", "creativity"),
            ("http://127.0.0.1:5500/", None),
            ("Editor", "workstudy"),
        ]
        start.return_value = self.selection
        snapshot.return_value = player.PlayerSnapshot("stopped")
        sleep.side_effect = [None, None, KeyboardInterrupt]

        player.run_player("existing", poll_seconds=0.1)

        self.assertEqual(start.call_count, 2)
        start.assert_any_call("creativity", "existing")
        start.assert_any_call("workstudy", "existing")

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
    def test_stopped_track_reads_latest_context_before_starting_next(
        self, _sync, context, start, snapshot, sleep
    ):
        events = []
        context.side_effect = lambda: events.append("context") or ("Editor", "workstudy")
        start.side_effect = lambda *_: events.append("play") or self.selection
        snapshot.side_effect = lambda: events.append("stopped") or player.PlayerSnapshot("stopped")
        sleep.side_effect = [None, KeyboardInterrupt]

        player.run_player("mix")

        self.assertEqual(events, ["context", "play", "stopped", "context", "play"])
        self.assertEqual(sleep.call_args_list[0].args, (0.25,))

    @patch("playMusicofGenre.time.sleep", return_value=None)
    @patch("playMusicofGenre.get_player_snapshot", return_value=player.PlayerSnapshot("stopped"))
    @patch("playMusicofGenre._start_for_current_context")
    @patch("playMusicofGenre.sync_playlist_library")
    def test_failed_next_selection_exits_instead_of_monitoring_finished_song(
        self, _sync, start, snapshot, _sleep
    ):
        start.side_effect = [self.selection, None]
        player.run_player("mix")
        snapshot.assert_called_once()

    @patch("playMusicofGenre.time.sleep")
    @patch("playMusicofGenre.start_song_for_keyword")
    @patch("playMusicofGenre.get_current_context")
    @patch("playMusicofGenre.sync_playlist_library")
    def test_player_waits_on_music_switcher_tab_before_starting(
        self, _sync, context, start, sleep
    ):
        context.side_effect = [
            ("http://127.0.0.1:5500", None),
            ("https://github.com", "deepthinking"),
        ]
        start.return_value = self.selection
        sleep.side_effect = [None, KeyboardInterrupt]

        player.run_player("happy", poll_seconds=0.1)

        start.assert_called_once_with("deepthinking", "happy")
        self.assertEqual(context.call_count, 2)

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
