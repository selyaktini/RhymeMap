"""The LRCLIB lookup.

The network call is one injectable function, so everything around it -- query
building, candidate scoring, the fallback order -- is tested here for real.
Nothing in this file touches the network.
"""

from __future__ import annotations

import json
import unittest
import urllib.parse

from rhymemap.sources.lrclib import (
    Match,
    best_match,
    build_get_url,
    build_search_url,
    lookup,
    normalise,
    score_match,
)

RAP_GOD = {
    "trackName": "Rap God", "artistName": "Eminem", "albumName": "The Marshall Mathers LP 2",
    "duration": 363, "instrumental": False,
    "plainLyrics": "Look, I was gonna go easy on you\nNot to hurt your feelings",
    "syncedLyrics": "[00:12.34]Look, I was gonna go easy on you\n[00:15.10]Not to hurt your feelings",
}


def record(**overrides) -> Match:
    payload = dict(RAP_GOD, **overrides)
    return Match(
        track=payload["trackName"], artist=payload["artistName"], album=payload["albumName"],
        duration=float(payload["duration"]), plain=payload["plainLyrics"],
        synced=payload["syncedLyrics"], instrumental=payload["instrumental"],
    )


def fetcher_for(routes: dict, log: list | None = None):
    """A fetcher that answers by path, so the call order can be asserted."""
    def fetch(url: str) -> str:
        if log is not None:
            log.append(url)
        for needle, body in routes.items():
            if needle in url:
                return body
        return ""
    return fetch


class TestNormalise(unittest.TestCase):
    def test_folds_case_and_punctuation(self):
        self.assertEqual(normalise("HUMBLE."), "humble")
        self.assertEqual(normalise("N.Y. State of Mind"), "n y state of mind")

    def test_collapses_whitespace(self):
        self.assertEqual(normalise("  a   b  "), "a b")

    def test_handles_none(self):
        self.assertEqual(normalise(None), "")


class TestScoring(unittest.TestCase):
    def test_an_exact_match_scores_well(self):
        self.assertGreater(score_match(record(), "Rap God", "Eminem", 363), 0.7)

    def test_a_different_song_scores_zero(self):
        self.assertEqual(score_match(record(), "Lose Yourself", "Eminem"), 0.0)

    def test_a_wrong_artist_still_scores_on_the_title(self):
        """The artist is the field YouTube most often gets wrong."""
        self.assertGreater(score_match(record(), "Rap God", "EminemMusic Channel"), 0.3)

    def test_instrumental_is_disqualified(self):
        self.assertEqual(score_match(record(instrumental=True), "Rap God", "Eminem", 363), 0.0)

    def test_a_wildly_different_duration_is_penalised(self):
        close = score_match(record(), "Rap God", "Eminem", 363)
        far = score_match(record(), "Rap God", "Eminem", 95)
        self.assertLess(far, close)

    def test_a_synced_record_outranks_an_identical_plain_one(self):
        synced = score_match(record(), "Rap God", "Eminem", 363)
        plain = score_match(record(syncedLyrics=""), "Rap God", "Eminem", 363)
        self.assertGreater(synced, plain)

    def test_unknown_duration_does_not_penalise(self):
        self.assertGreater(score_match(record(), "Rap God", "Eminem", 0), 0.5)


class TestBestMatch(unittest.TestCase):
    def test_picks_the_closest_by_duration(self):
        near = record(duration=363)
        far = record(duration=120, albumName="Some Compilation")
        self.assertIs(best_match([far, near], "Rap God", "Eminem", 363), near)

    def test_returns_none_when_nothing_is_close(self):
        self.assertIsNone(best_match([record()], "Totally Different Song", "Someone"))

    def test_returns_none_for_an_empty_list(self):
        self.assertIsNone(best_match([], "Rap God", "Eminem"))


class TestUrls(unittest.TestCase):
    def test_get_url_carries_every_field(self):
        url = build_get_url("Rap God", "Eminem", "MMLP2", 363.4)
        query = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
        self.assertEqual(query["track_name"], ["Rap God"])
        self.assertEqual(query["artist_name"], ["Eminem"])
        self.assertEqual(query["album_name"], ["MMLP2"])
        self.assertEqual(query["duration"], ["363"])

    def test_get_url_omits_an_unknown_duration(self):
        self.assertNotIn("duration", build_get_url("Rap God", "Eminem"))

    def test_search_is_fielded_when_the_artist_is_known(self):
        self.assertIn("track_name=", build_search_url("Rap God", "Eminem"))

    def test_search_is_free_text_without_an_artist(self):
        url = build_search_url("Rap God")
        self.assertIn("q=", url)
        self.assertNotIn("artist_name", url)

    def test_special_characters_are_escaped(self):
        self.assertIn("Bada%24%24", build_search_url("1999", "Joey Bada$$"))


class TestLookup(unittest.TestCase):
    def test_the_exact_endpoint_answers_first(self):
        log: list = []
        found = lookup("Rap God", "Eminem", 363,
                       fetcher=fetcher_for({"/get?": json.dumps(RAP_GOD)}, log))
        self.assertIsNotNone(found)
        self.assertEqual(found.track, "Rap God")
        self.assertEqual(len(log), 1, "a hit on /get must not also run a search")

    def test_falls_back_to_search_when_the_exact_lookup_misses(self):
        """A YouTube duration routinely differs from the release, so /get missing
        is the normal case rather than an error."""
        log: list = []
        found = lookup("Rap God", "Eminem", 999,
                       fetcher=fetcher_for({"/search?": json.dumps([RAP_GOD])}, log))
        self.assertIsNotNone(found)
        self.assertEqual(len(log), 2)
        self.assertIn("/get?", log[0])
        self.assertIn("/search?", log[1])

    def test_drops_the_artist_as_a_last_resort(self):
        """Rescue for an artist field that was really a channel name."""
        log: list = []

        def fetch(url):
            log.append(url)
            # Only the artist-free query finds anything.
            if "/search?" in url and "artist_name" not in url:
                return json.dumps([RAP_GOD])
            return ""

        found = lookup("Rap God", "SomeUploaderChannel", 363, fetcher=fetch)
        self.assertIsNotNone(found)
        self.assertEqual(len(log), 3)

    def test_no_match_anywhere_returns_none(self):
        self.assertIsNone(lookup("Nonexistent", "Nobody", 100, fetcher=fetcher_for({})))

    def test_an_instrumental_is_not_a_match(self):
        body = json.dumps(dict(RAP_GOD, instrumental=True, plainLyrics="", syncedLyrics=""))
        self.assertIsNone(lookup("Rap God", "Eminem", 363, fetcher=fetcher_for({"": body})))

    def test_an_empty_track_name_asks_nothing(self):
        log: list = []
        self.assertIsNone(lookup("", "Eminem", fetcher=fetcher_for({}, log)))
        self.assertEqual(log, [])

    def test_a_404_body_is_not_a_match(self):
        body = json.dumps({"statusCode": 404, "name": "TrackNotFound"})
        self.assertIsNone(lookup("Rap God", "Eminem", fetcher=fetcher_for({"": body})))

    def test_without_an_artist_it_searches_straight_away(self):
        log: list = []
        lookup("Rap God", "", fetcher=fetcher_for({"/search?": json.dumps([RAP_GOD])}, log))
        self.assertEqual(len(log), 1)
        self.assertIn("/search?", log[0])


if __name__ == "__main__":
    unittest.main()
