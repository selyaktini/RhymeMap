"""Tests for song ingestion.

The network call in ``fetch_youtube`` is the only untested line: the sandbox
these were written in blocks youtube.com. Everything it depends on -- URL
parsing, track selection, payload parsing, the assembled Song -- is exercised
here against a stand-in for yt-dlp built from YouTube's real response shapes.
"""

import json
import types
import unittest
from unittest.mock import patch

from rhymemap.sources import (
    Song,
    SourceError,
    explain_failure,
    from_text,
    is_youtube_url,
    load,
    parse_caption_payload,
    parse_youtube_id,
    pick_caption_track,
)

CAPTIONS = {"events": [
    {"tStartMs": 0, "dDurationMs": 1600, "segs": [
        {"utf8": "cat", "tOffsetMs": 0}, {"utf8": " in", "tOffsetMs": 400},
        {"utf8": " the", "tOffsetMs": 800}, {"utf8": " hat", "tOffsetMs": 1200}]},
    {"tStartMs": 2400, "dDurationMs": 1600, "segs": [
        {"utf8": "bat", "tOffsetMs": 0}, {"utf8": " on", "tOffsetMs": 400},
        {"utf8": " the", "tOffsetMs": 800}, {"utf8": " mat", "tOffsetMs": 1200}]},
]}

INFO = {
    "title": "Test Song", "track": "Test Song", "artist": "Test Artist",
    "uploader": "Test Channel", "duration": 210, "thumbnail": "https://img/x.jpg",
    "subtitles": {},
    "automatic_captions": {"en": [{"ext": "vtt", "url": "https://x/vtt"},
                                  {"ext": "json3", "url": "https://x/json3"}]},
}


def fake_yt_dlp(info=None, payload=None, raises=None, seen=None):
    """A stand-in for yt_dlp implementing the surface YouTubeReader uses.

    `raises` makes extraction fail the way yt-dlp does, so client rotation and
    the oEmbed fallback can be exercised. `seen` collects the options each
    attempt was constructed with.
    """
    body = json.dumps(payload if payload is not None else CAPTIONS).encode()

    class FakeYDL:
        def __init__(self, options):
            self.options = options
            self.closed = False
            if seen is not None:
                seen.append(options)

        def extract_info(self, url, download=False):
            if raises is not None:
                raise raises
            return info if info is not None else INFO

        def urlopen(self, url):
            return types.SimpleNamespace(read=lambda: body)

        def close(self):
            self.closed = True

    return types.SimpleNamespace(YoutubeDL=FakeYDL)


def no_lyrics_online(url):
    """An LRCLIB fetcher that finds nothing, so tests never touch the network."""
    return ""


class TestParseYoutubeId(unittest.TestCase):
    VALID = {
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ": "dQw4w9WgXcQ",
        "https://youtu.be/dQw4w9WgXcQ": "dQw4w9WgXcQ",
        "youtube.com/watch?v=dQw4w9WgXcQ&t=42s": "dQw4w9WgXcQ",
        "https://m.youtube.com/watch?v=dQw4w9WgXcQ": "dQw4w9WgXcQ",
        "https://music.youtube.com/watch?v=dQw4w9WgXcQ": "dQw4w9WgXcQ",
        "https://www.youtube.com/shorts/dQw4w9WgXcQ": "dQw4w9WgXcQ",
        "https://www.youtube.com/embed/dQw4w9WgXcQ": "dQw4w9WgXcQ",
        "https://www.youtube.com/live/dQw4w9WgXcQ": "dQw4w9WgXcQ",
        "dQw4w9WgXcQ": "dQw4w9WgXcQ",
    }

    def test_accepts_every_url_shape(self):
        for url, expected in self.VALID.items():
            with self.subTest(url=url):
                self.assertEqual(parse_youtube_id(url), expected)

    def test_rejects_non_youtube(self):
        for url in ("https://vimeo.com/12345", "not a url", "", "https://youtube.com/watch?v=short",
                    "https://example.com/watch?v=dQw4w9WgXcQ"):
            with self.subTest(url=url):
                self.assertIsNone(parse_youtube_id(url))

    def test_is_youtube_url(self):
        self.assertTrue(is_youtube_url("https://youtu.be/dQw4w9WgXcQ"))
        self.assertFalse(is_youtube_url("some pasted lyrics\nsecond line"))


class TestPickCaptionTrack(unittest.TestCase):
    def test_prefers_manual_over_automatic(self):
        info = {"subtitles": {"en": [{"ext": "vtt", "url": "manual"}]},
                "automatic_captions": {"en": [{"ext": "json3", "url": "auto"}]}}
        track, kind, _ = pick_caption_track(info)
        self.assertEqual(kind, "manual")
        self.assertEqual(track["url"], "manual")

    def test_prefers_json3_for_word_timing(self):
        track, _, _ = pick_caption_track(INFO)
        self.assertEqual(track["ext"], "json3")

    def test_falls_back_to_a_regional_variant(self):
        info = {"subtitles": {}, "automatic_captions": {"en-GB": [{"ext": "vtt", "url": "gb"}]}}
        track, _, language = pick_caption_track(info)
        self.assertEqual(language, "en-GB")

    def test_falls_back_to_any_language(self):
        info = {"subtitles": {}, "automatic_captions": {"fr": [{"ext": "vtt", "url": "fr"}]}}
        track, _, language = pick_caption_track(info)
        self.assertEqual(language, "fr")

    def test_no_captions(self):
        track, kind, language = pick_caption_track({"subtitles": {}, "automatic_captions": {}})
        self.assertIsNone(track)
        self.assertEqual((kind, language), ("", ""))


