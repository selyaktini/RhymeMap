"""Tests for the v1 exact-match rhyme engine.

This module previously had no test coverage at all, which is where every bug
found in the Phase 1 audit lived.
"""

import unittest

from rhymemap.engine import (
    CONSONANT_FAMILIES,
    RhymeRegistry,
    assign_rhyme_labels,
    candidate_syllables,
    encode_coda,
    get_syllable_signature,
    label_for_index,
)
from rhymemap.models import Line, Syllable, Verse, Word


def syl(nucleus="AE1", coda=(), onset=(), text="x", terminal=False):
    return Syllable(text=text, nucleus=nucleus, coda=list(coda), onset=list(onset), is_terminal=terminal)


def build_verse(lines_of_syllables):
    """Build a Verse from [[syllable, ...], ...] — one word per line, for brevity."""
    verse = Verse(metadata={"artist": "Test"})
    for line_id, syllables in enumerate(lines_of_syllables):
        for i, s in enumerate(syllables):
            s.line_id, s.word_id, s.syl_index = line_id, 0, i
        word = Word(text="w", syllables=syllables, line_id=line_id, word_id=0, is_last_word=True)
        verse.lines.append(Line(text="w", words=[word], line_id=line_id))
    return verse


class TestLabelSpace(unittest.TestCase):
    """Regression: the 27th rhyme group used to silently reuse label 'A'."""

    def test_first_26_are_single_letters(self):
        self.assertEqual(label_for_index(0), "A")
        self.assertEqual(label_for_index(25), "Z")

    def test_does_not_wrap_at_26(self):
        self.assertEqual(label_for_index(26), "AA")
        self.assertEqual(label_for_index(27), "AB")
        self.assertNotEqual(label_for_index(26), label_for_index(0))

    def test_continues_past_two_letters(self):
        self.assertEqual(label_for_index(51), "AZ")
        self.assertEqual(label_for_index(52), "BA")
        self.assertEqual(label_for_index(701), "ZZ")
        self.assertEqual(label_for_index(702), "AAA")

    def test_rejects_negative(self):
        with self.assertRaises(ValueError):
            label_for_index(-1)

    def test_registry_never_collides(self):
        registry = RhymeRegistry()
        labels = [registry.get_label(f"sig{i}") for i in range(500)]
        self.assertEqual(len(set(labels)), 500)

    def test_registry_is_stable(self):
        registry = RhymeRegistry()
        first = registry.get_label("AE_1_T")
        self.assertEqual(registry.get_label("AE_1_T"), first)


class TestCodaEncoding(unittest.TestCase):
    def test_empty_coda(self):
        self.assertEqual(encode_coda([]), "")

    def test_raw_coda_is_concatenated(self):
        self.assertEqual(encode_coda(["N", "T"]), "NT")

    def test_families_group_similar_consonants(self):
        """Regression: CONSONANT_FAMILIES was defined but never referenced."""
        self.assertEqual(encode_coda(["T"], use_consonant_families=True), "PLO")
        self.assertEqual(encode_coda(["K"], use_consonant_families=True), "PLO")
        self.assertEqual(
            encode_coda(["T"], use_consonant_families=True),
            encode_coda(["K"], use_consonant_families=True),
        )

    def test_unknown_consonant_passes_through(self):
        self.assertEqual(encode_coda(["QQ"], use_consonant_families=True), "QQ")

    def test_every_family_value_is_a_string(self):
        self.assertTrue(all(isinstance(v, str) for v in CONSONANT_FAMILIES.values()))


