"""Moroccan Darija: Arabizi spelling, schwa insertion, and language routing.

The failures these guard against are the quiet kind. An English G2P does not
refuse a Darija word, it answers -- "kayshuf" came back as K EY1 Z HH AH0 F --
so a Darija verse analysed through the English path produces a full set of
plausible-looking rhyme groups built on sounds nobody said.
"""

from __future__ import annotations

import unittest

from rhymemap import darija
from rhymemap.naming import spell_rime
from rhymemap.phonetics import phonemes_for_word, process_verse
from rhymemap.phonology import (
    CONSONANTS,
    DARIJA_CONSONANTS,
    ENGLISH_CONSONANTS,
    consonant_distance,
)

# A verse with the four things that break an English pipeline: Arabizi digits,
# emphatics, single-letter prepositions, and words written with no vowel at all.
DARIJA_VERSE = """Kanmchi f tri9 w rassi 3ali
Kolchi kayshuf melli ana ghadi
3ndi l7lm w 3ndi sber
Drt li 3liya w chft dnya"""


class TestGraphemes(unittest.TestCase):
    """The digits are the whole point: they are sounds English has no symbol for."""

    def test_digits_become_uvular_and_pharyngeal_phonemes(self):
        self.assertEqual(darija.arabizi_phonemes("3ali"), ["AIN", "AA1", "L", "IY1"])
        self.assertEqual(darija.arabizi_phonemes("7it"), ["HS", "IY1", "T"])
        self.assertEqual(darija.arabizi_phonemes("9al"), ["Q", "AA1", "L"])

    def test_digraphs_beat_their_letters(self):
        self.assertEqual(darija.arabizi_phonemes("khoya"), ["X", "OW1", "Y", "AA1"])
        self.assertEqual(darija.arabizi_phonemes("bghit"), ["B", "GH", "IY1", "T"])
        self.assertEqual(darija.arabizi_phonemes("chouf"), ["SH", "UW1", "F"])

    def test_a_glide_digraph_yields_to_a_following_vowel(self):
        """"ay" is one vowel in "kayn" and a vowel plus a consonant in "khoya"."""
        self.assertEqual(darija.arabizi_phonemes("kayn"), ["K", "AY1", "N"])
        self.assertIn("Y", darija.arabizi_phonemes("khoya"))

    def test_unknown_characters_are_dropped_not_guessed(self):
        self.assertEqual(darija.arabizi_phonemes("3a!li"), darija.arabizi_phonemes("3ali"))


class TestSchwaInsertion(unittest.TestCase):
    """Arabizi does not write the schwa, so a vowelless word has no nucleus."""

    def test_a_vowelless_word_still_gets_a_vowel(self):
        for word in ("ktbt", "chft", "drt", "bnt"):
            with self.subTest(word=word):
                phonemes = darija.arabizi_phonemes(word)
                self.assertTrue(any(p[-1].isdigit() for p in phonemes), phonemes)

    def test_the_schwa_lands_before_the_final_cluster(self):
        # [ktebt], not [ketbet]: onset "kt", nucleus, coda "bt".
        self.assertEqual(darija.arabizi_phonemes("ktbt"), ["K", "T", "AH1", "B", "T"])
        self.assertEqual(darija.arabizi_phonemes("chft"), ["SH", "AH1", "F", "T"])

    def test_a_lone_consonant_is_a_word(self):
        """Darija's one-letter prepositions. Without a nucleus they vanish."""
        for word in ("w", "f", "l", "b", "d"):
            with self.subTest(word=word):
                self.assertEqual(len(darija.arabizi_syllables(word)), 1)

    def test_a_word_initial_cluster_is_an_onset_not_a_schwa(self):
        # Darija really does allow [bgh] and [shn]; English would not.
        self.assertEqual(darija.arabizi_syllables("bghit")[0]["onset"], ["B", "GH"])
        self.assertEqual(darija.arabizi_syllables("chnou")[0]["onset"], ["SH", "N"])


