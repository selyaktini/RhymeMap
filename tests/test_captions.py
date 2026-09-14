"""Tests for caption parsing, rolling dedup and line recovery."""

import json
import unittest

from rhymemap.captions import (
    CaptionCue,
    cues_to_verse,
    dedupe_rolling,
    is_noise,
    parse_json3,
    parse_vtt_captions,
    split_lines_by_pauses,
    strip_brackets,
)
from rhymemap.timing import WordTiming


def event(start_ms, duration_ms, *words, step=300):
    return {"tStartMs": start_ms, "dDurationMs": duration_ms,
            "segs": [{"utf8": (" " if i else "") + w, "tOffsetMs": i * step}
                     for i, w in enumerate(words)]}


def timings(spec, intra=0.06, length=0.22):
    """Build word timings from [(line, gap_after), ...]."""
    out, clock = [], 0.0
    for line, gap in spec:
        for word in line.split():
            out.append(WordTiming(word, clock, clock + length))
            clock += length + intra
        clock += gap
    return out


class TestNoiseFiltering(unittest.TestCase):
    def test_recognises_stage_directions(self):
        for text in ("[Music]", "[music]", "[Applause]", "[Laughter]", "  "):
            self.assertTrue(is_noise(text), text)

    def test_lyrics_are_not_noise(self):
        self.assertFalse(is_noise("his palms are sweaty"))

    def test_strip_brackets_inside_a_line(self):
        self.assertEqual(strip_brackets("hello [Music] world").split(), ["hello", "world"])


class TestParseJson3(unittest.TestCase):
    def test_word_level_timings(self):
        cues = parse_json3({"events": [event(1000, 1200, "cat", "hat")]})
        self.assertEqual(len(cues), 1)
        self.assertEqual([w.word for w in cues[0].words], ["cat", "hat"])
        self.assertAlmostEqual(cues[0].words[0].start, 1.0)
        self.assertAlmostEqual(cues[0].words[1].start, 1.3)

    def test_accepts_a_json_string(self):
        payload = json.dumps({"events": [event(0, 600, "cat")]})
        self.assertEqual(parse_json3(payload)[0].text, "cat")

    def test_music_events_are_dropped(self):
        cues = parse_json3({"events": [event(0, 500, "[Music]"), event(500, 500, "cat")]})
        self.assertEqual([c.text for c in cues], ["cat"])

    def test_events_without_segments_are_skipped(self):
        cues = parse_json3({"events": [{"tStartMs": 0}, event(0, 500, "cat")]})
        self.assertEqual(len(cues), 1)

    def test_empty_payload(self):
        self.assertEqual(parse_json3({"events": []}), [])

    def test_word_end_runs_to_the_next_word(self):
        cues = parse_json3({"events": [event(0, 1000, "cat", "hat")]})
        self.assertAlmostEqual(cues[0].words[0].end, cues[0].words[1].start)


class TestParseVttCaptions(unittest.TestCase):
    VTT = ("WEBVTT\n\n"
           "00:00:00.000 --> 00:00:02.000\nhis palms are sweaty\n\n"
           "00:00:02.000 --> 00:00:03.000\n[Music]\n\n"
           "00:00:03.000 --> 00:00:05.000\nknees weak\n")

    def test_parses_cues_and_skips_noise(self):
        cues = parse_vtt_captions(self.VTT)
        self.assertEqual([c.text for c in cues], ["his palms are sweaty", "knees weak"])

    def test_spreads_words_across_the_cue(self):
        words = parse_vtt_captions(self.VTT)[0].words
        self.assertEqual(len(words), 4)
        self.assertAlmostEqual(words[0].start, 0.0)
        self.assertAlmostEqual(words[-1].end, 2.0, places=5)


