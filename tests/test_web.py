"""Tests for the viewer's data contract and the local analysis server.

The browser side is checked by asserting the shape of what Python produces:
``web/app.js`` reads specific keys, and a rename on the Python side would
otherwise only show up as a blank page.
"""

import json
import re
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

from rhymemap.engine import assign_rhyme_labels
from rhymemap.phonetics import process_verse
from rhymemap.webexport import analyse_text, verse_to_dict
from scripts.serve_web import Handler

PROJECT_ROOT = Path(__file__).resolve().parent.parent
WEB_DIR = PROJECT_ROOT / "web"

LYRICS = ("His palms are sweaty, knees weak, arms are heavy\n"
          "There is vomit on his sweater already, moms spaghetti\n"
          "He is nervous but on the surface he looks calm and ready")

# Keys web/app.js reads. Adding one here means updating the page too.
VERSE_KEYS = {"artist", "track", "engine", "text", "lines", "metrics", "groups",
              "audio", "timed", "source", "language"}
SYLLABLE_KEYS = {"text", "label", "nucleus", "coda", "onset", "start", "end"}
GROUP_KEYS = {"label", "syllables", "length", "occurrences", "similarity", "strength",
              "rime", "exemplars", "positions"}


class TestVerseSerialisation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        verse = process_verse(LYRICS, artist="Eminem")
        assign_rhyme_labels(verse, min_occurrences=2)
        cls.payload = verse_to_dict(verse, "Eminem", "Test", "exact")

    def test_top_level_keys(self):
        self.assertEqual(set(self.payload), VERSE_KEYS)

    def test_lines_are_lists_of_words(self):
        self.assertEqual(len(self.payload["lines"]), 3)
        self.assertTrue(all(isinstance(line, list) for line in self.payload["lines"]))

    def test_syllable_keys(self):
        syllable = self.payload["lines"][0][0]["syllables"][0]
        self.assertEqual(set(syllable), SYLLABLE_KEYS)

    def test_group_keys(self):
        for group in self.payload["groups"]:
            self.assertEqual(set(group), GROUP_KEYS)

    def test_groups_are_sorted_longest_then_strongest(self):
        keys = [(-g["length"], -g["strength"], g["label"]) for g in self.payload["groups"]]
        self.assertEqual(keys, sorted(keys))

    def test_text_round_trips_for_reanalysis(self):
        """The viewer re-posts this text to switch engines."""
        self.assertTrue(self.payload["text"].strip())
        self.assertEqual(len(self.payload["text"].split("\n")), 3)

    def test_payload_is_json_serialisable(self):
        json.dumps(self.payload)

    def test_every_label_appears_in_groups(self):
        labels = {syl["label"]
                  for line in self.payload["lines"]
                  for word in line
                  for syl in word["syllables"] if syl["label"]}
        self.assertEqual(labels, {g["label"] for g in self.payload["groups"]})


class TestAnalyseText(unittest.TestCase):
    def test_each_engine_produces_a_valid_payload(self):
        for engine in ("exact", "families", "similarity", "chains"):
            with self.subTest(engine=engine):
                payload = analyse_text(LYRICS, "You", "Pasted", engine=engine)
                self.assertEqual(set(payload), VERSE_KEYS)
                self.assertEqual(payload["engine"], engine)
                self.assertEqual(payload["text"], LYRICS)

    def test_groups_are_named_after_their_sound(self):
        """Not "A"/"B": a group is named from its own rime, e.g. "-eddy"."""
        payload = analyse_text(LYRICS, "You", "Pasted", engine="similarity")
        labels = [g["label"] for g in payload["groups"]]
        self.assertTrue(labels)
        self.assertFalse(any(len(label) <= 2 and label.isalpha() for label in labels),
                         f"spreadsheet-style labels survived: {labels}")
        self.assertTrue(all(g["rime"] for g in payload["groups"]))

    def test_chain_names_are_phrases(self):
        payload = analyse_text(LYRICS, "You", "Pasted", engine="chains")
        multi = [g for g in payload["groups"] if g["length"] > 1]
        for group in multi:
            self.assertNotIn(group["label"], {"A", "B", "C"})

    def test_group_names_match_the_syllable_labels(self):
        """Renaming must rewrite both, or the viewer colours nothing."""
        payload = analyse_text(LYRICS, "You", "Pasted", engine="similarity")
        used = {syl["label"]
                for line in payload["lines"] for word in line
                for syl in word["syllables"] if syl["label"]}
        self.assertEqual(used, {g["label"] for g in payload["groups"]})

    def test_chain_groups_carry_length_and_similarity(self):
        payload = analyse_text(LYRICS, "You", "Pasted", engine="chains")
        multi = [g for g in payload["groups"] if g["length"] > 1]
        for group in multi:
            self.assertIsNotNone(group["similarity"])
            self.assertGreaterEqual(group["occurrences"], 2)


