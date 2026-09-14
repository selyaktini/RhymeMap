"""The order sources are tried in, and what happens when each one fails.

This is the behaviour the whole "analyse any song" feature rests on, and none of
it can be checked against the real services from a test suite. So the network is
faked at two seams -- the yt_dlp module and the LRCLIB fetcher -- and everything
between them is exercised for real.

The ordering is a claim about trust, and it is asserted here rather than
described: a human-written synced lyric beats machine transcription of singing,
because ASR mishears rhyme endings specifically and rhyme endings are the one
thing this project measures.
"""

from __future__ import annotations

import json
import types
import unittest
from unittest.mock import patch

from rhymemap.sources import Song, SourceError, resolve
from rhymemap.sources.youtube import client_rounds, cookie_options

URL = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

WORD_CAPTIONS = {"events": [
    {"tStartMs": 0, "dDurationMs": 1600, "segs": [
        {"utf8": "captions", "tOffsetMs": 0}, {"utf8": " in", "tOffsetMs": 400},
        {"utf8": " the", "tOffsetMs": 800}, {"utf8": " hat", "tOffsetMs": 1200}]},
    {"tStartMs": 2400, "dDurationMs": 1600, "segs": [
        {"utf8": "bat", "tOffsetMs": 0}, {"utf8": " on", "tOffsetMs": 400},
        {"utf8": " the", "tOffsetMs": 800}, {"utf8": " mat", "tOffsetMs": 1200}]},
]}

TRACK = [{"ext": "json3", "url": "https://x/json3"}]

LRCLIB_SYNCED = json.dumps({
    "trackName": "Test Song", "artistName": "Test Artist", "albumName": "",
    "duration": 210, "instrumental": False,
    "plainLyrics": "lrclib plain one\nlrclib plain two",
    "syncedLyrics": "[00:01.00]lrclib synced one\n[00:04.00]lrclib synced two",
})

LRCLIB_PLAIN_ONLY = json.dumps({
    "trackName": "Test Song", "artistName": "Test Artist", "albumName": "",
    "duration": 210, "instrumental": False,
    "plainLyrics": "lrclib plain one\nlrclib plain two", "syncedLyrics": "",
})


def info_with(manual=False, automatic=False):
    return {
        "title": "Test Artist - Test Song", "track": "Test Song", "artist": "Test Artist",
        "uploader": "Test Channel", "duration": 210, "thumbnail": "https://img/x.jpg",
        "subtitles": {"en": list(TRACK)} if manual else {},
        "automatic_captions": {"en": list(TRACK)} if automatic else {},
    }


def fake_yt_dlp(info=None, raises=None, fail_times=0, seen=None):
    """Stands in for yt_dlp. `fail_times` fails that many attempts, then succeeds."""
    body = json.dumps(WORD_CAPTIONS).encode()
    state = {"failures": 0}

    class FakeYDL:
        def __init__(self, options):
            self.options = options
            if seen is not None:
                seen.append(options)

        def extract_info(self, url, download=False):
            if raises is not None:
                raise raises
            if state["failures"] < fail_times:
                state["failures"] += 1
                raise RuntimeError("ERROR: Sign in to confirm you're not a bot")
            return info

        def urlopen(self, url):
            return types.SimpleNamespace(read=lambda: body)

        def close(self):
            pass

    return types.SimpleNamespace(YoutubeDL=FakeYDL)


def using(module):
    """Substitute the yt-dlp import, without touching sys.modules."""
    return patch("rhymemap.sources.youtube._import_yt_dlp", return_value=module)


def lrclib_serving(body: str, log: list | None = None):
    def fetch(url: str) -> str:
        if log is not None:
            log.append(url)
        return body
    return fetch


def nothing_online(url: str) -> str:
    return ""


class ChainCase(unittest.TestCase):
    def resolve(self, info=None, lyrics_body="", **kwargs):
        module = fake_yt_dlp(info=info if info is not None else info_with(), **kwargs)
        with using(module):
            return resolve(URL, fetcher=lrclib_serving(lyrics_body) if lyrics_body else nothing_online)


