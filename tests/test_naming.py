"""Tests for rhyme-group naming."""

import unittest

from rhymemap.chains import RhymeChain
from rhymemap.models import Line, Syllable, Verse, Word
from rhymemap.naming import (
    FUNCTION_WORDS,
    GroupName,
    canonical_rime,
    deduplicate,
    name_chain,
    name_single_group,
    pick_exemplars,
    rename_groups,
    rime_from_spelling,
    spell_rime,
    strip_stress,
    vowel_groups,
)


def S(nucleus, coda=(), text="x", label=""):
    return Syllable(text=text, nucleus=nucleus, coda=list(coda), rhyme_label=label)


def verse_of(rows):
    """rows: [[(word_text, [(nucleus, coda, label), ...]), ...], ...]"""
    verse = Verse(metadata={"artist": "Test"})
    for line_id, words in enumerate(rows):
        word_objects = []
        for word_id, (text, syllables) in enumerate(words):
            objects = []
            for i, (nucleus, coda, label) in enumerate(syllables):
                syl = S(nucleus, coda, text=text, label=label)
                syl.line_id, syl.word_id, syl.syl_index = line_id, word_id, i
                objects.append(syl)
            word_objects.append(Word(text=text, syllables=objects, line_id=line_id, word_id=word_id))
        verse.lines.append(Line(text=" ".join(w.text for w in word_objects),
                                words=word_objects, line_id=line_id))
    return verse


class TestStripStress(unittest.TestCase):
    def test_removes_the_digit(self):
        self.assertEqual(strip_stress("AA1"), "AA")
        self.assertEqual(strip_stress("IH0"), "IH")

    def test_leaves_consonants_alone(self):
        self.assertEqual(strip_stress("NG"), "NG")


class TestVowelGroups(unittest.TestCase):
    def test_finds_runs_not_letters(self):
        self.assertEqual(vowel_groups("asteroid"), [0, 3, 5])   # a, e, oi

    def test_digraph_counts_once(self):
        self.assertEqual(vowel_groups("beat"), [1])

    def test_leading_y_is_a_consonant(self):
        """'yeah' must start at 'e', or an AE group gets named '-yeah'."""
        self.assertEqual(vowel_groups("yeah"), [1])

    def test_internal_y_is_a_vowel(self):
        self.assertIn(2, vowel_groups("rhyme"))

    def test_no_vowels(self):
        self.assertEqual(vowel_groups("psst"), [])


class TestRimeFromSpelling(unittest.TestCase):
    def test_monosyllable(self):
        self.assertEqual(rime_from_spelling("flames"), "ames")
        self.assertEqual(rime_from_spelling("nod"), "od")

    def test_silent_e_is_not_reached(self):
        """Indexing forward from the start, 'shame' gives 'ame', not 'e'."""
        self.assertEqual(rime_from_spelling("shame"), "ame")

    def test_uses_the_labelled_syllable(self):
        self.assertEqual(rime_from_spelling("asteroid", 2), "oid")
        self.assertEqual(rime_from_spelling("spaghetti", 1), "etti")

    def test_index_past_the_end_clamps(self):
        self.assertEqual(rime_from_spelling("nod", 9), "od")

    def test_word_without_vowels(self):
        self.assertEqual(rime_from_spelling("psst"), "psst")

    def test_punctuation_is_dropped(self):
        self.assertEqual(rime_from_spelling("flames,"), "ames")


class TestSpellRime(unittest.TestCase):
    def test_known_phonemes(self):
        self.assertEqual(spell_rime("EY1", ["M", "Z"]), "aymz")

    def test_bare_vowel(self):
        self.assertEqual(spell_rime("IY1", []), "ee")

    def test_unknown_phoneme_passes_through(self):
        self.assertEqual(spell_rime("QQ", []), "qq")


class TestCanonicalRime(unittest.TestCase):
    def test_takes_the_commonest(self):
        syllables = [S("AE1", ["M"]), S("AE1", ["M"]), S("AE1", ["N"])]
        self.assertEqual(canonical_rime(syllables), ("AE", ("M",)))

    def test_ignores_stress(self):
        self.assertEqual(canonical_rime([S("AE1", ["T"]), S("AE2", ["T"])]), ("AE", ("T",)))

    def test_empty(self):
        self.assertEqual(canonical_rime([]), ("", ()))


class TestPickExemplars(unittest.TestCase):
    def test_commonest_first(self):
        self.assertEqual(pick_exemplars(["fame", "flames", "flames"])[0], "flames")

    def test_function_words_are_demoted(self):
        chosen = pick_exemplars(["the", "the", "the", "flames"], limit=2)
        self.assertEqual(chosen[0], "flames")

    def test_on_rime_words_come_first(self):
        chosen = pick_exemplars(["what", "what", "flames"], on_rime=["flames"], limit=1)
        self.assertEqual(chosen, ["flames"])

    def test_is_deterministic(self):
        words = ["fame", "shame", "flames"]
        self.assertEqual(pick_exemplars(words), pick_exemplars(list(reversed(words))))

    def test_limit(self):
        self.assertEqual(len(pick_exemplars(["a", "b", "c", "d", "e"], limit=2)), 2)