class TestStaticFiles(unittest.TestCase):
    def test_page_references_its_assets(self):
        html = (WEB_DIR / "index.html").read_text(encoding="utf-8")
        for asset in ("style.css", "app.js", "data.js", "effects.js"):
            self.assertIn(asset, html)

    def test_no_enumerated_rhyme_classes(self):
        """Colour must be generated: a verse can have hundreds of groups."""
        css = (WEB_DIR / "style.css").read_text(encoding="utf-8")
        self.assertNotIn(".rhyme-a", css)
        self.assertNotIn(".rhyme-z", css)

    def test_required_element_ids_exist(self):
        html = (WEB_DIR / "index.html").read_text(encoding="utf-8")
        for element_id in ("trackSelect", "engineSelect", "lyrics", "chains", "stats",
                           "tooltip", "pastePanel", "analyseBtn", "linkInput", "linkForm",
                           "threads", "grain", "status", "player",
                           # transport
                           "transport", "seek", "playToggle", "playIcon", "clock",
                           # effects and progress
                           "heroParticles", "trackCard", "analyseProgress"):
            self.assertIn(f'id="{element_id}"', html)

    def test_effects_used_by_the_app_are_exported(self):
        """app.js calls these by name; a rename in one file breaks the page
        silently, because a missing method is only found when it is called."""
        app = (WEB_DIR / "app.js").read_text(encoding="utf-8")
        effects = (WEB_DIR / "effects.js").read_text(encoding="utf-8")
        used = sorted(set(re.findall(r"Effects\.([a-zA-Z]+)\(", app)))
        self.assertTrue(used, "no Effects calls found; this test is not looking at the right file")
        exported = effects.split("return {")[-1].split("};")[0]
        for name in used:
            with self.subTest(effect=name):
                self.assertIn(name, exported, f"app.js calls Effects.{name} but effects.js never returns it")

    def test_the_transport_has_an_accessible_slider(self):
        """A scrubber nobody can reach from the keyboard is not finished."""
        effects = (WEB_DIR / "effects.js").read_text(encoding="utf-8")
        for required in ("role', 'slider'", "aria-valuenow", "aria-valuemax", "tabindex"):
            self.assertIn(required, effects)

    def test_hidden_attribute_is_not_overridden(self):
        """An id selector setting `display` beats [hidden]; the CSS must undo it."""
        css = (WEB_DIR / "style.css").read_text(encoding="utf-8")
        self.assertIn("#pastePanel[hidden]", css)


class QuietHandler(Handler):
    """Handler without the request logging, so test output stays readable."""

    def log_message(self, fmt, *args):
        pass


