"""Tests for the unified metric definitions."""

import unittest

from rhymemap.metrics import compute_metrics, multisyllabic_runs
from rhymemap.models import Line, Syllable, Verse, Word


def labelled(*labels):
    """Build a one-line verse whose syllables carry the given labels."""
    syllables = [Syllable(text="x", nucleus="AE1", coda=[], rhyme_label=lab) for lab in labels]
    word = Word(text="w", syllables=syllables, is_last_word=True)
    return Verse(lines=[Line(text="w", words=[word])])


class TestMultisyllabicRuns(unittest.TestCase):
    def test_no_runs_when_labels_alternate(self):
        """Regression: the old metric counted any two adjacent *labelled*
        syllables as multisyllabic, without checking the labels matched."""
        verse = labelled("A", "B", "A", "B")
        self.assertEqual(multisyllabic_runs(verse.syllables()), [])

    def test_detects_a_run_of_same_label(self):
        runs = multisyllabic_runs(labelled("A", "A", "A").syllables())
        self.assertEqual(runs, [(0, 3, "A")])

    def test_unlabelled_syllable_breaks_a_run(self):
        runs = multisyllabic_runs(labelled("A", "", "A").syllables())
        self.assertEqual(runs, [])

    def test_multiple_runs(self):
        runs = multisyllabic_runs(labelled("A", "A", "", "B", "B", "B").syllables())
        self.assertEqual(runs, [(0, 2, "A"), (3, 3, "B")])


class TestComputeMetrics(unittest.TestCase):
    def test_empty_verse(self):
        metrics = compute_metrics(Verse())
        self.assertEqual(metrics["syllables"], 0)
        self.assertEqual(metrics["density"], 0.0)

    def test_density_counts_labelled_syllables(self):
        metrics = compute_metrics(labelled("A", "A", "", ""))
        self.assertEqual(metrics["density"], 50.0)

    def test_multi_counts_only_same_label_runs(self):
        self.assertEqual(compute_metrics(labelled("A", "B", "A", "B"))["multi"], 0.0)
        self.assertEqual(compute_metrics(labelled("A", "A", "B", "B"))["multi"], 100.0)

    def test_signatures_counts_distinct_groups(self):
        self.assertEqual(compute_metrics(labelled("A", "A", "B", ""))["signatures"], 2)

    def test_diversity_is_groups_over_syllables(self):
        self.assertEqual(compute_metrics(labelled("A", "A", "B", ""))["diversity"], 50.0)

    def test_all_keys_present(self):
        metrics = compute_metrics(labelled("A"))
        self.assertEqual(set(metrics), {"density", "multi", "diversity", "signatures", "syllables"})


if __name__ == "__main__":
    unittest.main()
