"""Tests for cleaning, phoneme lookup and syllabification."""

import unittest

from rhymemap.models import Line, Verse
from rhymemap.phonetics import (
    clean_word,
    extract_nuclei,
    extract_syllables,
    g2p_available,
    lookup_variants,
    phonemes_for_word,
    process_line,
    process_verse,
    split_word_text,
)

# The neural fallback is only needed for words outside CMUdict. Tests that
# require it are skipped rather than failing when the corpora are absent.
needs_g2p = unittest.skipUnless(g2p_available(), "g2p_en/NLTK corpora unavailable")


class TestCleanWord(unittest.TestCase):
    def test_strips_punctuation_and_lowercases(self):
        self.assertEqual(clean_word("Hello!"), "hello")
        self.assertEqual(clean_word("(parenthesis)"), "parenthesis")
        self.assertEqual(clean_word("  spaces  "), "spaces")

    def test_removes_apostrophes(self):
        self.assertEqual(clean_word("rock'n'roll"), "rocknroll")
        self.assertEqual(clean_word("don't"), "dont")


class TestLookupVariants(unittest.TestCase):
    """The backoff that keeps g-dropped and de-apostrophised words in CMUdict."""

    def test_word_itself_comes_first(self):
        self.assertEqual(next(iter(lookup_variants("cat"))), "cat")

    def test_g_dropping(self):
        self.assertIn("coming", list(lookup_variants("comin")))

    def test_clitic_restoration(self):
        self.assertIn("don't", list(lookup_variants("dont")))
        self.assertIn("he's", list(lookup_variants("hes")))
        self.assertIn("you'll", list(lookup_variants("youll")))

    def test_short_words_are_not_split(self):
        """'is' must not be treated as 'i' + clitic 's'."""
        self.assertEqual(list(lookup_variants("is")), ["is"])


class TestPhonemes(unittest.TestCase):
    def test_dictionary_word(self):
        self.assertEqual(phonemes_for_word("banana"), ["B", "AH0", "N", "AE1", "N", "AH0"])

    def test_empty_word(self):
        self.assertEqual(phonemes_for_word(""), [])

    def test_backoff_gives_dictionary_pronunciation(self):
        """'comin' should resolve via 'coming', not a neural guess."""
        self.assertEqual(phonemes_for_word("comin"), phonemes_for_word("coming"))

    def test_repeated_lookup_is_consistent(self):
        self.assertEqual(phonemes_for_word("hello"), phonemes_for_word("hello"))


class TestSplitWordText(unittest.TestCase):
    def test_single_syllable(self):
        self.assertEqual(split_word_text("cat", 1), ["cat"])

    def test_parts_rejoin_to_the_original(self):
        for word, n in [("banana", 3), ("beautiful", 3), ("extraordinary", 6)]:
            self.assertEqual("".join(split_word_text(word, n)), word)

    def test_zero_syllables(self):
        self.assertEqual(split_word_text("cat", 0), ["cat"])


class TestExtractSyllables(unittest.TestCase):
    def test_splits_a_known_word(self):
        syllables = extract_syllables("banana", 0, 0, True)
        self.assertEqual(len(syllables), 3)
        self.assertEqual([s.nucleus for s in syllables], ["AH0", "AE1", "AH0"])

    def test_captures_onset_and_coda(self):
        syllables = extract_syllables("banana", 0, 0, False)
        self.assertEqual(syllables[0].onset, ["B"])
        self.assertEqual(syllables[1].coda, ["N"])

    def test_position_metadata_is_filled(self):
        syllables = extract_syllables("banana", 3, 7, False)
        self.assertTrue(all(s.line_id == 3 and s.word_id == 7 for s in syllables))
        self.assertEqual([s.syl_index for s in syllables], [0, 1, 2])

    def test_only_last_syllable_of_last_word_is_terminal(self):
        syllables = extract_syllables("banana", 0, 0, True)
        self.assertEqual([s.is_terminal for s in syllables], [False, False, True])

    def test_non_final_word_has_no_terminal(self):
        self.assertFalse(any(s.is_terminal for s in extract_syllables("banana", 0, 0, False)))

    @needs_g2p
    def test_out_of_vocabulary_word_still_yields_syllables(self):
        self.assertGreater(len(extract_syllables("skrrt", 0, 0, True)), 0)

    def test_empty_word(self):
        self.assertEqual(extract_syllables("", 0, 0, True), [])


class TestNuclei(unittest.TestCase):
    def test_extract_nuclei(self):
        nuclei = extract_nuclei("hello", 0, 0, True)
        self.assertGreater(len(nuclei), 0)
        self.assertTrue(nuclei[-1].is_terminal)

    def test_non_last_word_has_no_terminal_nucleus(self):
        self.assertFalse(extract_nuclei("hello", 0, 0, False)[-1].is_terminal)

    def test_derived_nuclei_match_direct_extraction(self):
        """process_line derives nuclei from syllables instead of a second g2p pass."""
        word = process_line("banana", 0).words[0]
        direct = extract_nuclei("banana", 0, 0, True)
        self.assertEqual([n.phoneme for n in word.nuclei], [n.phoneme for n in direct])


class TestProcessLine(unittest.TestCase):
    def test_single_word(self):
        line = process_line("hello", 0)
        self.assertIsInstance(line, Line)
        self.assertEqual(len(line.words), 1)
        self.assertTrue(line.words[0].is_last_word)

    def test_multiple_words(self):
        line = process_line("hello world", 0)
        self.assertEqual([w.text for w in line.words], ["hello", "world"])
        self.assertFalse(line.words[0].is_last_word)
        self.assertTrue(line.words[1].is_last_word)


class TestProcessVerse(unittest.TestCase):
    def test_simple_verse(self):
        verse = process_verse("hello world\nthis is a test", artist="Test Artist")
        self.assertIsInstance(verse, Verse)
        self.assertEqual(verse.metadata["artist"], "Test Artist")
        self.assertEqual(len(verse.lines), 2)
        self.assertEqual(len(verse.lines[1].words), 4)

    def test_blank_lines_are_skipped(self):
        verse = process_verse("line one\n\nline two")
        self.assertEqual([l.text for l in verse.lines], ["line one", "line two"])

    def test_outer_whitespace_is_stripped(self):
        verse = process_verse("  hello   world  \n  test  ")
        self.assertEqual(verse.lines[0].text, "hello   world")
        self.assertEqual(verse.lines[1].text, "test")

    def test_line_ids_are_sequential(self):
        verse = process_verse("a\nb\nc")
        self.assertEqual([l.line_id for l in verse.lines], [0, 1, 2])

    def test_syllables_carry_their_line_id(self):
        verse = process_verse("banana\napple")
        self.assertTrue(all(s.line_id == 1 for s in verse.lines[1].words[0].syllables))


if __name__ == "__main__":
    unittest.main()