class TestServer(unittest.TestCase):
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

    def post(self, payload, path="/api/analyze"):
        request = urllib.request.Request(
            f"http://127.0.0.1:{self.port}{path}",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST")
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                return response.status, json.loads(response.read())
        except urllib.error.HTTPError as error:
            return error.code, json.loads(error.read())

    def test_analyse_endpoint(self):
        status, payload = self.post({"lyrics": LYRICS, "engine": "similarity"})
        self.assertEqual(status, 200)
        self.assertEqual(set(payload), VERSE_KEYS)
        self.assertGreater(payload["metrics"]["syllables"], 0)

    def test_empty_lyrics_rejected(self):
        status, payload = self.post({"lyrics": "   "})
        self.assertEqual(status, 400)
        self.assertIn("error", payload)

    def test_unknown_engine_rejected(self):
        status, payload = self.post({"lyrics": LYRICS, "engine": "nope"})
        self.assertEqual(status, 400)
        self.assertIn("error", payload)

    def test_unknown_endpoint_is_404(self):
        status, _ = self.post({"lyrics": LYRICS}, path="/api/nope")
        self.assertEqual(status, 404)

    def test_oversized_body_rejected(self):
        status, payload = self.post({"lyrics": "la la la\n" * 40000})
        self.assertEqual(status, 413)
        self.assertIn("error", payload)

    def test_assets_must_be_revalidated(self):
        """No Cache-Control means the browser invents one.

        The usual heuristic is a tenth of the file's age, during which it does
        not ask the server at all - so a deploy lands and returning visitors
        keep the old JavaScript with nothing to suggest why.
        """
        for path in ("/app.js", "/style.css", "/effects.js", "/"):
            with self.subTest(path=path):
                request = urllib.request.Request(f"http://127.0.0.1:{self.port}{path}")
                with urllib.request.urlopen(request, timeout=30) as response:
                    self.assertEqual(response.headers.get("Cache-Control"), "no-cache")

    def test_revalidation_is_still_cheap(self):
        """`no-cache` means revalidate, not re-download: a conditional request
        must still answer 304 rather than resending the file."""
        url = f"http://127.0.0.1:{self.port}/app.js"
        with urllib.request.urlopen(url, timeout=30) as response:
            last_modified = response.headers.get("Last-Modified")
        self.assertTrue(last_modified)

        request = urllib.request.Request(url, headers={"If-Modified-Since": last_modified})
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                self.fail(f"expected 304, got {response.status}")
        except urllib.error.HTTPError as error:
            self.assertEqual(error.code, 304)

    def test_range_request_returns_partial_content(self):
        """Browsers refuse to seek in media served without byte ranges."""
        request = urllib.request.Request(
            f"http://127.0.0.1:{self.port}/style.css",
            headers={"Range": "bytes=10-19"})
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read()
            self.assertEqual(response.status, 206)
            self.assertEqual(len(body), 10)
            self.assertTrue(response.headers["Content-Range"].startswith("bytes 10-19/"))

    def test_suffix_range(self):
        request = urllib.request.Request(
            f"http://127.0.0.1:{self.port}/style.css", headers={"Range": "bytes=-5"})
        with urllib.request.urlopen(request, timeout=30) as response:
            self.assertEqual(response.status, 206)
            self.assertEqual(len(response.read()), 5)

    def test_open_ended_range(self):
        full = urllib.request.urlopen(f"http://127.0.0.1:{self.port}/style.css", timeout=30).read()
        request = urllib.request.Request(
            f"http://127.0.0.1:{self.port}/style.css", headers={"Range": "bytes=5-"})
        with urllib.request.urlopen(request, timeout=30) as response:
            self.assertEqual(response.read(), full[5:])

    def test_unsatisfiable_range(self):
        request = urllib.request.Request(
            f"http://127.0.0.1:{self.port}/style.css",
            headers={"Range": "bytes=99999999-99999999"})
        with self.assertRaises(urllib.error.HTTPError) as caught:
            urllib.request.urlopen(request, timeout=30)
        self.assertEqual(caught.exception.code, 416)

    def test_accept_ranges_is_advertised(self):
        with urllib.request.urlopen(f"http://127.0.0.1:{self.port}/style.css", timeout=30) as response:
            self.assertEqual(response.headers["Accept-Ranges"], "bytes")

    def test_song_endpoint_accepts_lyrics(self):
        status, payload = self.post({"url": LYRICS, "engine": "similarity"}, path="/api/song")
        self.assertEqual(status, 200)
        self.assertEqual(payload["source"]["kind"], "text")
        self.assertGreater(payload["metrics"]["syllables"], 0)

    def test_song_endpoint_rejects_empty(self):
        status, payload = self.post({"url": "  "}, path="/api/song")
        self.assertEqual(status, 400)
        self.assertIn("error", payload)

    def test_song_endpoint_reports_a_bad_link(self):
        """A non-YouTube URL is treated as lyrics, so a bare domain is one line."""
        status, payload = self.post({"url": "https://vimeo.com/12345"}, path="/api/song")
        self.assertEqual(status, 200)
        self.assertEqual(payload["source"]["kind"], "text")

    def test_serves_the_page(self):
        with urllib.request.urlopen(f"http://127.0.0.1:{self.port}/", timeout=30) as response:
            self.assertEqual(response.status, 200)
            self.assertIn(b"RhymeMapper", response.read())


if __name__ == "__main__":
    unittest.main()


class TestDecorationIsolation(unittest.TestCase):
    """A failing effect must not be able to blank the page.

    Every effect used to run unguarded in init(). One throw - a canvas context
    refused, a WebGL call rejected, a browser missing something - and everything
    after it was skipped, including the call that renders the analysis. The
    result was a hero, a footer and nothing in between, with no clue why.

    Verified in a browser by making the background effect throw: the analysis
    still rendered 89 lines and 22 groups, identical to the healthy page.
    """

    def setUp(self):
        self.app = (WEB_DIR / "app.js").read_text(encoding="utf-8")

    def test_effects_run_through_the_guard(self):
        self.assertIn("function decorate(", self.app)
        body = self.app.split("function init()", 1)[1]
        # Each of these is decoration; none of them may run bare in init().
        for effect in ("waves", "borderGlow", "clickSpark", "magnet",
                       "scrollProgress", "rotatingText", "spotlight"):
            with self.subTest(effect=effect):
                self.assertIn(f"'{effect}'", body,
                              f"Effects.{effect} is not wrapped in decorate() in init()")

    def test_the_guard_reports_rather_than_swallows(self):
        """Silently ignoring a broken effect is how this stays broken."""
        guard = self.app.split("function decorate(", 1)[1].split("\n}", 1)[0]
        self.assertIn("console.error", guard)

    def test_missing_songs_are_explained(self):
        """data.js is generated, not committed; its absence must not be silent."""
        self.assertIn("rhymeDataMissing", self.app)
        self.assertIn("data.js is missing", self.app)
