"""Tests for multisyllabic chain detection."""

import unittest

from rhymemap.chains import RhymeChain, _split_by_locality, assign_chain_labels, chain_metrics, detect_chains
from rhymemap.models import Line, Syllable, Verse, Word


def S(nucleus, coda=(), onset=(), text="x"):
    return Syllable(text=text, nucleus=nucleus, coda=list(coda), onset=list(onset))


def verse_of(rows):
    """Build a verse from [[syllable, ...], ...]; each row is one line."""
    verse = Verse(metadata={"artist": "Test"})
    for line_id, syllables in enumerate(rows):
        for i, s in enumerate(syllables):
            s.line_id, s.word_id, s.syl_index = line_id, i, 0
        words = [Word(text=s.text, syllables=[s], line_id=line_id, word_id=i,
                      is_last_word=(i == len(syllables) - 1))
                 for i, s in enumerate(syllables)]
        verse.lines.append(Line(text=" ".join(s.text for s in syllables), words=words, line_id=line_id))
    return verse


# A distinctive three-syllable span, and filler that rhymes with nothing.
SPAN = [("EY1", ["T"], ["L"]), ("IH0", ["N"], ["T"]), ("AA1", ["G"], ["D"])]
FILLER = [("UW1", ["M"], ["Z"]), ("ER1", ["P"], ["V"])]


def span(prefix=""):
    return [S(n, c, o, text=f"{prefix}{i}") for i, (n, c, o) in enumerate(SPAN)]


def filler(prefix=""):
    return [S(n, c, o, text=f"{prefix}f{i}") for i, (n, c, o) in enumerate(FILLER)]


class TestRhymeChain(unittest.TestCase):
    def test_strength_is_length_times_similarity_times_count(self):
        chain = RhymeChain(length=4, occurrences=[0, 10, 20], similarity=0.5)
        self.assertAlmostEqual(chain.strength, 4 * 0.5 * 3)

    def test_covers_every_index_of_every_occurrence(self):
        self.assertEqual(RhymeChain(length=2, occurrences=[0, 5]).covers(), {0, 1, 5, 6})

    def test_longer_chain_outranks_its_own_fragment(self):
        long_chain = RhymeChain(length=4, occurrences=[0, 10], similarity=0.9)
        fragment = RhymeChain(length=1, occurrences=[0, 10], similarity=1.0)
        self.assertGreater(long_chain.strength, fragment.strength)


class TestSplitByLocality(unittest.TestCase):
    def test_close_occurrences_stay_together(self):
        self.assertEqual(_split_by_locality([0, 1], {0: 0, 1: 1}, 2), [[0, 1]])

    def test_distant_occurrences_split(self):
        self.assertEqual(_split_by_locality([0, 1], {0: 0, 1: 40}, 2), [[0], [1]])

    def test_zero_gap_disables_splitting(self):
        self.assertEqual(_split_by_locality([0, 1], {0: 0, 1: 99}, 0), [[0, 1]])

    def test_chains_of_close_occurrences(self):
        lines = {0: 0, 1: 2, 2: 4, 3: 20}
        self.assertEqual(_split_by_locality([0, 1, 2, 3], lines, 2), [[0, 1, 2], [3]])


