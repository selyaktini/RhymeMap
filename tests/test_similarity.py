"""Tests for continuous rhyme scoring and similarity clustering."""

import unittest

from rhymemap.models import Line, Syllable, Verse, Word
from rhymemap.similarity import (
    DEFAULT_WEIGHTS,
    assign_similarity_labels,
    cluster_syllables,
    rhyme_key,
    stress_similarity,
    syllable_similarity,
)


def S(nucleus, coda=(), onset=(), terminal=False, text="x"):
    return Syllable(text=text, nucleus=nucleus, coda=list(coda), onset=list(onset), is_terminal=terminal)


def verse_of(rows):
    """Build a verse from [[syllable, ...], ...], one word per line."""
    verse = Verse(metadata={"artist": "Test"})
    for line_id, syllables in enumerate(rows):
        for i, s in enumerate(syllables):
            s.line_id, s.word_id, s.syl_index = line_id, 0, i
        verse.lines.append(Line(text="w", line_id=line_id,
                                words=[Word(text="w", syllables=syllables, line_id=line_id, is_last_word=True)]))
    return verse


class TestStressSimilarity(unittest.TestCase):
    def test_identical_stress(self):
        self.assertEqual(stress_similarity(1, 1, 0.8), 1.0)

    def test_both_stressed_gets_partial_credit(self):
        self.assertEqual(stress_similarity(1, 2, 0.8), 0.8)

    def test_stressed_vs_unstressed(self):
        self.assertEqual(stress_similarity(1, 0, 0.8), 0.0)


class TestSyllableSimilarity(unittest.TestCase):
    def test_perfect_rhyme_scores_one(self):
        self.assertAlmostEqual(syllable_similarity(S("AE1", ["T"], ["K"]), S("AE1", ["T"], ["HH"])), 1.0)

    def test_is_symmetric(self):
        a, b = S("AE1", ["T"], ["K"]), S("IY1", ["N"], ["S"])
        self.assertAlmostEqual(syllable_similarity(a, b), syllable_similarity(b, a))

    def test_stays_in_range(self):
        samples = [S("AE1", ["T"], ["K"]), S("IY1", [], []), S("UW1", ["L", "Z"], ["S", "T"]), S("AH0", ["N"], ["M"])]
        for a in samples:
            for b in samples:
                self.assertGreaterEqual(syllable_similarity(a, b), 0.0)
                self.assertLessEqual(syllable_similarity(a, b), 1.0)

    def test_unrelated_syllables_score_low(self):
        self.assertLess(syllable_similarity(S("AE1", ["T"], ["K"]), S("UW1", ["L"], ["K"])), 0.5)

    def test_slant_rhyme_beats_unrelated(self):
        slant = syllable_similarity(S("AW1", ["D"], ["L"]), S("AW1", ["T"], []))
        unrelated = syllable_similarity(S("AE1", ["T"], ["K"]), S("UW1", ["L"], ["M"]))
        self.assertGreater(slant, unrelated)

    def test_near_rhyme_ranks_between(self):
        perfect = syllable_similarity(S("AE1", ["T"], ["K"]), S("AE1", ["T"], ["HH"]))
        near = syllable_similarity(S("IH1", ["T"], ["B"]), S("IY1", ["T"], ["F"]))
        unrelated = syllable_similarity(S("AE1", ["T"], ["K"]), S("UW1", ["L"], ["M"]))
        self.assertGreater(perfect, near)
        self.assertGreater(near, unrelated)


class TestOnsetPenalty(unittest.TestCase):
    """Identical onset plus identical rime is repetition, not rhyme."""

    def test_repetition_scores_below_a_true_rhyme(self):
        repetition = syllable_similarity(S("AE1", ["T"], ["K"]), S("AE1", ["T"], ["K"]))
        rhyme = syllable_similarity(S("AE1", ["T"], ["K"]), S("AE1", ["T"], ["HH"]))
        self.assertLess(repetition, rhyme)

    def test_penalty_matches_the_configured_weight(self):
        expected = 1.0 - DEFAULT_WEIGHTS["onset_identity_penalty"]
        self.assertAlmostEqual(syllable_similarity(S("AE1", ["T"], ["K"]), S("AE1", ["T"], ["K"])), expected)

    def test_two_empty_onsets_are_not_penalised(self):
        """Vowel-initial syllables share 'no onset', which is not repetition."""
        self.assertAlmostEqual(syllable_similarity(S("AE1", ["T"]), S("AE1", ["T"])), 1.0)

    def test_different_onsets_are_not_penalised(self):
        self.assertAlmostEqual(syllable_similarity(S("AE1", ["T"], ["K"]), S("AE1", ["T"], ["B"])), 1.0)

    def test_penalty_can_be_disabled(self):
        weights = dict(DEFAULT_WEIGHTS, onset_identity_penalty=0.0)
        self.assertAlmostEqual(
            syllable_similarity(S("AE1", ["T"], ["K"]), S("AE1", ["T"], ["K"]), weights), 1.0)


