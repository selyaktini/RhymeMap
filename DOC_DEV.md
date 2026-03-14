# Project: RhymeMapper

A tool to analyze rhyme schemes in rap lyrics using phonetic data.

---

## Current Data Structures (`models.py`)

### Nucleus
Represents a stressed vowel (core of a rhyme).  
**Attributes:**  
- `phoneme`  
- `stress`  
- `line_id`  
- `word_id`  
- `is_terminal`  

### Word
Stores a word and its vowel nuclei.  
**Attributes:**  
- `text`  
- `nuclei` (list of `Nucleus`)  
- `line_id`  
- `word_id`  
- `is_last_word`  

### Line
Complete line of lyrics.  
**Attributes:**  
- `text`  
- `words` (list of `Word`)  
- `line_id`  
- `rhyme_label` (e.g., `"A"`, `"B"`)  

### Verse
Container for multiple lines (e.g., a verse or chorus).  
**Attributes:**  
- `lines` (list of `Line`)  
- `metadata` (dict, e.g., artist)  
- `verse_id`  

---

## Current Functions (`phonetics.py`)

### `clean_word(word)`
Removes punctuation and lowercases a word.

### `extract_nuclei(word_text, line_id, word_id, is_last_word)`
Uses `g2p_en` to get phonemes, filters vowels, creates `Nucleus` objects, and marks the terminal vowel if needed.

### `process_line(line_text, line_id)`
Splits a raw line into words, creates `Word` and `Line` objects, and populates nuclei.

### `process_verse(raw_text, artist="Unknown")`
Entry point that takes raw lyrics (multi-line string), processes each line, and returns a `Verse` object.

---

## Dependencies

- `g2p_en` for phonetic conversion.  
- `dataclasses` (standard in Python 3.7+).  

---

**Note:** This is a working draft. Structures and functions will evolve as the project progresses.