class TestOrdering(ChainCase):
    def test_manual_captions_win(self):
        """A human-written caption track is the best source available."""
        song = self.resolve(info_with(manual=True, automatic=True), lyrics_body=LRCLIB_SYNCED)
        self.assertEqual(song.provider, "captions")
        self.assertEqual(song.caption_kind, "manual")
        self.assertIn("captions in the hat", song.lyrics)
        self.assertEqual(song.sync, "word")

    def test_lrclib_synced_beats_automatic_captions(self):
        """Machine transcription of singing mishears exactly what we measure."""
        song = self.resolve(info_with(automatic=True), lyrics_body=LRCLIB_SYNCED)
        self.assertEqual(song.provider, "lrclib-synced")
        self.assertIn("lrclib synced one", song.lyrics)
        self.assertEqual(song.sync, "line")
        self.assertEqual(len(song.lines), 2)

    def test_automatic_captions_used_when_lrclib_has_nothing(self):
        song = self.resolve(info_with(automatic=True))
        self.assertEqual(song.provider, "captions")
        self.assertEqual(song.caption_kind, "automatic")
        self.assertEqual(song.sync, "word")

    def test_plain_lyrics_are_the_last_resort(self):
        song = self.resolve(info_with(), lyrics_body=LRCLIB_PLAIN_ONLY)
        self.assertEqual(song.provider, "lrclib-plain")
        self.assertIn("lrclib plain one", song.lyrics)
        self.assertEqual(song.sync, "none")

    def test_a_song_with_no_captions_anywhere_still_resolves(self):
        """The whole point: captions missing is not the end of the road."""
        song = self.resolve(info_with(), lyrics_body=LRCLIB_SYNCED)
        self.assertTrue(song.lyrics.strip())
        self.assertEqual(song.source, "youtube")


class TestExhaustion(ChainCase):
    def test_every_source_failing_raises(self):
        with self.assertRaises(SourceError):
            self.resolve(info_with())

    def test_the_error_lists_what_was_tried(self):
        with self.assertRaises(SourceError) as caught:
            self.resolve(info_with())
        message = str(caught.exception)
        for expected in ("Tried:", "manual captions", "automatic captions", "lrclib"):
            self.assertIn(expected, message)

    def test_the_error_suggests_pasting(self):
        with self.assertRaises(SourceError) as caught:
            self.resolve(info_with())
        self.assertIn("Pasting the lyrics", str(caught.exception))

    def test_a_non_youtube_link_is_refused_before_any_fetch(self):
        with self.assertRaises(SourceError) as caught:
            resolve("https://vimeo.com/12345")
        self.assertIn("YouTube", str(caught.exception))


class TestBlockedExtraction(unittest.TestCase):
    """When YouTube refuses extraction entirely, oEmbed still names the song --
    and a lyrics database only needs the name."""

    def test_oembed_rescues_the_lookup(self):
        module = fake_yt_dlp(raises=RuntimeError("ERROR: Sign in to confirm you're not a bot"))
        with using(module), \
             patch("rhymemap.sources.probe_oembed",
                   return_value={"title": "Test Artist - Test Song", "uploader": "Test Channel"}):
            song = resolve(URL, fetcher=lrclib_serving(LRCLIB_SYNCED))
        self.assertEqual(song.provider, "lrclib-synced")
        self.assertIn("lrclib synced one", song.lyrics)

    def test_the_block_is_recorded_even_when_recovery_works(self):
        module = fake_yt_dlp(raises=RuntimeError("ERROR: Sign in to confirm you're not a bot"))
        with using(module), \
             patch("rhymemap.sources.probe_oembed",
                   return_value={"title": "Test Artist - Test Song", "uploader": "Test Channel"}):
            song = resolve(URL, fetcher=lrclib_serving(LRCLIB_SYNCED))
        self.assertTrue(any(not attempt.ok for attempt in song.attempts))

    def test_a_total_block_reports_the_youtube_reason(self):
        module = fake_yt_dlp(raises=RuntimeError("ERROR: Private video"))
        with using(module), \
             patch("rhymemap.sources.probe_oembed", return_value={}):
            with self.assertRaises(SourceError) as caught:
                resolve(URL, fetcher=nothing_online)
        self.assertIn("private", str(caught.exception).lower())