class TestDetectChains(unittest.TestCase):
    def test_empty_verse(self):
        self.assertEqual(detect_chains(Verse()), [])

    def test_single_syllable_verse(self):
        self.assertEqual(detect_chains(verse_of([[S("AA1", ["T"])]])), [])

    def test_finds_a_repeated_span(self):
        verse = verse_of([filler("a") + span("a"), filler("b") + span("b")])
        chains = detect_chains(verse, min_occurrences=2)
        self.assertTrue(any(c.length >= len(SPAN) for c in chains),
                        f"expected a {len(SPAN)}-syllable chain, got {chains}")

    def test_repeated_span_is_one_chain_not_fragments(self):
        """The whole point: a 3-syllable repeat must not be shredded into 1-grams."""
        verse = verse_of([filler("a") + span("a"), filler("b") + span("b")])
        assign_chain_labels(verse, min_occurrences=2)
        labels = [s.rhyme_label for s in verse.syllables()]
        first = labels[len(FILLER):len(FILLER) + len(SPAN)]
        second = labels[2 * len(FILLER) + len(SPAN):]
        self.assertTrue(all(first), "first occurrence should be labelled")
        self.assertEqual(len(set(first)), 1, "one occurrence should carry one label")
        self.assertEqual(first, second, "both occurrences should carry the same labels")

    def test_min_occurrences_is_respected(self):
        verse = verse_of([filler("a") + span("a"), filler("b")])
        self.assertEqual([c for c in detect_chains(verse, min_occurrences=2) if c.length == len(SPAN)], [])

    def test_distant_repeats_are_not_one_chain(self):
        rows = [filler("a") + span("a")] + [filler(f"p{i}") for i in range(8)] + [filler("b") + span("b")]
        chains = detect_chains(verse_of(rows), min_occurrences=2, max_line_gap=2)
        self.assertTrue(all(len(c.occurrences) < 2 or c.length < len(SPAN) for c in chains),
                        "occurrences 9 lines apart should not form one chain")

    def test_occurrences_within_a_chain_never_overlap(self):
        verse = verse_of([span("a") + span("b"), span("c") + span("d")])
        for chain in detect_chains(verse, min_occurrences=2):
            covered = set()
            for start in chain.occurrences:
                span_indices = set(range(start, start + chain.length))
                self.assertFalse(span_indices & covered, "a chain's occurrences overlap")
                covered |= span_indices

    def test_chains_never_overlap_each_other(self):
        verse = verse_of([filler("a") + span("a"), filler("b") + span("b"), filler("c") + span("c")])
        seen = set()
        for chain in detect_chains(verse, min_occurrences=2):
            self.assertFalse(chain.covers() & seen, "two chains claim the same syllable")
            seen |= chain.covers()

    def test_max_window_caps_chain_length(self):
        rows = [span("a") + span("b") + span("c"), span("d") + span("e") + span("f")]
        for chain in detect_chains(verse_of(rows), max_window=2, min_occurrences=2):
            self.assertLessEqual(chain.length, 2)


class TestAssignChainLabels(unittest.TestCase):
    def test_labels_are_written_onto_syllables(self):
        verse = verse_of([filler("a") + span("a"), filler("b") + span("b")])
        chains = assign_chain_labels(verse, min_occurrences=2)
        self.assertTrue(chains)
        self.assertTrue(any(s.rhyme_label for s in verse.syllables()))

    def test_previous_labels_are_cleared(self):
        verse = verse_of([filler("a"), filler("b")])
        for s in verse.syllables():
            s.rhyme_label = "STALE"
        assign_chain_labels(verse, min_occurrences=5)
        self.assertTrue(all(s.rhyme_label != "STALE" for s in verse.syllables()))

    def test_every_chain_gets_a_distinct_label(self):
        verse = verse_of([filler("a") + span("a"), filler("b") + span("b")])
        chains = assign_chain_labels(verse, min_occurrences=2)
        labels = [c.label for c in chains]
        self.assertEqual(len(labels), len(set(labels)))


class TestChainMetrics(unittest.TestCase):
    def test_empty_verse(self):
        metrics = chain_metrics(Verse(), [])
        self.assertEqual(metrics["chains"], 0)
        self.assertEqual(metrics["multi_score"], 0.0)

    def test_no_chains_means_zero_coverage(self):
        verse = verse_of([filler("a"), filler("b")])
        metrics = chain_metrics(verse, [])
        self.assertEqual(metrics["chain_density"], 0.0)

    def test_multi_score_counts_only_multisyllabic_chains(self):
        verse = verse_of([filler("a") + span("a"), filler("b") + span("b")])
        singles = [RhymeChain(length=1, occurrences=[0, 2], similarity=1.0)]
        self.assertEqual(chain_metrics(verse, singles)["multi_score"], 0.0)
        self.assertGreater(chain_metrics(verse, singles)["chain_density"], 0.0)

    def test_reports_the_longest_chain(self):
        verse = verse_of([filler("a") + span("a"), filler("b") + span("b")])
        chains = [RhymeChain(length=3, occurrences=[2, 7], similarity=0.9)]
        self.assertEqual(chain_metrics(verse, chains)["longest_chain"], 3)


if __name__ == "__main__":
    unittest.main()
