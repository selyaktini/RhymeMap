"""Tests for word-timing parsing and attachment."""

import json
import tempfile
import unittest
from pathlib import Path

from rhymemap.labeling import label_verse
from rhymemap.phonetics import process_verse
from rhymemap.timing import (
    TimingError,
    WordTiming,
    attach_timings,
    load_timings,
    parse_json,
    parse_labels,
    parse_vtt,
    timing_coverage,
)

LYRICS = "cat in the hat\nbat on the mat"


def timings_for(words, step=0.5):
    return [WordTiming(w, i * step, i * step + 0.4) for i, w in enumerate(words)]


class TestWordTiming(unittest.TestCase):
    def test_duration(self):
        self.assertAlmostEqual(WordTiming("cat", 1.0, 1.5).duration, 0.5)

    def test_negative_duration_clamps_to_zero(self):
        self.assertEqual(WordTiming("cat", 2.0, 1.0).duration, 0.0)


class TestParseJson(unittest.TestCase):
    def test_flat_list(self):
        timings = parse_json('[{"word":"cat","start":0,"end":0.4}]')
        self.assertEqual((timings[0].word, timings[0].start, timings[0].end), ("cat", 0.0, 0.4))

    def test_whisperx_style_wrapper(self):
        self.assertEqual(len(parse_json('{"words":[{"word":"cat","start":0,"end":0.4}]}')), 1)

    def test_entries_missing_times_are_skipped(self):
        self.assertEqual(parse_json('[{"word":"cat"},{"word":"hat","start":1,"end":2}]')[0].word, "hat")

    def test_accepts_text_key(self):
        self.assertEqual(parse_json('[{"text":"cat","start":0,"end":1}]')[0].word, "cat")


class TestParseVtt(unittest.TestCase):
    VTT = ("WEBVTT\n\n"
           "00:00:00.000 --> 00:00:00.400\ncat\n\n"
           "00:00:00.500 --> 00:00:00.900\nhat\n")

    def test_parses_cues(self):
        timings = parse_vtt(self.VTT)
        self.assertEqual([t.word for t in timings], ["cat", "hat"])
        self.assertAlmostEqual(timings[1].start, 0.5)

    def test_srt_comma_separator(self):
        timings = parse_vtt("1\n00:00:01,250 --> 00:00:01,750\ncat\n")
        self.assertAlmostEqual(timings[0].start, 1.25)

    def test_minutes_and_hours(self):
        timings = parse_vtt("00:01:02.500 --> 00:01:03.000\ncat\n")
        self.assertAlmostEqual(timings[0].start, 62.5)


class TestParseLabels(unittest.TestCase):
    def test_tab_separated(self):
        timings = parse_labels("0.0\t0.4\tcat\n0.5\t0.9\that\n")
        self.assertEqual([t.word for t in timings], ["cat", "hat"])

    def test_space_separated_fallback(self):
        self.assertEqual(parse_labels("0.0 0.4 cat\n")[0].word, "cat")

    def test_malformed_rows_are_skipped(self):
        self.assertEqual(len(parse_labels("garbage\n0.0\t0.4\tcat\n")), 1)


class TestLoadTimings(unittest.TestCase):
    def test_missing_file(self):
        with self.assertRaises(TimingError):
            load_timings("/nonexistent/timings.json")

    def test_by_extension(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "t.json"
            path.write_text(json.dumps([{"word": "cat", "start": 0, "end": 0.4}]))
            self.assertEqual(len(load_timings(path)), 1)

    def test_unknown_extension_sniffs_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "t.weird"
            path.write_text("0.0\t0.4\tcat\n")
            self.assertEqual(load_timings(path)[0].word, "cat")

    def test_empty_file_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "t.json"
            path.write_text("[]")
            with self.assertRaises(TimingError):
                load_timings(path)


class TestAttachTimings(unittest.TestCase):
    def setUp(self):
        self.verse = process_verse(LYRICS, artist="Test")
        label_verse(self.verse, engine="similarity", min_occurrences=2)

    def test_all_words_matched(self):
        words = [w for line in self.verse.lines for w in line.words]
        matched = attach_timings(self.verse, timings_for([w.text for w in words]))
        self.assertEqual(matched, len(words))
        self.assertAlmostEqual(timing_coverage(self.verse), 1.0)

    def test_syllable_times_are_interpolated(self):
        words = [w for line in self.verse.lines for w in line.words]
        attach_timings(self.verse, timings_for([w.text for w in words]))
        for syl in self.verse.syllables():
            self.assertIsNotNone(syl.start)
            self.assertGreaterEqual(syl.end, syl.start)

    def test_times_are_non_decreasing(self):
        words = [w for line in self.verse.lines for w in line.words]
        attach_timings(self.verse, timings_for([w.text for w in words]))
        starts = [s.start for s in self.verse.syllables()]
        self.assertEqual(starts, sorted(starts))

    def test_extra_timing_words_are_skipped(self):
        """Ad-libs in the alignment must not drag the rest out of step."""
        words = [w.text for line in self.verse.lines for w in line.words]
        noisy = timings_for([words[0], "yeah", *words[1:]])
        matched = attach_timings(self.verse, noisy)
        self.assertEqual(matched, len(words))

    def test_unmatched_words_are_left_untimed(self):
        matched = attach_timings(self.verse, timings_for(["zzz", "qqq"]))
        self.assertEqual(matched, 0)
        self.assertEqual(timing_coverage(self.verse), 0.0)

    def test_no_timings_is_a_no_op(self):
        self.assertEqual(attach_timings(self.verse, []), 0)
        self.assertTrue(all(s.start is None for s in self.verse.syllables()))

    def test_coverage_of_empty_verse(self):
        from rhymemap.models import Verse
        self.assertEqual(timing_coverage(Verse()), 0.0)


if __name__ == "__main__":
    unittest.main()
