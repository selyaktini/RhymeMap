import unittest
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.models import Nucleus, Word, Line, Verse

class TestModels(unittest.TestCase):
    def test_nucleus_creation(self):
        n = Nucleus(phoneme="OW1", stress=1, line_id=0, word_id=0, is_terminal=True)
        self.assertEqual(n.phoneme, "OW1")
        self.assertEqual(n.stress, 1)
        self.assertEqual(n.line_id, 0)
        self.assertEqual(n.word_id, 0)
        self.assertTrue(n.is_terminal)

    def test_word_creation(self):
        w = Word(text="hello", line_id=0, word_id=0, is_last_word=True)
        self.assertEqual(w.text, "hello")
        self.assertEqual(w.line_id, 0)
        self.assertEqual(w.word_id, 0)
        self.assertTrue(w.is_last_word)
        self.assertEqual(w.nuclei, [])

    def test_word_with_nuclei(self):
        n = Nucleus(phoneme="EH1", stress=1, line_id=0, word_id=0, is_terminal=True)
        w = Word(text="hello", nuclei=[n], line_id=0, word_id=0, is_last_word=True)
        self.assertEqual(len(w.nuclei), 1)
        self.assertEqual(w.nuclei[0].phoneme, "EH1")

    def test_line_creation(self):
        line = Line(text="hello world", line_id=0)
        self.assertEqual(line.text, "hello world")
        self.assertEqual(line.line_id, 0)
        self.assertEqual(line.words, [])
        self.assertEqual(line.rhyme_label, "")

    def test_line_with_words(self):
        w1 = Word(text="hello", line_id=0, word_id=0)
        w2 = Word(text="world", line_id=0, word_id=1)
        line = Line(text="hello world", words=[w1, w2], line_id=0)
        self.assertEqual(len(line.words), 2)
        self.assertEqual(line.words[0].text, "hello")
        self.assertEqual(line.words[1].text, "world")

    def test_verse_creation(self):
        verse = Verse(metadata={"artist": "Eminem"}, verse_id=0)
        self.assertEqual(verse.metadata["artist"], "Eminem")
        self.assertEqual(verse.verse_id, 0)
        self.assertEqual(verse.lines, [])

    def test_verse_with_lines(self):
        line1 = Line(text="line one", line_id=0)
        line2 = Line(text="line two", line_id=1)
        verse = Verse(lines=[line1, line2], verse_id=1)
        self.assertEqual(len(verse.lines), 2)
        self.assertEqual(verse.lines[0].text, "line one")
        self.assertEqual(verse.lines[1].text, "line two")

if __name__ == '__main__':
    unittest.main()