class TestNameSingleGroup(unittest.TestCase):
    def test_names_after_the_rime(self):
        syllables = [S("EY1", ["M", "Z"]), S("EY1", ["M"]), S("EY1", ["M"])]
        occurrences = [("flames", 0), ("fame", 0), ("shame", 0)]
        name = name_single_group(syllables, occurrences)
        self.assertEqual(name.label, "-ame")
        self.assertEqual(name.rime, "EY M")

    def test_label_and_rime_agree(self):
        """The label must describe the group's modal rime, not its first member."""
        syllables = [S("IH1", ["M"]), S("IH1", ["M"]), S("IH1", ["T"])]
        name = name_single_group(syllables, [("him", 0), ("slim", 0), ("it", 0)])
        self.assertEqual(name.rime, "IH M")
        self.assertIn("im", name.label)

    def test_label_never_lacks_a_vowel(self):
        """A letter-name like 'j' once labelled an entire group."""
        syllables = [S("EY1", []), S("EY1", []), S("EY1", [])]
        name = name_single_group(syllables, [("j", 0), ("day", 0), ("hey", 0)])
        self.assertTrue(any(c in "aeiou" for c in name.label), name.label)

    def test_empty_group(self):
        self.assertTrue(name_single_group([], []).label)


class TestNameChain(unittest.TestCase):
    def test_names_after_the_span(self):
        name = name_chain(["lookin boy", "lookin boy", "say lookin boy"])
        self.assertEqual(name.label, "lookin boy")

    def test_keeps_word_spacing(self):
        """Collapsing to 'lookinboy' defeats the point of naming at all."""
        self.assertIn(" ", name_chain(["they say lookin boy"] * 2).label)

    def test_empty(self):
        self.assertEqual(name_chain([]).label, "chain")


class TestDeduplicate(unittest.TestCase):
    def test_leaves_unique_names_alone(self):
        names = [GroupName(label="-ame"), GroupName(label="-od")]
        self.assertEqual([n.label for n in deduplicate(names)], ["-ame", "-od"])

    def test_prefers_another_real_spelling_over_a_number(self):
        names = [GroupName(label="-at"), GroupName(label="-at", alternatives=["atter"])]
        self.assertEqual([n.label for n in deduplicate(names)], ["-at", "-atter"])

    def test_falls_back_to_a_number(self):
        names = [GroupName(label="-at"), GroupName(label="-at")]
        self.assertEqual(deduplicate(names)[1].label, "-at 2")

    def test_three_way_collision(self):
        names = [GroupName(label="-at") for _ in range(3)]
        self.assertEqual(len({n.label for n in deduplicate(names)}), 3)


class TestRenameGroups(unittest.TestCase):
    def test_replaces_labels_on_syllables(self):
        verse = verse_of([
            [("flames", [("EY1", ["M", "Z"], "A")])],
            [("shame", [("EY1", ["M"], "A")])],
        ])
        names = rename_groups(verse)
        labels = {s.rhyme_label for s in verse.syllables()}
        self.assertEqual(len(labels), 1)
        self.assertTrue(next(iter(labels)).startswith("-"))
        self.assertEqual(set(names), labels)

    def test_unlabelled_syllables_are_untouched(self):
        verse = verse_of([[("flames", [("EY1", ["M"], "")])]])
        rename_groups(verse)
        self.assertEqual(verse.syllables()[0].rhyme_label, "")

    def test_records_positions(self):
        verse = verse_of([
            [("flames", [("EY1", ["M"], "A")])],
            [("shame", [("EY1", ["M"], "A")])],
        ])
        name = next(iter(rename_groups(verse).values()))
        self.assertEqual(len(name.positions), 2)
        self.assertTrue(all(0.0 <= p <= 1.0 for p in name.positions))

    def test_chain_labels_are_rewritten_too(self):
        verse = verse_of([
            [("lookin", [("UH1", ["K"], "A")]), ("boy", [("OY1", [], "A")])],
            [("lookin", [("UH1", ["K"], "A")]), ("boy", [("OY1", [], "A")])],
        ])
        chain = RhymeChain(length=2, occurrences=[0, 2], similarity=1.0, label="A")
        rename_groups(verse, [chain])
        self.assertNotEqual(chain.label, "A")
        self.assertEqual(chain.label, verse.syllables()[0].rhyme_label)

    def test_empty_verse(self):
        self.assertEqual(rename_groups(Verse()), {})

    def test_is_stable_across_runs(self):
        """The same sound must be called the same thing every time."""
        def build():
            return verse_of([[("flames", [("EY1", ["M", "Z"], "A")])],
                             [("shame", [("EY1", ["M"], "A")])]])
        self.assertEqual(set(rename_groups(build())), set(rename_groups(build())))


class TestFunctionWords(unittest.TestCase):
    def test_covers_the_common_ones(self):
        for word in ("the", "of", "you", "it", "and"):
            self.assertIn(word, FUNCTION_WORDS)


if __name__ == "__main__":
    unittest.main()