class TestDedupeRolling(unittest.TestCase):
    """Auto-captions scroll, repeating the tail of the previous cue."""

    def test_removes_the_repeated_prefix(self):
        cues = [CaptionCue("his palms are sweaty"),
                CaptionCue("his palms are sweaty knees weak"),
                CaptionCue("knees weak arms are heavy")]
        self.assertEqual([c.text for c in dedupe_rolling(cues)],
                         ["his palms are sweaty", "knees weak", "arms are heavy"])

    def test_trims_timings_alongside_words(self):
        cues = [CaptionCue("cat hat", [WordTiming("cat", 0, 1), WordTiming("hat", 1, 2)]),
                CaptionCue("cat hat bat", [WordTiming("cat", 2, 3), WordTiming("hat", 3, 4),
                                           WordTiming("bat", 4, 5)])]
        deduped = dedupe_rolling(cues)
        self.assertEqual([c.text for c in deduped], ["cat hat", "bat"])
        self.assertEqual([w.word for w in deduped[1].words], ["bat"])

    def test_keeps_the_first_occurrence_time(self):
        cues = [CaptionCue("cat", [WordTiming("cat", 0.0, 0.5)]),
                CaptionCue("cat hat", [WordTiming("cat", 2.0, 2.5), WordTiming("hat", 2.5, 3.0)])]
        deduped = dedupe_rolling(cues)
        self.assertAlmostEqual(deduped[0].words[0].start, 0.0)

    def test_unrelated_lines_are_untouched(self):
        cues = [CaptionCue("cat hat"), CaptionCue("dog log")]
        self.assertEqual([c.text for c in dedupe_rolling(cues)], ["cat hat", "dog log"])

    def test_matching_is_case_insensitive(self):
        cues = [CaptionCue("Cat Hat"), CaptionCue("cat hat bat")]
        self.assertEqual([c.text for c in dedupe_rolling(cues)], ["Cat Hat", "bat"])

    def test_empty_input(self):
        self.assertEqual(dedupe_rolling([]), [])


class TestSplitLinesByPauses(unittest.TestCase):
    def test_recovers_lines_from_breaths(self):
        spec = [("his palms are sweaty knees weak arms are heavy", 0.55),
                ("there's vomit on his sweater already mom's spaghetti", 0.62),
                ("he is nervous but on the surface he looks calm and ready", 0.0)]
        self.assertEqual(split_lines_by_pauses(timings(spec)), [line for line, _ in spec])

    def test_threshold_adapts_to_a_fast_flow(self):
        """A double-time verse has smaller gaps everywhere, including its breaks."""
        spec = [("rapid fire words with no breath at all", 0.30),
                ("second line of the fast flow now", 0.0)]
        self.assertEqual(split_lines_by_pauses(timings(spec, intra=0.02)), [line for line, _ in spec])

    def test_does_not_strand_single_words(self):
        spec = [("one two three", 0.6), ("four five six", 0.0)]
        for line in split_lines_by_pauses(timings(spec)):
            self.assertGreaterEqual(len(line.split()), 2)

    def test_empty_and_single(self):
        self.assertEqual(split_lines_by_pauses([]), [])
        self.assertEqual(split_lines_by_pauses([WordTiming("cat", 0, 1)]), ["cat"])

    def test_uniform_gaps_produce_one_line(self):
        even = [WordTiming(f"w{i}", i * 0.3, i * 0.3 + 0.25) for i in range(8)]
        self.assertEqual(len(split_lines_by_pauses(even)), 1)


class TestCuesToVerse(unittest.TestCase):
    def test_end_to_end_dedup_and_split(self):
        cues = parse_json3({"events": [
            event(0, 1800, "his", "palms", "are", "sweaty", step=400),
            event(1800, 1800, "his", "palms", "are", "sweaty", step=400),
        ]})
        text, word_timings = cues_to_verse(cues)
        self.assertNotIn("\n", text.strip(), "the repeated cue should not become a second line")
        self.assertEqual(len(word_timings), 4)

    def test_resplit_can_be_disabled(self):
        cues = [CaptionCue("a b", [WordTiming("a", 0, 0.2), WordTiming("b", 0.25, 0.45)]),
                CaptionCue("c d", [WordTiming("c", 2.0, 2.2), WordTiming("d", 2.25, 2.45)])]
        text, _ = cues_to_verse(cues, resplit_lines=False)
        self.assertEqual(text.split("\n"), ["a b", "c d"])

    def test_noise_only_captions_give_empty_text(self):
        text, word_timings = cues_to_verse(parse_json3({"events": [event(0, 500, "[Music]")]}))
        self.assertEqual(text, "")
        self.assertEqual(word_timings, [])


if __name__ == "__main__":
    unittest.main()
