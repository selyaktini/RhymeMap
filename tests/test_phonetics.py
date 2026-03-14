import unittest
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.phonetics import clean_word, extract_nuclei, process_line, process_verse
from src.models import Nucleus, Line, Verse

class TestPhonetics(unittest.TestCase):
    def test_clean_word(self):
        self.assertEqual(clean_word("Hello!"), "hello")
        self.assertEqual(clean_word("world?"), "world")
        self.assertEqual(clean_word("rock'n'roll"), "rocknroll")
        self.assertEqual(clean_word("(parenthesis)"), "parenthesis")
        self.assertEqual(clean_word("  spaces  "), "spaces")

    def test_extract_nuclei_simple_word(self):
        nuclei = extract_nuclei("hello", line_id=0, word_id=0, is_last_word=True)
        self.assertIsInstance(nuclei, list)
        self.assertGreater(len(nuclei), 0)
        nuc = nuclei[0]
        self.assertIsInstance(nuc, Nucleus)
        self.assertEqual(nuc.line_id, 0)
        self.assertEqual(nuc.word_id, 0)
        self.assertTrue(nuclei[-1].is_terminal)

    def test_extract_nuclei_non_last_word(self):
        nuclei = extract_nuclei("hello", line_id=0, word_id=0, is_last_word=False)
        self.assertFalse(nuclei[-1].is_terminal)

    def test_process_line_single_word(self):
        line_obj = process_line("hello", line_id=0)
        self.assertIsInstance(line_obj, Line)
        self.assertEqual(line_obj.text, "hello")
        self.assertEqual(line_obj.line_id, 0)
        self.assertEqual(len(line_obj.words), 1)
        word = line_obj.words[0]
        self.assertEqual(word.text, "hello")
        self.assertEqual(word.line_id, 0)
        self.assertEqual(word.word_id, 0)
        self.assertTrue(word.is_last_word)
        self.assertGreater(len(word.nuclei), 0)

    def test_process_line_multiple_words(self):
        line_obj = process_line("hello world", line_id=0)
        self.assertEqual(len(line_obj.words), 2)
        self.assertEqual(line_obj.words[0].text, "hello")
        self.assertEqual(line_obj.words[0].word_id, 0)
        self.assertFalse(line_obj.words[0].is_last_word)
        self.assertEqual(line_obj.words[1].text, "world")
        self.assertEqual(line_obj.words[1].word_id, 1)
        self.assertTrue(line_obj.words[1].is_last_word)
        self.assertGreater(len(line_obj.words[0].nuclei), 0)
        self.assertGreater(len(line_obj.words[1].nuclei), 0)

    def test_process_verse_simple(self):
        raw_text = "hello world\nthis is a test"
        verse = process_verse(raw_text, artist="Test Artist")
        self.assertIsInstance(verse, Verse)
        self.assertEqual(verse.metadata["artist"], "Test Artist")
        self.assertEqual(len(verse.lines), 2)
        self.assertEqual(verse.lines[0].text, "hello world")
        self.assertEqual(verse.lines[1].text, "this is a test")
        self.assertEqual(len(verse.lines[0].words), 2)
        self.assertEqual(len(verse.lines[1].words), 4)

    def test_process_verse_with_empty_lines(self):
        raw_text = "line one\n\nline two"
        verse = process_verse(raw_text)
        self.assertEqual(len(verse.lines), 2)
        self.assertEqual(verse.lines[0].text, "line one")
        self.assertEqual(verse.lines[1].text, "line two")

    def test_process_verse_strip_spaces(self):
        raw_text = "  hello   world  \n  test  "
        verse = process_verse(raw_text)
        self.assertEqual(verse.lines[0].text, "hello   world")
        self.assertEqual(verse.lines[1].text, "test")

if __name__ == '__main__':
    unittest.main()
