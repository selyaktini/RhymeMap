# RhymeMapper History

## v0.1 (2025-03-14) – MVP
- First working version.
- Rhyme detection based on the last nucleus (vowel) of each line.
- Automatic label assignment (A, B, C…) to lines.
- Basic terminal output with line labels.

## v0.2 (2025-03-20) – Syllable extraction
- Replaced nucleus‑only detection with full syllable analysis.
- Integration of `syllabify` for phonetic syllable splitting.
- Each syllable stores its text, nucleus (vowel + stress), and coda (following consonants).
- Heuristic fallback for unknown words (using `g2p_en` and vowel detection).

## v0.3 (2025-03-28) – Rhyme signatures & consonant families
- Created `get_syllable_signature()`: nucleus (without stress) + coda mapped to consonant families (NAS, PLO, SIB, FRI, LIQ, GLI, ASP).
- Enabled slant rhyme detection (e.g., `loud` / `out` share `AW-PLO`).
- Introduced `min_occurrences` threshold to filter rare signatures.
- Colored only terminal syllables (last syllable of last word of each line) by default.
- Removed line labels (`[A]`, `[B]`) from the visual output.

## v0.4 (2025-04-15) – Batch analysis & metrics
- Created `scripts/generate_stats.py` to process a CSV of lyrics (`dataset/lyrics_raw.csv`).
- Computed metrics per morceau:
  - **Density** = % of syllables participating in a rhyme.
  - **Multi** = diversity of rhyme signatures (number of distinct signatures / total syllables × 100).
  - **Signatures** = number of distinct rhyme signatures.
  - **Syll.** = total number of syllables.
- Exported results to `data/stats.csv`.

## v1.0 (2025-04-27) – Final version for defense
- Added `analysis/` module with reusable plotting functions:
  - `config.py`: paths, colour palette.
  - `data_loader.py`: load stats, compute artist averages.
  - `plots.py`: scatter plots (all tracks & artist averages), boxplots, similarity heatmaps.
  - `run_all_plots.py`: generate all graphs automatically.
- Created `Makefile` to automate:
  - `make install` – install dependencies.
  - `make test` – run unit tests.
  - `make stats` – generate stats CSV.
  - `make plots` – produce all figures.
  - `make demo` – run the Eminem example.
  - `make clean` – remove generated files.
  - `make all` – full pipeline.
- Fully documented code (docstrings, comments).
- Restructured project directories (moved scripts into `analysis/` and `scripts/`).
- Updated `README.md`, `DOC_DEV.md`, and `HISTORY.md` for clarity.
- Ready for oral defense.
