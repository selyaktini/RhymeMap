"""Parsing LRC, the synced-lyrics format."""

from __future__ import annotations

import unittest

from rhymemap.sources.lrc import LyricLine, is_synced, parse_lrc, to_text

DOC = """[ar:Eminem]
[ti:Rap God]
[00:12.34]Look, I was gonna go easy on you
[00:15.1]Not to hurt your feelings
[00:18.00]
[00:22.50][01:42.00]But I only got one chance
"""


class TestParseLrc(unittest.TestCase):
    def setUp(self):
        self.lines = parse_lrc(DOC, duration=200.0)

    def test_metadata_tags_are_not_lyrics(self):
        for line in self.lines:
            self.assertNotIn("[ar:", line.text)
            self.assertNotIn("Eminem", line.text)

    def test_reads_the_cues(self):
        self.assertEqual(self.lines[0].text, "Look, I was gonna go easy on you")
        self.assertAlmostEqual(self.lines[0].start, 12.34)

    def test_one_digit_fraction_is_tenths(self):
        """[00:15.1] is 15.1 seconds, not 15.01."""
        self.assertAlmostEqual(self.lines[1].start, 15.1)

    def test_end_is_the_next_cue(self):
        self.assertAlmostEqual(self.lines[0].end, 15.1)

    def test_a_blank_cue_closes_the_line_before_it(self):
        """An empty line at 18.00 marks where the previous line stops."""
        self.assertAlmostEqual(self.lines[1].end, 18.0)
        self.assertNotIn("", [line.text for line in self.lines])

    def test_repeated_timestamps_emit_the_line_once_each(self):
        repeats = [line for line in self.lines if line.text == "But I only got one chance"]
        self.assertEqual(len(repeats), 2)
        self.assertAlmostEqual(repeats[0].start, 22.5)
        self.assertAlmostEqual(repeats[1].start, 102.0)

    def test_lines_come_out_in_time_order(self):
        starts = [line.start for line in self.lines]
        self.assertEqual(starts, sorted(starts))

    def test_the_last_line_ends_at_the_track_duration(self):
        self.assertAlmostEqual(self.lines[-1].end, 200.0)

    def test_no_duration_still_gives_the_last_line_an_end(self):
        lines = parse_lrc("[00:10.00]only line")
        self.assertGreater(lines[0].end, lines[0].start)

    def test_colon_fraction_separator(self):
        self.assertAlmostEqual(parse_lrc("[01:02:50]x")[0].start, 62.5)

    def test_no_fraction_at_all(self):
        self.assertAlmostEqual(parse_lrc("[01:02]x")[0].start, 62.0)

    def test_minutes_past_ninety_nine(self):
        self.assertAlmostEqual(parse_lrc("[100:00.00]x")[0].start, 6000.0)

    def test_plain_lyrics_yield_nothing(self):
        self.assertEqual(parse_lrc("just some words\nand more"), [])

    def test_empty_input(self):
        self.assertEqual(parse_lrc(""), [])
        self.assertEqual(parse_lrc(None), [])


class TestHelpers(unittest.TestCase):
    def test_to_text_joins_the_lines(self):
        text = to_text([LyricLine("one", 0.0, 1.0), LyricLine("two", 1.0, 2.0)])
        self.assertEqual(text, "one\ntwo")

    def test_is_synced(self):
        self.assertTrue(is_synced("[00:01.00]hello"))
        self.assertFalse(is_synced("hello"))

    def test_duration_property(self):
        self.assertAlmostEqual(LyricLine("x", 1.0, 3.5).duration, 2.5)

    def test_duration_never_negative(self):
        self.assertEqual(LyricLine("x", 5.0, 1.0).duration, 0.0)


if __name__ == "__main__":
    unittest.main()
