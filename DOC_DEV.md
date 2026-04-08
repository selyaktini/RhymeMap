# Project: RhymeMapper

A tool to analyze rhyme schemes in rap lyrics using phonetic data.

---

## Current Data Structures (`models.py`)

### Syllable
Represents a syllable (nucleus + coda).  
**Attributes:**  
- `text` (approximate substring of the word)  
- `nucleus` (vowel phoneme, e.g., `"AA1"`)  
- `coda` (list of consonant phonemes after the nucleus)  
- `is_terminal` (True if last syllable of the word)  
- `rhyme_label` (e.g., `"A"`, `"B"`)

### Nucleus
Represents a stressed vowel (core of a rhyme).  
**Attributes:**  
- `phoneme`  
- `stress`  
- `line_id`  
- `word_id`  
- `is_terminal`  

### Word
Stores a word and its syllables (and nuclei for compatibility).  
**Attributes:**  
- `text`  
- `syllables` (list of `Syllable`)  
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

### `extract_syllables(word_text, line_id, word_id, is_last_word)`
Uses `syllabify` (or a heuristic fallback) to split a word into syllables, returning a list of `Syllable` objects. Each syllable stores its nucleus and coda.

### `process_line(line_text, line_id)`
Splits a raw line into words, cleans each word, extracts both nuclei and syllables, and creates `Word` and `Line` objects.

### `process_verse(raw_text, artist="Unknown")`
Entry point that takes raw lyrics (multi-line string), processes each line, and returns a `Verse` object.

---

## Rhyme Labeling (`engine.py`)

### `get_syllable_signature(syllable)`
Builds a rhyme signature: nucleus without stress + coda where each consonant is replaced by its family (NAS, PLO, SIB, FRI, LIQ, GLI, ASP).  
Example: `"AA1 K"` → `"AA-PLO"`.

### `assign_rhyme_labels(verse, min_occurrences=3, only_terminal=True)`
- Counts signatures of terminal syllables (last syllable of last word of each line).  
- Keeps only signatures that appear at least `min_occurrences` times.  
- Assigns a letter (A, B, C…) to each frequent signature.  
- Stores the label in `syllable.rhyme_label` and in `line.rhyme_label`.

---

## Visualization (`visual.py`)

### `VisualEngine`
- Maps rhyme labels to ANSI background colors.  
- `_format_word(word)`: concatenates colored syllables (if a syllable has a label) or plain text.  
- `display(verse)`: prints the lyrics with colored syllables, no line labels.

---

## Dependencies

- `g2p_en` for phonetic conversion.  
- `syllabify` for syllable splitting (uses CMUdict).  
- `dataclasses` (standard in Python 3.7+).  

---

**Note:** This is the final version used for the rhyme scheme visualization. The heuristic fallback in `extract_syllables` handles words not found in the CMU dictionary.