class TestParseCaptionPayload(unittest.TestCase):
    def test_json3(self):
        cues = parse_caption_payload(json.dumps(CAPTIONS), "json3")
        self.assertEqual(cues[0].text, "cat in the hat")

    def test_vtt(self):
        vtt = "WEBVTT\n\n00:00:00.000 --> 00:00:02.000\ncat in the hat\n"
        self.assertEqual(parse_caption_payload(vtt, "vtt")[0].text, "cat in the hat")

    def test_malformed_json3_falls_back_to_vtt_parsing(self):
        self.assertEqual(parse_caption_payload("not json at all", "json3"), [])


class TestFromText(unittest.TestCase):
    def test_wraps_lyrics(self):
        song = from_text("cat in the hat\nbat on the mat")
        self.assertEqual(song.source, "text")
        self.assertEqual(song.line_count, 2)

    def test_rejects_empty(self):
        with self.assertRaises(SourceError):
            from_text("   ")


class TestFetchYoutube(unittest.TestCase):
    def fetch(self, url="https://www.youtube.com/watch?v=dQw4w9WgXcQ", **kwargs):
        from rhymemap.sources import resolve
        with patch("rhymemap.sources.youtube._import_yt_dlp", return_value=fake_yt_dlp(**kwargs)):
            return resolve(url, fetcher=no_lyrics_online)

    def test_builds_a_song(self):
        song = self.fetch()
        self.assertIsInstance(song, Song)
        self.assertEqual(song.title, "Test Song")
        self.assertEqual(song.artist, "Test Artist")
        self.assertEqual(song.video_id, "dQw4w9WgXcQ")
        self.assertEqual(song.source, "youtube")
        self.assertEqual(song.caption_kind, "automatic")
        self.assertEqual(song.duration, 210.0)

    def test_lyrics_and_timings_come_from_one_fetch(self):
        song = self.fetch()
        self.assertIn("cat in the hat", song.lyrics)
        self.assertEqual(len(song.timings), 8)

    def test_topic_suffix_is_stripped_from_the_artist(self):
        info = dict(INFO, artist=None, uploader="Some Artist - Topic")
        self.assertEqual(self.fetch(info=info).artist, "Some Artist")

    def test_rejects_a_non_youtube_url(self):
        with self.assertRaises(SourceError) as caught:
            self.fetch("https://vimeo.com/12345")
        self.assertIn("YouTube", str(caught.exception))

    def test_exhausting_every_source_lists_what_was_tried(self):
        info = dict(INFO, subtitles={}, automatic_captions={})
        with self.assertRaises(SourceError) as caught:
            self.fetch(info=info)
        message = str(caught.exception)
        self.assertIn("Tried:", message)
        self.assertIn("manual captions", message)
        self.assertIn("lrclib", message)

    def test_noise_only_captions_fall_through_rather_than_succeeding(self):
        """[Music] is not lyrics; the chain must carry on to the next source."""
        payload = {"events": [{"tStartMs": 0, "dDurationMs": 500,
                               "segs": [{"utf8": "[Music]", "tOffsetMs": 0}]}]}
        with self.assertRaises(SourceError) as caught:
            self.fetch(payload=payload)
        self.assertIn("Tried:", str(caught.exception))


class TestExplainFailure(unittest.TestCase):
    """yt-dlp reports everything as one DownloadError telling the user to file a
    bug. Almost none of these are bugs."""

    def test_network_failure(self):
        message = explain_failure(
            "ERROR: Unable to download API page: ('Unable to connect to proxy', "
            "OSError('Tunnel connection failed: 403 Forbidden'))")
        self.assertIn("Could not reach YouTube", message)

    def test_private_video(self):
        self.assertIn("private", explain_failure("ERROR: [youtube] X: Private video. Sign in").lower())

    def test_unavailable_video(self):
        self.assertIn("unavailable", explain_failure("ERROR: [youtube] X: Video unavailable").lower())

    def test_age_restriction(self):
        message = explain_failure("ERROR: [youtube] X: Sign in to confirm your age")
        self.assertIn("age-restricted", message)

    def test_geo_block(self):
        message = explain_failure("ERROR: The uploader has not made this video available in your country")
        self.assertIn("region", message)

    def test_unknown_failure_keeps_the_first_line(self):
        message = explain_failure(
            "ERROR: [youtube] X: Brand new failure; please report this issue on "
            "https://github.com/yt-dlp/yt-dlp/issues?q=\nsecond line")
        self.assertIn("Brand new failure", message)

    def test_unknown_failure_drops_the_issue_tracker_boilerplate(self):
        message = explain_failure("ERROR: boom; please report this issue on https://github.com/yt-dlp")
        self.assertNotIn("github.com", message)
        self.assertNotIn("report this issue", message)


class TestLoad(unittest.TestCase):
    def test_routes_lyrics_to_text(self):
        self.assertEqual(load("cat in the hat\nbat on the mat").source, "text")

    def test_routes_a_link_to_youtube(self):
        # lrclib.fetch is substituted as well as yt-dlp: `load` takes no fetcher,
        # and this fixture has no manual captions, so the chain reaches the
        # lyrics lookup. Without this the test really called lrclib.net.
        with patch("rhymemap.sources.youtube._import_yt_dlp", return_value=fake_yt_dlp()), \
             patch("rhymemap.sources.lrclib.fetch", no_lyrics_online):
            self.assertEqual(load("https://youtu.be/dQw4w9WgXcQ").source, "youtube")

    def test_age_restriction_hint_mentions_cookies(self):
        message = explain_failure("ERROR: [youtube] X: Sign in to confirm you are not a bot")
        self.assertIn("RHYMEMAP_COOKIES_FROM_BROWSER", message)


if __name__ == "__main__":
    unittest.main()