class TestClientRotation(unittest.TestCase):
    """YouTube blocks its own clients independently; a refusal for one is often
    served for another."""

    # The rotation reads yt-dlp's own client list, which a stand-in module does
    # not carry, so it is supplied here. That fallback is itself behaviour worth
    # having: an unreadable list means "use yt-dlp's default", never a crash.
    KNOWN = {"tv", "ios", "web_safari", "android", "web"}

    def test_a_blocked_client_is_retried_with_the_next(self):
        seen: list = []
        module = fake_yt_dlp(info=info_with(automatic=True), fail_times=1, seen=seen)
        with using(module), \
             patch("rhymemap.sources.youtube.available_clients", return_value=self.KNOWN):
            song = resolve(URL, fetcher=nothing_online)
        self.assertTrue(song.lyrics.strip())
        self.assertGreaterEqual(len(seen), 2)

    def test_rotation_gives_up_after_every_client(self):
        seen: list = []
        module = fake_yt_dlp(info=info_with(automatic=True), fail_times=99, seen=seen)
        with using(module), \
             patch("rhymemap.sources.youtube.available_clients", return_value=self.KNOWN), \
             patch("rhymemap.sources.probe_oembed", return_value={}):
            with self.assertRaises(SourceError):
                resolve(URL, fetcher=nothing_online)
        self.assertEqual(len(seen), len(client_rounds(known=self.KNOWN)))

    def test_the_default_client_is_tried_first(self):
        seen: list = []
        module = fake_yt_dlp(info=info_with(automatic=True), seen=seen)
        with using(module), \
             patch("rhymemap.sources.youtube.available_clients", return_value=self.KNOWN):
            resolve(URL, fetcher=nothing_online)
        self.assertNotIn("extractor_args", seen[0])

    def test_rounds_drop_clients_this_yt_dlp_does_not_know(self):
        rounds = client_rounds(known={"tv"})
        flattened = [client for attempt in rounds for client in attempt]
        self.assertEqual(set(flattened), {"tv"})

    def test_rounds_survive_an_unrecognisable_yt_dlp(self):
        """If the client list cannot be read, fall back to yt-dlp's own default."""
        self.assertEqual(client_rounds(known=set()), [()])

    def test_the_real_client_list_is_readable(self):
        rounds = client_rounds()
        self.assertGreater(len(rounds), 1, "expected the installed yt-dlp to expose its clients")


class TestCookies(unittest.TestCase):
    """The documented fix for "Sign in to confirm you're not a bot"."""

    def test_browser_cookies_from_the_environment(self):
        options = cookie_options({"RHYMEMAP_COOKIES_FROM_BROWSER": "firefox"})
        self.assertEqual(options["cookiesfrombrowser"], ("firefox", None, None, None))

    def test_a_cookie_file_from_the_environment(self):
        options = cookie_options({"RHYMEMAP_COOKIES": "/tmp/cookies.txt"})
        self.assertEqual(options["cookiefile"], "/tmp/cookies.txt")

    def test_nothing_is_read_by_default(self):
        """Reading a browser's cookie store is the user's decision, not ours."""
        self.assertEqual(cookie_options({}), {})


class TestSongShape(unittest.TestCase):
    def test_sync_reports_the_finest_timing_available(self):
        from rhymemap.sources.lrc import LyricLine
        from rhymemap.timing import WordTiming

        self.assertEqual(Song("t", "a", "x").sync, "none")
        self.assertEqual(Song("t", "a", "x", lines=[LyricLine("x", 0, 1)]).sync, "line")
        self.assertEqual(Song("t", "a", "x", timings=[WordTiming("x", 0, 1)]).sync, "word")


if __name__ == "__main__":
    unittest.main()


class TestEndToEnd(unittest.TestCase):
    """Resolver -> analyser -> viewer payload, with the network faked at both
    seams. This is the path a pasted link actually takes."""

    def analyse(self, info, lyrics_body):
        from rhymemap.webexport import analyse_song

        module = fake_yt_dlp(info=info)
        with using(module):
            song = resolve(URL, fetcher=lrclib_serving(lyrics_body))
        return song, analyse_song(song, engine="similarity")

    def test_a_song_with_no_captions_analyses_from_lrclib(self):
        song, payload = self.analyse(info_with(), LRCLIB_SYNCED)
        self.assertEqual(payload["source"]["provider"], "lrclib-synced")
        self.assertEqual(payload["source"]["sync"], "line")
        self.assertTrue(payload["lines"], "the verse came through with no lines")
        self.assertTrue(payload["groups"], "nothing was labelled")

    def test_line_times_align_one_to_one_with_the_lyric_lines(self):
        """The viewer indexes one by the other, so a drift here desynchronises
        the highlight against the music."""
        song, payload = self.analyse(info_with(), LRCLIB_SYNCED)
        self.assertEqual(len(payload["source"]["line_times"]), len(payload["lines"]))

    def test_line_times_are_ordered_and_forward_going(self):
        _, payload = self.analyse(info_with(), LRCLIB_SYNCED)
        for start, end in payload["source"]["line_times"]:
            self.assertLessEqual(start, end)
        starts = [pair[0] for pair in payload["source"]["line_times"]]
        self.assertEqual(starts, sorted(starts))

    def test_word_timings_still_reach_the_syllables(self):
        _, payload = self.analyse(info_with(manual=True), "")
        self.assertTrue(payload["timed"])
        self.assertEqual(payload["source"]["sync"], "word")

    def test_the_payload_is_json_serialisable(self):
        _, payload = self.analyse(info_with(), LRCLIB_SYNCED)
        json.dumps(payload)

    def test_attempts_are_reported_to_the_viewer(self):
        _, payload = self.analyse(info_with(), LRCLIB_SYNCED)
        providers = [a["provider"] for a in payload["source"]["attempts"]]
        self.assertIn("manual captions", providers)
        self.assertIn("lrclib synced", providers)