class TestRhymeKey(unittest.TestCase):
    def test_same_sound_gives_same_key(self):
        self.assertEqual(rhyme_key(S("AE1", ["T"], ["K"], text="cat")),
                         rhyme_key(S("AE1", ["T"], ["K"], text="kat")))

    def test_different_coda_gives_different_key(self):
        self.assertNotEqual(rhyme_key(S("AE1", ["T"])), rhyme_key(S("AE1", ["D"])))

    def test_stress_is_part_of_the_key(self):
        self.assertNotEqual(rhyme_key(S("AE1", ["T"])), rhyme_key(S("AE0", ["T"])))


class TestClustering(unittest.TestCase):
    def test_empty_input(self):
        self.assertEqual(cluster_syllables([]), {})

    def test_single_syllable(self):
        assignment = cluster_syllables([S("AE1", ["T"], ["K"])])
        self.assertEqual(len(assignment), 1)

    def test_rhyming_syllables_share_a_cluster(self):
        a, b = S("AE1", ["T"], ["K"]), S("AE1", ["T"], ["HH"])
        assignment = cluster_syllables([a, b])
        self.assertEqual(assignment[rhyme_key(a)], assignment[rhyme_key(b)])

    def test_unrelated_syllables_split(self):
        a, b = S("AE1", ["T"], ["K"]), S("UW1", ["L"], ["M"])
        assignment = cluster_syllables([a, b])
        self.assertNotEqual(assignment[rhyme_key(a)], assignment[rhyme_key(b)])

    def test_threshold_controls_granularity(self):
        syllables = [S("AE1", ["T"], ["K"]), S("EH1", ["T"], ["B"]), S("UW1", ["L"], ["M"])]
        loose = len(set(cluster_syllables(syllables, threshold=0.5).values()))
        strict = len(set(cluster_syllables(syllables, threshold=0.99).values()))
        self.assertLessEqual(loose, strict)


class TestAssignSimilarityLabels(unittest.TestCase):
    def test_empty_verse(self):
        self.assertEqual(len(assign_similarity_labels(Verse()).mapping), 0)

    def test_rhyming_lines_get_the_same_label(self):
        verse = verse_of([[S("AE1", ["T"], ["K"], terminal=True)],
                          [S("AE1", ["T"], ["HH"], terminal=True)],
                          [S("AE1", ["T"], ["B"], terminal=True)]])
        assign_similarity_labels(verse, min_occurrences=2)
        labels = [s.rhyme_label for s in verse.syllables()]
        self.assertTrue(all(labels))
        self.assertEqual(len(set(labels)), 1)

    def test_min_occurrences_filters_singletons(self):
        verse = verse_of([[S("AE1", ["T"], ["K"], terminal=True)],
                          [S("UW1", ["L"], ["M"], terminal=True)]])
        assign_similarity_labels(verse, min_occurrences=2)
        self.assertTrue(all(s.rhyme_label == "" for s in verse.syllables()))

    def test_unstressed_midline_syllables_are_skipped_by_default(self):
        verse = verse_of([[S("AH0", ["N"], ["M"]), S("AE1", ["T"], ["K"], terminal=True)],
                          [S("AH0", ["N"], ["B"]), S("AE1", ["T"], ["HH"], terminal=True)]])
        assign_similarity_labels(verse, min_occurrences=2)
        labelled = [s for s in verse.syllables() if s.rhyme_label]
        self.assertTrue(all(s.nucleus.endswith("1") for s in labelled))

    def test_unstressed_filter_can_be_disabled(self):
        verse = verse_of([[S("AH0", ["N"], ["M"])], [S("AH0", ["N"], ["B"])]])
        assign_similarity_labels(verse, min_occurrences=2, skip_unstressed_midline=False)
        self.assertTrue(any(s.rhyme_label for s in verse.syllables()))


if __name__ == "__main__":
    unittest.main()