class TestSignature(unittest.TestCase):
    def test_basic_signature(self):
        self.assertEqual(get_syllable_signature(syl("AE1", ["T"])), "AE_1_T")

    def test_empty_nucleus_yields_no_signature(self):
        self.assertEqual(get_syllable_signature(syl("", [])), "")

    def test_unstressed_midline_is_ignored(self):
        self.assertEqual(get_syllable_signature(syl("AH0", ["T"], terminal=False)), "")

    def test_unstressed_terminal_is_kept(self):
        self.assertEqual(get_syllable_signature(syl("AH0", ["T"], terminal=True)), "AH_0_T")

    def test_include_stress_false_merges_stress_levels(self):
        primary = get_syllable_signature(syl("AE1", ["T"]), include_stress=False)
        secondary = get_syllable_signature(syl("AE2", ["T"]), include_stress=False)
        self.assertEqual(primary, secondary)

    def test_stress_separates_by_default(self):
        self.assertNotEqual(get_syllable_signature(syl("AE1", ["T"])),
                            get_syllable_signature(syl("AE2", ["T"])))

    def test_slant_rhyme_only_with_families(self):
        loud, out = syl("AW1", ["D"]), syl("AW1", ["T"])
        self.assertNotEqual(get_syllable_signature(loud), get_syllable_signature(out))
        self.assertEqual(
            get_syllable_signature(loud, use_consonant_families=True),
            get_syllable_signature(out, use_consonant_families=True),
        )


class TestCandidateSelection(unittest.TestCase):
    def setUp(self):
        self.line = build_verse([[syl(text="a"), syl(text="b"), syl(text="c", terminal=True)]]).lines[0]

    def test_all_syllables_by_default(self):
        self.assertEqual(len(candidate_syllables(self.line)), 3)

    def test_tail_window_limits_to_last_n(self):
        picked = candidate_syllables(self.line, tail_window=2)
        self.assertEqual([s.text for s in picked], ["b", "c"])

    def test_only_terminal_keeps_line_final(self):
        """Regression: only_terminal was accepted as a parameter and ignored."""
        picked = candidate_syllables(self.line, only_terminal=True)
        self.assertEqual([s.text for s in picked], ["c"])

    def test_only_terminal_overrides_tail_window(self):
        picked = candidate_syllables(self.line, tail_window=3, only_terminal=True)
        self.assertEqual([s.text for s in picked], ["c"])


class TestAssignRhymeLabels(unittest.TestCase):
    def test_threshold_filters_rare_signatures(self):
        verse = build_verse([[syl("AE1", ["T"], terminal=True)],
                             [syl("AE1", ["T"], terminal=True)],
                             [syl("OW1", ["N"], terminal=True)]])
        assign_rhyme_labels(verse, min_occurrences=2)
        labels = [s.rhyme_label for s in verse.syllables()]
        self.assertEqual(labels[0], labels[1])
        self.assertTrue(labels[0])
        self.assertEqual(labels[2], "", "signature below threshold must stay unlabelled")

    def test_only_terminal_restricts_labelling(self):
        verse = build_verse([[syl("AE1", ["T"]), syl("AE1", ["T"], terminal=True)],
                             [syl("AE1", ["T"]), syl("AE1", ["T"], terminal=True)]])
        assign_rhyme_labels(verse, min_occurrences=2, only_terminal=True)
        labelled = [s for s in verse.syllables() if s.rhyme_label]
        self.assertEqual(len(labelled), 2)
        self.assertTrue(all(s.is_terminal for s in labelled))

    def test_returns_registry(self):
        verse = build_verse([[syl("AE1", ["T"], terminal=True)], [syl("AE1", ["T"], terminal=True)]])
        registry = assign_rhyme_labels(verse, min_occurrences=2)
        self.assertIsInstance(registry, RhymeRegistry)
        self.assertEqual(len(registry.mapping), 1)

    def test_many_groups_get_distinct_labels(self):
        """End-to-end guard against the modulo-26 collision."""
        lines = []
        for i in range(40):
            # Two-letter vowel codes: the stress regex reads the trailing digit,
            # so "V101" would parse as vowel "V" + stress "1" and collide.
            nucleus = f"{chr(65 + i // 26)}{chr(65 + i % 26)}1"
            lines.extend([[syl(nucleus, ["T"], terminal=True)], [syl(nucleus, ["T"], terminal=True)]])
        verse = build_verse(lines)
        assign_rhyme_labels(verse, min_occurrences=2)
        labels = {s.rhyme_label for s in verse.syllables() if s.rhyme_label}
        self.assertEqual(len(labels), 40)


if __name__ == "__main__":
    unittest.main()
