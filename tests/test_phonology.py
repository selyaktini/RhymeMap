"""Tests for the articulatory feature space."""

import unittest

from rhymemap.phonology import (
    CONSONANTS,
    VOWELS,
    cluster_distance,
    consonant_distance,
    manner_distance,
    parse_vowel,
    vowel_distance,
)


class TestParseVowel(unittest.TestCase):
    def test_splits_stress_digit(self):
        self.assertEqual(parse_vowel("AA1"), ("AA", 1))
        self.assertEqual(parse_vowel("IH0"), ("IH", 0))
        self.assertEqual(parse_vowel("EY2"), ("EY", 2))

    def test_bare_vowel_is_unstressed(self):
        self.assertEqual(parse_vowel("AA"), ("AA", 0))

    def test_is_case_insensitive(self):
        self.assertEqual(parse_vowel("aa1"), ("AA", 1))


class TestVowelDistance(unittest.TestCase):
    def test_identity_is_zero(self):
        for v in VOWELS:
            self.assertEqual(vowel_distance(v, v), 0.0)

    def test_stress_is_ignored(self):
        self.assertEqual(vowel_distance("AA1", "AA2"), 0.0)

    def test_is_symmetric(self):
        for a in VOWELS:
            for b in VOWELS:
                self.assertAlmostEqual(vowel_distance(a, b), vowel_distance(b, a), places=9)

    def test_stays_in_range(self):
        for a in VOWELS:
            for b in VOWELS:
                self.assertGreaterEqual(vowel_distance(a, b), 0.0)
                self.assertLessEqual(vowel_distance(a, b), 1.0)

    def test_neighbours_are_closer_than_opposites(self):
        """IH/IY differ only in tenseness; IY/AA are opposite corners."""
        self.assertLess(vowel_distance("IH", "IY"), vowel_distance("IY", "AA"))
        self.assertLess(vowel_distance("AE", "EH"), vowel_distance("AE", "UW"))

    def test_uses_the_full_range(self):
        """Without rescaling the furthest pair only reached ~0.64."""
        worst = max(vowel_distance(a, b) for a in VOWELS for b in VOWELS)
        self.assertGreater(worst, 0.95)

    def test_unknown_symbol_is_maximally_distant(self):
        self.assertEqual(vowel_distance("AA", "QQ"), 1.0)
        self.assertEqual(vowel_distance("QQ", "QQ"), 0.0)


class TestConsonantDistance(unittest.TestCase):
    def test_identity_is_zero(self):
        for c in CONSONANTS:
            self.assertEqual(consonant_distance(c, c), 0.0)

    def test_is_symmetric(self):
        for a in CONSONANTS:
            for b in CONSONANTS:
                self.assertAlmostEqual(consonant_distance(a, b), consonant_distance(b, a), places=9)

    def test_stays_in_range(self):
        for a in CONSONANTS:
            for b in CONSONANTS:
                self.assertGreaterEqual(consonant_distance(a, b), 0.0)
                self.assertLessEqual(consonant_distance(a, b), 1.0)

    def test_voicing_pair_is_close(self):
        """T/D differ only in voicing; T/M differ in manner too."""
        self.assertLess(consonant_distance("T", "D"), consonant_distance("T", "M"))
        self.assertLess(consonant_distance("S", "Z"), consonant_distance("S", "NG"))

    def test_same_manner_beats_different_manner(self):
        self.assertLess(consonant_distance("T", "K"), consonant_distance("T", "S"))
        self.assertLess(consonant_distance("M", "N"), consonant_distance("M", "T"))

    def test_unknown_symbol_is_maximally_distant(self):
        self.assertEqual(consonant_distance("T", "QQ"), 1.0)


class TestMannerDistance(unittest.TestCase):
    def test_identity(self):
        self.assertEqual(manner_distance("plosive", "plosive"), 0.0)

    def test_symmetric_lookup(self):
        self.assertEqual(manner_distance("plosive", "nasal"), manner_distance("nasal", "plosive"))

    def test_unknown_manner_pair(self):
        self.assertEqual(manner_distance("plosive", "click"), 1.0)


class TestClusterDistance(unittest.TestCase):
    def test_identical_clusters(self):
        self.assertEqual(cluster_distance(["N", "T"], ["N", "T"]), 0.0)

    def test_both_empty(self):
        self.assertEqual(cluster_distance([], []), 0.0)

    def test_is_symmetric(self):
        self.assertAlmostEqual(cluster_distance(["N", "T"], ["K", "S"]),
                               cluster_distance(["K", "S"], ["N", "T"]), places=9)

    def test_stays_in_range(self):
        for a in ([], ["T"], ["N", "T"], ["S", "T", "R"]):
            for b in ([], ["D"], ["N", "D"], ["K", "S"]):
                self.assertGreaterEqual(cluster_distance(a, b), 0.0)
                self.assertLessEqual(cluster_distance(a, b), 1.0)

    def test_similar_cluster_beats_dissimilar(self):
        """-nt/-nd differ by one voicing feature; -nt/-ks share nothing."""
        self.assertLess(cluster_distance(["N", "T"], ["N", "D"]),
                        cluster_distance(["N", "T"], ["K", "S"]))

    def test_alignment_beats_string_equality(self):
        """The point of the feature-based alignment: -nt/-nd are near, not just unequal."""
        self.assertLess(cluster_distance(["N", "T"], ["N", "D"]), 0.2)

    def test_length_mismatch_costs_something(self):
        self.assertGreater(cluster_distance(["N", "T"], ["N"]), 0.0)

    def test_ignores_case_and_blanks(self):
        self.assertEqual(cluster_distance(["n", "t"], ["N", "T", ""]), 0.0)


if __name__ == "__main__":
    unittest.main()