class TestSyllabification(unittest.TestCase):
    def test_one_consonant_opens_the_second_syllable(self):
        """"3ndi" is [3en.di]: the "n" closes the first syllable, not the second."""
        parts = darija.arabizi_syllables("3ndi")
        self.assertEqual(len(parts), 2)
        self.assertEqual(parts[0]["coda"], ["N"])
        self.assertEqual(parts[1]["onset"], ["D"])

    def test_a_geminate_splits_across_the_break(self):
        parts = darija.arabizi_syllables("rassi")
        self.assertEqual(parts[0]["coda"], ["S"])
        self.assertEqual(parts[1]["onset"], ["S"])

    def test_a_lone_schwa_is_stressed(self):
        """Otherwise the engine drops the word away from a line end, and
        "drt"/"chft" is a real rhyme."""
        self.assertEqual(darija.arabizi_syllables("drt")[0]["nucleus"], "AH1")

    def test_an_epenthetic_schwa_beside_a_full_vowel_is_not(self):
        self.assertEqual(darija.arabizi_syllables("3ndi")[0]["nucleus"], "AH0")


class TestEmphatics(unittest.TestCase):
    def test_a_known_emphatic_word_is_respelled(self):
        self.assertEqual(darija.arabizi_phonemes("tri9")[0], "TD")
        self.assertEqual(darija.arabizi_phonemes("sber")[0], "SD")

    def test_emphasis_is_a_contrast_not_an_accent(self):
        """Same place, same manner: only the pharyngeal gesture separates them."""
        self.assertGreater(consonant_distance("S", "SD"), 0.0)
        self.assertAlmostEqual(consonant_distance("S", "SD"), consonant_distance("S", "Z"), places=6)


class TestDetection(unittest.TestCase):
    def test_arabizi_digits_are_conclusive(self):
        for word in ("3ndi", "7ala", "9alb", "3lach"):
            with self.subTest(word=word):
                self.assertTrue(darija.is_darija(word))

    def test_english_digits_are_not_arabizi(self):
        """Rap is full of 3s and 9s that mean numbers."""
        for word in ("3rd", "9mm", "2nd", "5th", "24", "365", "40oz", "2pac", "b4"):
            with self.subTest(word=word):
                self.assertFalse(darija.is_darija(word))

    def test_english_keeps_the_words_it_uses_more(self):
        """Every one of these is also everyday Darija. English wants them more."""
        for word in ("had", "men", "hit", "jay", "lil", "bent", "weld", "sir"):
            with self.subTest(word=word):
                self.assertFalse(darija.is_darija(word))

    def test_the_generated_lexicon_is_loaded(self):
        self.assertGreater(darija.lexicon_size(), 100_000)
        self.assertTrue(darija.is_darija("kolchi"))

    def test_the_lexicon_cannot_collide_with_cmudict(self):
        """It was filtered at build time, which is what lets it outrank CMUdict."""
        for word in ("money", "the", "business", "album", "camera", "rhyme"):
            with self.subTest(word=word):
                self.assertNotIn(word, darija.lexicon())


class TestVerseLanguage(unittest.TestCase):
    def test_a_darija_verse_is_recognised(self):
        self.assertEqual(darija.detect_language(DARIJA_VERSE), "dar")

    def test_darija_written_without_digits_is_recognised(self):
        """What the word list is for: not every Moroccan writes 3 and 7."""
        plain = (
            "Bghit nmchi l dar walakin ma kayn walo\n"
            "Kolchi kayghani wana kanssenna chi klma\n"
            "Rah lhal tqil w drari kaytsennaw"
        )
        self.assertEqual(darija.detect_language(plain), "dar")

    def test_an_english_verse_is_not(self):
        english = (
            "His palms are sweaty, knees weak, arms are heavy\n"
            "There's vomit on his sweater already, mom's spaghetti\n"
            "He's nervous, but on the surface he looks calm and ready"
        )
        self.assertEqual(darija.detect_language(english), "en")

    def test_one_stray_word_does_not_flip_a_verse(self):
        self.assertEqual(darija.detect_language("i got the 3ali flow tonight"), "en")

    def test_empty_text_is_english(self):
        self.assertEqual(darija.detect_language(""), "en")


