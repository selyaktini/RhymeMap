"""Tests for the core dataclasses."""

import unittest

from rhymemap.models import Line, Nucleus, Syllable, Verse, Word


class TestSyllable(unittest.TestCase):
    def test_minimal_construction(self):
        s = Syllable(text="cat", nucleus="AE1", coda=["T"])
        self.assertEqual(s.text, "cat")
        self.assertEqual(s.nucleus, "AE1")
        self.assertEqual(s.coda, ["T"])

    def test_defaults(self):
        s = Syllable(text="a", nucleus="AH0", coda=[])
        self.assertEqual(s.onset, [])
        self.assertFalse(s.is_terminal)
        self.assertEqual(s.rhyme_label, "")
        self.assertEqual((s.line_id, s.word_id, s.syl_index), (0, 0, 0))

    def test_onset_is_retained(self):
        """The similarity engine needs the onset to penalise repetition."""
        s = Syllable(text="strength", nucleus="EH1", coda=["NG", "K", "TH"], onset=["S", "T", "R"])
        self.assertEqual(s.onset, ["S", "T", "R"])

    def test_mutable_defaults_are_not_shared(self):
        a, b = Syllable(text="a", nucleus="AA1", coda=[]), Syllable(text="b", nucleus="AA1", coda=[])
        a.onset.append("K")
        self.assertEqual(b.onset, [])


class TestNucleus(unittest.TestCase):
    def test_creation(self):
        n = Nucleus(phoneme="OW1", stress=1, line_id=0, word_id=0, is_terminal=True)
        self.assertEqual(n.phoneme, "OW1")
        self.assertEqual(n.stress, 1)
        self.assertTrue(n.is_terminal)


class TestWord(unittest.TestCase):
    def test_creation(self):
        w = Word(text="hello", line_id=0, word_id=0, is_last_word=True)
        self.assertEqual(w.text, "hello")
        self.assertTrue(w.is_last_word)
        self.assertEqual(w.nuclei, [])
        self.assertEqual(w.syllables, [])

    def test_with_nuclei(self):
        n = Nucleus(phoneme="EH1", stress=1, line_id=0, word_id=0)
        w = Word(text="hello", nuclei=[n])
        self.assertEqual(w.nuclei[0].phoneme, "EH1")


class TestLine(unittest.TestCase):
    def test_creation(self):
        line = Line(text="hello world", line_id=0)
        self.assertEqual(line.words, [])
        self.assertEqual(line.rhyme_label, "")

    def test_with_words(self):
        line = Line(text="hello world", words=[Word(text="hello"), Word(text="world")])
        self.assertEqual([w.text for w in line.words], ["hello", "world"])


class TestVerse(unittest.TestCase):
    def test_creation(self):
        verse = Verse(metadata={"artist": "Eminem"}, verse_id=0)
        self.assertEqual(verse.metadata["artist"], "Eminem")
        self.assertEqual(verse.lines, [])

    def test_syllables_flattens_in_order(self):
        def word(*texts):
            return Word(text="".join(texts), syllables=[Syllable(text=t, nucleus="AA1", coda=[]) for t in texts])

        verse = Verse(lines=[
            Line(text="l0", words=[word("a", "b"), word("c")]),
            Line(text="l1", words=[word("d")]),
        ])
        self.assertEqual([s.text for s in verse.syllables()], ["a", "b", "c", "d"])

    def test_syllables_on_empty_verse(self):
        self.assertEqual(Verse().syllables(), [])


if __name__ == "__main__":
    unittest.main()
