"""The server's analysis cache, and the /api/song route.

Resolving a link costs a round trip to YouTube, often another to a lyrics
database, and then the whole phonetic analysis. Switching engine, reloading, or
a second person opening the same link should not pay that again.
"""

from __future__ import annotations

import json
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from unittest.mock import patch

from scripts.serve_web import ANALYSIS_CACHE_SIZE, Handler, cache_clear, cache_get, cache_put
from tests.test_resolver import LRCLIB_SYNCED, fake_yt_dlp, info_with, lrclib_serving

URL = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
OTHER_URL = "https://www.youtube.com/watch?v=aQw4w9WgXcZ"


class QuietHandler(Handler):
    def log_message(self, *args):
        pass


class TestCacheStore(unittest.TestCase):
    def setUp(self):
        cache_clear()

    def tearDown(self):
        cache_clear()

    def test_round_trips(self):
        cache_put(("a", "similarity", 2), {"x": 1})
        self.assertEqual(cache_get(("a", "similarity", 2)), {"x": 1})

    def test_a_miss_is_none(self):
        self.assertIsNone(cache_get(("nothing", "similarity", 2)))

    def test_the_engine_is_part_of_the_key(self):
        """Switching engine must re-analyse, not serve the other engine's result."""
        cache_put(("a", "similarity", 2), {"engine": "similarity"})
        self.assertIsNone(cache_get(("a", "chains", 2)))

    def test_it_is_bounded(self):
        for index in range(ANALYSIS_CACHE_SIZE + 8):
            cache_put((f"v{index}", "similarity", 2), {"n": index})
        self.assertLessEqual(len(_entries()), ANALYSIS_CACHE_SIZE)

    def test_the_oldest_is_evicted_first(self):
        for index in range(ANALYSIS_CACHE_SIZE + 1):
            cache_put((f"v{index}", "similarity", 2), {"n": index})
        self.assertIsNone(cache_get(("v0", "similarity", 2)))
        self.assertIsNotNone(cache_get((f"v{ANALYSIS_CACHE_SIZE}", "similarity", 2)))

    def test_reading_an_entry_keeps_it_alive(self):
        """A song being asked for repeatedly should not be the one evicted."""
        cache_put(("keep", "similarity", 2), {"n": "keep"})
        for index in range(ANALYSIS_CACHE_SIZE - 1):
            cache_put((f"v{index}", "similarity", 2), {"n": index})
            cache_get(("keep", "similarity", 2))
        cache_put(("last", "similarity", 2), {"n": "last"})
        self.assertIsNotNone(cache_get(("keep", "similarity", 2)))


def _entries():
    from scripts.serve_web import _analysis_cache
    return _analysis_cache


class TestSongEndpoint(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), QuietHandler)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def setUp(self):
        cache_clear()

    def tearDown(self):
        cache_clear()

    def post(self, payload):
        request = urllib.request.Request(
            f"http://127.0.0.1:{self.port}/api/song",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                return response.status, json.loads(response.read())
        except urllib.error.HTTPError as error:
            return error.code, json.loads(error.read())

    def faked(self, info=None, body=LRCLIB_SYNCED):
        """Patch both network seams for the duration of a request."""
        module = fake_yt_dlp(info=info if info is not None else info_with())
        return patch("rhymemap.sources.youtube._import_yt_dlp", return_value=module), \
            patch("rhymemap.sources.lrclib.fetch", lrclib_serving(body))

    def test_a_link_resolves_and_analyses(self):
        modules, lyrics = self.faked()
        with modules, lyrics:
            status, payload = self.post({"url": URL, "engine": "similarity"})
        self.assertEqual(status, 200, payload.get("error", "")[:800])
        self.assertEqual(payload["source"]["provider"], "lrclib-synced")
        self.assertTrue(payload["groups"])

    def test_the_second_request_is_served_from_cache(self):
        modules, lyrics = self.faked()
        with modules, lyrics:
            self.post({"url": URL, "engine": "similarity"})

        # No network seams patched at all this time: a cache miss would fail.
        status, payload = self.post({"url": URL, "engine": "similarity"})
        self.assertEqual(status, 200)
        self.assertTrue(payload.get("cached"))

    def test_a_different_engine_is_not_served_from_cache(self):
        modules, lyrics = self.faked()
        with modules, lyrics:
            self.post({"url": URL, "engine": "similarity"})
            status, payload = self.post({"url": URL, "engine": "chains"})
        self.assertEqual(status, 200)
        self.assertFalse(payload.get("cached"))
        self.assertEqual(payload["engine"], "chains")

    def test_a_different_song_is_not_served_from_cache(self):
        modules, lyrics = self.faked()
        with modules, lyrics:
            self.post({"url": URL, "engine": "similarity"})
            status, payload = self.post({"url": OTHER_URL, "engine": "similarity"})
        self.assertEqual(status, 200)
        self.assertFalse(payload.get("cached"))

    def test_an_unresolvable_song_is_422_and_lists_what_was_tried(self):
        modules, lyrics = self.faked(body="")
        with modules, lyrics:
            status, payload = self.post({"url": URL, "engine": "similarity"})
        self.assertEqual(status, 422)
        self.assertIn("Tried:", payload["error"])

    def test_a_failure_is_not_cached(self):
        """Otherwise a transient block would be remembered as a permanent one."""
        modules, lyrics = self.faked(body="")
        with modules, lyrics:
            self.post({"url": URL, "engine": "similarity"})

        modules, lyrics = self.faked()
        with modules, lyrics:
            status, payload = self.post({"url": URL, "engine": "similarity"})
        self.assertEqual(status, 200)

    def test_raw_lyrics_still_work_through_this_route(self):
        status, payload = self.post({"query": "cat in the hat\nbat on the mat",
                                     "engine": "similarity"})
        self.assertEqual(status, 200)
        self.assertEqual(payload["source"]["provider"], "pasted")

    def test_empty_request_rejected(self):
        status, payload = self.post({"url": "   "})
        self.assertEqual(status, 400)
        self.assertIn("error", payload)


if __name__ == "__main__":
    unittest.main()