class TestRouting(unittest.TestCase):
    """The single decision point: rhymemap.phonetics._syllable_parts."""

    def test_an_unmistakable_word_outranks_cmudict(self):
        self.assertEqual(phonemes_for_word("3ndi")[0], "AIN")

    def test_english_is_untouched_by_default(self):
        self.assertEqual(phonemes_for_word("banana"), ["B", "AH0", "N", "AE1", "N", "AH0"])
        self.assertEqual(phonemes_for_word("money"), ["M", "AH1", "N", "IY0"])

    def test_a_darija_verse_routes_the_words_no_list_contains(self):
        """The inflections: ktbt, ktbti, ktbna, kaykteb, ghaykteb, makatbch."""
        self.assertNotIn("X", phonemes_for_word("ykhali", language="en"))
        self.assertIn("X", phonemes_for_word("ykhali", language="dar"))

    def test_an_english_insertion_stays_english_inside_a_darija_verse(self):
        """CMUdict is asked first either way, so loanwords keep their sound."""
        self.assertEqual(
            phonemes_for_word("money", language="dar"),
            phonemes_for_word("money", language="en"),
        )

    def test_a_single_letter_preposition_is_not_the_letters_name(self):
        """CMUdict answers "w" with "double-u": three syllables of noise."""
        self.assertEqual(phonemes_for_word("w", language="dar"), ["W", "AH0"])

    def test_a_clitic_is_unstressed_but_a_short_word_is_not(self):
        """"f tri9" is said [ftri9], leaning on the word after it. Stressing the
        clitic would let w/f/l/b group with each other, and noise would stand
        where a rhyme should be -- while "drt"/"chft" must keep its stress."""
        for clitic in ("w", "f", "l", "b", "d"):
            with self.subTest(word=clitic):
                self.assertEqual(darija.arabizi_syllables(clitic)[0]["nucleus"], "AH0")
        for word in ("drt", "chft", "sber"):
            with self.subTest(word=word):
                self.assertEqual(darija.arabizi_syllables(word)[0]["nucleus"], "AH1")

    def test_the_cache_key_separates_the_languages(self):
        english = phonemes_for_word("sber", language="en")
        self.assertNotEqual(phonemes_for_word("sber", language="dar"), english)


class TestVerseIntegration(unittest.TestCase):
    def test_a_darija_verse_is_detected_and_recorded(self):
        verse = process_verse(DARIJA_VERSE, artist="Demo")
        self.assertEqual(verse.metadata["language"], "dar")

    def test_every_word_comes_out_with_a_syllable(self):
        verse = process_verse(DARIJA_VERSE, artist="Demo")
        for line in verse.lines:
            for word in line.words:
                with self.subTest(word=word.text):
                    self.assertTrue(word.syllables)

    def test_no_syllable_is_left_without_a_nucleus(self):
        verse = process_verse(DARIJA_VERSE, artist="Demo")
        for line in verse.lines:
            for word in line.words:
                for syl in word.syllables:
                    with self.subTest(word=word.text):
                        self.assertTrue(syl.nucleus)

    def test_an_explicit_language_overrides_detection(self):
        verse = process_verse("hello world\nthis is a test", language="dar")
        self.assertEqual(verse.metadata["language"], "dar")


class TestEnglishIsUnaffected(unittest.TestCase):
    """Adding a language must not retune the one that was already there."""

    def test_the_consonant_scale_is_pinned_to_english(self):
        """The widest Darija pair is wider than the widest English one.
        Normalising over both would shrink every English distance by 8%."""
        self.assertEqual(len(ENGLISH_CONSONANTS), len(CONSONANTS) - len(DARIJA_CONSONANTS))
        self.assertNotIn("AIN", ENGLISH_CONSONANTS)

    def test_known_english_distances_are_unchanged(self):
        # Measured before Darija existed.
        self.assertAlmostEqual(consonant_distance("P", "W"), 1.0, places=6)
        self.assertAlmostEqual(consonant_distance("S", "Z"), 0.2111, places=3)
        self.assertAlmostEqual(consonant_distance("S", "T"), 0.3165, places=3)

    def test_an_english_verse_still_reads_as_english(self):
        verse = process_verse("mom's spaghetti\nknees weak arms are heavy")
        self.assertEqual(verse.metadata["language"], "en")


class TestNaming(unittest.TestCase):
    def test_a_darija_rime_is_spelled_back_in_arabizi(self):
        """A group of Moroccan rhymes should be called "-a3", not "-aain"."""
        self.assertEqual(spell_rime("AA1", ["AIN"]), "ah3")
        self.assertEqual(spell_rime("IY1", ["Q"]), "ee9")
        self.assertEqual(spell_rime("UW1", ["X"]), "ookh")


if __name__ == "__main__":
    unittest.main()
