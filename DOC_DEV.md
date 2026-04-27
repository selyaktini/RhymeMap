# RhymeMapper – Developer Documentation

## Table of Contents
1. [Project Overview](#overview)
2. [Project Structure](#structure)
3. [Core Data Models (`models.py`)](#models)
4. [Phonetic Processing (`phonetics.py`)](#phonetics)
5. [Rhyme Engine (`engine.py`)](#engine)
6. [Colour Visualisation (`visual.py`)](#visual)
7. [Batch Statistics (`scripts/generate_stats.py`)](#stats)
8. [Analysis & Plotting (`analysis/`)](#analysis)
9. [Makefile Commands](#makefile)
10. [Testing](#testing)
11. [Dependencies](#dependencies)
12. [Pipeline Summary](#pipeline)

---

## 1. Project Overview <a name="overview"></a>

RhymeMapper analyses rhyme schemes in rap lyrics using phonetic data. It converts words into phonemes, splits them into syllables, extracts the nucleus (vowel) and coda (following consonants), builds a rhyme signature (with consonant families to support slant rhymes), then groups and colour‑codes rhyming syllables. It also computes statistical metrics (density, diversity, etc.) and generates comparative graphs for batch analysis.

---

## 2. Project Structure <a name="structure"></a>
RhymeMapper/
├── src/ # core modules
│ ├── models.py # data classes
│ ├── phonetics.py # cleaning, phoneme extraction, syllable splitting
│ ├── engine.py # rhyme signature, label assignment
│ ├── visual.py # ANSI colour rendering
│ └── main.py # demo entry point
├── scripts/
│ └── generate_stats.py # batch analysis from CSV → stats.csv
├── analysis/ # plotting scripts
│ ├── config.py # paths, colour palette
│ ├── data_loader.py # load stats.csv, compute artist averages
│ ├── plots.py # scatter, boxplot, similarity heatmap functions
│ └── run_all_plots.py # generate all graphs automatically
├── dataset/ # input CSV files (lyrics_raw.csv, artists_sample.csv)
├── data/ # generated stats.csv and figures
├── tests/ # unit tests (test_models.py, test_phonetics.py)
├── Makefile # automation
├── requirements.txt # dependencies
├── README.md # user guide
├── HISTORY.md # version history
└── DOC_DEV.md # this file


---

## 3. Core Data Models (`src/models.py`) <a name="models"></a>

All data classes use `@dataclass` for automatic constructors and string representations.

### `Syllable`
Represents a syllable.
- `text: str` – approximate substring of the word (for colouring).
- `nucleus: str` – vowel phoneme with stress (e.g., `"AA1"`).
- `coda: list[str]` – consonant phonemes after the nucleus.
- `is_terminal: bool` – True if this is the last syllable of the word.
- `rhyme_label: str` – assigned letter (e.g., `"A"`, `"B"`).

### `Nucleus` (legacy)
Kept for backward compatibility.
- `phoneme: str` – vowel phoneme with stress.
- `stress: int` – 0, 1, or 2.
- `line_id: int`, `word_id: int`, `is_terminal: bool`.

### `Word`
- `text: str` – cleaned word.
- `syllables: list[Syllable]` – extracted from the word.
- `nuclei: list[Nucleus]` – legacy vowel list.
- `line_id: int`, `word_id: int`, `is_last_word: bool`.

### `Line`
- `text: str` – original line.
- `words: list[Word]` – words belonging to the line.
- `line_id: int`, `rhyme_label: str` – optional line label.

### `Verse`
- `lines: list[Line]` – sequence of lines.
- `metadata: dict` – e.g., `{"artist": "Eminem"}`.
- `verse_id: int`.

---

## 4. Phonetic Processing (`src/phonetics.py`) <a name="phonetics"></a>

- `clean_word(text)`: strips punctuation, lowercases, strips whitespace.
- `extract_nuclei()`: legacy, uses `g2p_en` to get vowels (kept for compatibility).
- `split_word_text(word_text, num_syllables)`: heuristic to divide a word into approximate character spans per syllable.
- `heuristic_syllables(phonemes, word_text)`: fallback when `syllabify` fails – splits phonemes into syllables by detecting vowel digits.
- `extract_syllables(word_text, line_id, word_id, is_last_word)`: main extraction. Uses `syllabify`; if that fails, calls `heuristic_syllables`. Returns a list of `Syllable` objects with text, nucleus, coda, and `is_terminal` correctly set.
- `process_line(line_text, line_id)`: splits a raw line into words, cleans each, extracts both nuclei (legacy) and syllables, and builds a `Line` object.
- `process_verse(raw_text, artist)`: entry point – splits raw text into lines, calls `process_line` for each, returns a `Verse`.

---

## 5. Rhyme Engine (`src/engine.py`) <a name="engine"></a>

### Constants
- `CONSONANT_FAMILIES`: maps phonemes (e.g., `"K"`) to groups (`"PLO"`, `"NAS"`, etc.). Used to allow slant rhymes.

### Functions
- `get_syllable_signature(syllable)`: returns a string combining the nucleus (without stress) and the coda where each consonant is replaced by its family. Example: `"AA1 K"` → `"AA-PLO"`. If no coda, returns just the nucleus.

- `assign_rhyme_labels(verse, min_occurrences=3, tail_window=None)`:  
  1. **Count** – collects signatures from all syllables (or only the last `tail_window` syllables of each line if `tail_window` is specified).  
  2. **Filter** – keeps only signatures with count ≥ `min_occurrences`.  
  3. **Label** – uses `RhymeRegistry` to assign letters (A, B, C…) to each frequent signature.  
  4. **Assign** – stores the label in `syllable.rhyme_label` and also in `line.rhyme_label` (for convenience).

### Class `RhymeRegistry`
- Internal mapping from signature to label letter. Uses alphabet `"ABCDEFGHIJKLMNOPQRSTUVWXYZ"` (wraps around if more than 26).

---

## 6. Colour Visualisation (`src/visual.py`) <a name="visual"></a>

- `COLORS`: list of ANSI background colour codes (black text). Extended palette (18 colours) to avoid collisions.
- `VisualEngine`:
  - `_get_color(label)`: returns the ANSI code for a given label, assigning a new colour on first encounter.
  - `_format_word(word)`: iterates over the word’s syllables; if a syllable has a `rhyme_label`, it wraps its `text` with the corresponding colour code.
  - `display(verse)`: prints the lyrics line by line, colouring each syllable according to its rhyme label. No line labels are shown.

---

## 7. Batch Statistics (`scripts/generate_stats.py`) <a name="stats"></a>

Reads a CSV file (default `dataset/lyrics_raw.csv`) containing columns `track_name`, `artist`, and `artist_verses` (or `raw_lyrics`). For each row:
- Calls `process_verse()` to build a `Verse`.
- Calls `assign_rhyme_labels` with `min_occurrences=3`, `tail_window=None` (analyse all syllables).
- Computes:
  - `Density`: percentage of syllables that have a `rhyme_label`.
  - `Multi`: diversity = (number of distinct rhyme signatures / total syllables) × 100.
  - `Signatures`: number of distinct rhyme signatures.
  - `Syll.`: total syllable count.
- Appends the results to a list, then exports to `data/stats.csv`.

Run with `make stats` or `python -m scripts.generate_stats`.

---

## 8. Analysis & Plotting (`analysis/`) <a name="analysis"></a>

### `config.py`
- Defines `PROJECT_ROOT`, `DATA_DIR`, `STATS_FILE`, `FIGURES_DIR`, and a default colour palette.

### `data_loader.py`
- `load_stats()`: reads `stats.csv` into a DataFrame.
- `get_artist_means()`: returns a DataFrame with mean values per artist.

### `plots.py`
- `scatter_all_morceaux()`: scatter plot Density vs Multi, one point per track, coloured by artist.
- `scatter_artist_averages()`: scatter plot of mean Density vs mean Multi per artist, with labels.
- `boxplot_density()`: boxplot of Density by artist.
- `similarity_heatmap()`: cosine similarity heatmap for tracks of a given artist (features: Density, Multi, Signatures, Syll.). Names are truncated, annotations removed if more than 15 tracks, figure size adjusts dynamically.

### `run_all_plots.py`
- Calls all plotting functions and saves the figures to `data/` as PNG files.
- Generates heatmaps only for artists with between 2 and 20 tracks (configurable).

Run with `make plots` or `python -m analysis.run_all_plots`.

---

## 9. Makefile Commands <a name="makefile"></a>

| Command          | Action                                                     |
|------------------|------------------------------------------------------------|
| `make install`   | Install dependencies from `requirements.txt`.              |
| `make test`      | Run unit tests (`./run_tests.sh`).                         |
| `make stats`     | Generate `data/stats.csv` (batch analysis).                |
| `make plots`     | Produce all graphs (scatter, boxplot, heatmaps).           |
| `make demo`      | Run the Eminem demo (`python -m src.main`).                |
| `make clean`     | Remove `__pycache__`, `data/*.png`, `data/stats.csv`.      |
| `make all`       | Execute `stats`, `plots`, `demo` in sequence.              |

---

## 10. Testing <a name="testing"></a>

Unit tests are in `tests/`:
- `test_models.py`: verifies dataclass creation.
- `test_phonetics.py`: tests cleaning, syllable extraction (on sample words).

Run with `./run_tests.sh` or `make test`. All tests should pass.

---

## 11. Dependencies <a name="dependencies"></a>

See `requirements.txt`:
g2p_en
syllabify
pandas
matplotlib
seaborn
numpy


All are available on PyPI. Install with `make install` or `pip install -r requirements.txt`.

---

## 12. Pipeline Summary <a name="pipeline"></a>
Raw lyrics → clean_word → g2p_en & syllabify → Syllable objects
↓
get_syllable_signature → signature (e.g., "AA-PLO")
↓
assign_rhyme_labels → count signatures → filter by min_occurrences → assign letters
↓
visual.py → coloured terminal output
↓
generate_stats.py → compute Density, Multi, Signatures, Syll. → stats.csv
↓
analysis/plots → scatter, boxplot, similarity heatmaps


---

**Last updated:** 2025-04-27  
**Version:** 1.0 
