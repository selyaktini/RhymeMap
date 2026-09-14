"""Tests for the evaluation harness and the gold set's integrity."""

import json
import unittest
from pathlib import Path

from eval.scoring import (
    Score,
    aggregate_pairwise,
    bcubed_score,
    groups_to_labels,
    mean_score,
    pairwise_counts,
    pairwise_score,
)

GOLD_PATH = Path(__file__).resolve().parent.parent / "eval" / "gold.json"


class TestScore(unittest.TestCase):
    def test_f1_is_the_harmonic_mean(self):
        self.assertAlmostEqual(Score(0.5, 0.5).f1, 0.5)
        self.assertAlmostEqual(Score(1.0, 0.5).f1, 2 / 3)

    def test_f1_is_zero_when_both_are_zero(self):
        self.assertEqual(Score(0.0, 0.0).f1, 0.0)


class TestGroupsToLabels(unittest.TestCase):
    def test_basic_conversion(self):
        self.assertEqual(groups_to_labels([[0, 2], [1]], 3), [0, 1, 0])

    def test_unlisted_lines_become_singletons(self):
        labels = groups_to_labels([[0, 1]], 4)
        self.assertEqual(labels[0], labels[1])
        self.assertEqual(len({labels[2], labels[3], labels[0]}), 3)

    def test_out_of_range_indices_are_ignored(self):
        self.assertEqual(len(groups_to_labels([[0, 99]], 2)), 2)


class TestPairwise(unittest.TestCase):
    def test_identical_partitions_score_one(self):
        labels = groups_to_labels([[0, 1, 2], [3, 4]], 5)
        score = pairwise_score(labels, labels)
        self.assertEqual((score.precision, score.recall, score.f1), (1.0, 1.0, 1.0))

    def test_one_group_has_full_recall_and_poor_precision(self):
        gold = groups_to_labels([[0, 1, 2], [3, 4]], 5)
        score = pairwise_score([0] * 5, gold)
        self.assertEqual(score.recall, 1.0)
        self.assertLess(score.precision, 1.0)

    def test_all_singletons_has_zero_recall(self):
        gold = groups_to_labels([[0, 1, 2], [3, 4]], 5)
        self.assertEqual(pairwise_score(list(range(5)), gold).recall, 0.0)

    def test_counts_add_up(self):
        gold = groups_to_labels([[0, 1], [2, 3]], 4)
        predicted = groups_to_labels([[0, 1, 2], [3]], 4)
        tp, fp, fn = pairwise_counts(predicted, gold)
        self.assertEqual(tp, 1)   # (0,1) only
        self.assertEqual(fp, 2)   # (0,2) and (1,2)
        self.assertEqual(fn, 1)   # (2,3)

    def test_is_symmetric_in_f1_for_swapped_roles(self):
        a = groups_to_labels([[0, 1], [2]], 3)
        b = groups_to_labels([[0], [1, 2]], 3)
        self.assertAlmostEqual(pairwise_score(a, b).f1, pairwise_score(b, a).f1)


class TestBCubed(unittest.TestCase):
    def test_identical_partitions_score_one(self):
        labels = groups_to_labels([[0, 1, 2], [3, 4]], 5)
        score = bcubed_score(labels, labels)
        self.assertAlmostEqual(score.precision, 1.0)
        self.assertAlmostEqual(score.recall, 1.0)

    def test_all_singletons_has_perfect_precision(self):
        gold = groups_to_labels([[0, 1, 2], [3, 4]], 5)
        self.assertAlmostEqual(bcubed_score(list(range(5)), gold).precision, 1.0)

    def test_one_group_has_perfect_recall(self):
        gold = groups_to_labels([[0, 1, 2], [3, 4]], 5)
        self.assertAlmostEqual(bcubed_score([0] * 5, gold).recall, 1.0)

    def test_punishes_over_merging_less_than_pairwise(self):
        """B-cubed exists because pairwise weights big groups quadratically."""
        gold = groups_to_labels([[0, 1, 2], [3, 4]], 5)
        self.assertGreater(bcubed_score([0] * 5, gold).f1, pairwise_score([0] * 5, gold).f1)

    def test_empty_input(self):
        self.assertEqual(bcubed_score([], []).f1, 1.0)


class TestAggregation(unittest.TestCase):
    def test_pairwise_counts_are_pooled(self):
        score = aggregate_pairwise([(1, 0, 0), (1, 1, 1)])
        self.assertAlmostEqual(score.precision, 2 / 3)
        self.assertAlmostEqual(score.recall, 2 / 3)

    def test_empty_aggregate(self):
        self.assertEqual(aggregate_pairwise([]).f1, 1.0)

    def test_mean_score_averages(self):
        score = mean_score([Score(1.0, 0.0), Score(0.0, 1.0)])
        self.assertAlmostEqual(score.precision, 0.5)
        self.assertAlmostEqual(score.recall, 0.5)


class TestGoldSet(unittest.TestCase):
    """The gold set is data, so its integrity is a test, not a convention."""

    @classmethod
    def setUpClass(cls):
        if not GOLD_PATH.exists():
            raise unittest.SkipTest("eval/gold.json not built; run `make gold`")
        cls.gold = json.loads(GOLD_PATH.read_text(encoding="utf-8"))

    def test_has_verses(self):
        self.assertGreater(len(self.gold["verses"]), 0)

    def test_declared_counts_match_content(self):
        self.assertEqual(self.gold["verse_count"], len(self.gold["verses"]))
        self.assertEqual(self.gold["line_count"], sum(len(v["lines"]) for v in self.gold["verses"]))

    def test_every_line_is_in_exactly_one_group(self):
        for verse in self.gold["verses"]:
            flat = [i for group in verse["end_rhyme_groups"] for i in group]
            self.assertEqual(sorted(flat), list(range(len(verse["lines"]))),
                             f"{verse['id']}: groups must partition the lines exactly once")

    def test_verse_ids_are_unique(self):
        ids = [v["id"] for v in self.gold["verses"]]
        self.assertEqual(len(ids), len(set(ids)))

    def test_no_empty_lines(self):
        for verse in self.gold["verses"]:
            self.assertTrue(all(line.strip() for line in verse["lines"]), verse["id"])

    def test_provenance_is_recorded(self):
        """The annotations are model-made; the file must say so."""
        self.assertIn("provenance", self.gold)
        self.assertIn("Claude", self.gold["provenance"])

    def test_every_verse_carries_required_fields(self):
        for verse in self.gold["verses"]:
            for field in ("id", "track", "artist", "source", "lines", "end_rhyme_groups", "notes"):
                self.assertIn(field, verse, f"{verse.get('id')} is missing {field}")


if __name__ == "__main__":
    unittest.main()
