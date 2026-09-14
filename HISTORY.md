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
- Created `get_syllable_signature()`: nucleus + stress + coda.
- Introduced `min_occurrences` threshold to filter rare signatures.
- Removed line labels (`[A]`, `[B]`) from the visual output.

> **Correction (v2.0).** This entry originally claimed that signatures mapped the
> coda to consonant families and that slant rhyme detection was enabled. Neither
> was true: `CONSONANT_FAMILIES` was defined but never referenced, and the
> signature used the raw coda plus the stress digit — which made matching
> *stricter* than plain exact matching, not looser. Family encoding was
> implemented in v2.0. The claim about colouring only terminal syllables by
> default was also wrong; `only_terminal` was ignored until v2.0.

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

## v2.0 (2026-09-13) – Repaired foundation

Audit of the v1.0 codebase against its own documentation, and repair of what the
audit found.

### Correctness
- **Rhyme labels no longer collide.** `RhymeRegistry` indexed a 26-letter
  alphabet modulo its length, so the 27th rhyme group silently reused the first
  group's label. *Rap God* produces 56 groups; the shipped `web/data.js` used all
  26 letters, so the published demo was mislabelling. Labels now continue
  `A…Z, AA, AB, …` without bound.
- **`only_terminal` now works.** It was accepted as a parameter, ignored, and
  passed by `generate_stats.py` in the belief that it did something.
- **`CONSONANT_FAMILIES` is wired in** behind `use_consonant_families`, off by
  default so exact matching stays reproducible as an evaluation baseline.
- **The `multi` metric checks that adjacent labels match.** It previously counted
  any two adjacent *labelled* syllables as a multisyllabic rhyme.
- **One definition per metric.** `generate_stats.py` and `analyzer.py` each
  computed a different formula under the name "Multi" and fed the same column.
  `rhymemap/metrics.py` is now the single source; `diversity` is the separated name
  for the other formula.

### Things that did not run
- `analysis/run_all_plots.py` had two `__main__` blocks, mid-file imports and an
  undefined `df`; `make plots` raised `NameError`, and the artist-similarity and
  dendrogram figures were unreachable. Rewritten, headless-safe.
- `scripts/generate_stats.py` defaulted to `dataset/lyrics_raw.csv`, which is not
  in the repository; `make stats` raised `FileNotFoundError`. It now defaults to
  the bundled corpus and takes `--input`/`--output`.
- `make demo` shelled out to `firefox`. It now uses Python's `webbrowser`.
- `make install` never fetched the NLTK corpora `g2p_en` needs, so the first
  out-of-vocabulary word raised `LookupError`.

### Performance and accuracy
- Phoneme and syllable lookups are cached in memory and on disk: **7.1s → 0.34s**
  on the bundled corpus.
- `g2p_en` was called for every word to populate `Word.nuclei`, a field no
  consumer reads. Nuclei are now derived from the syllable split.
- `G2p()` (~3.8s to construct) is built lazily, so it is only paid when a word is
  genuinely unknown. Test-suite runtime went from 4.6s to 0.008s.
- Out-of-vocabulary words are recovered by spelling first — g-dropping
  (`comin` → `coming`) and clitic restoration (`dont` → `don't`) — which resolves
  21 of the bundled corpus's 38 unknown words *more accurately* than the neural
  model did (`dont` → `D AA1 N T`, `thats` → `TH AE1 T S`).

### Engineering
- `engine.py` had no test coverage; the suite went from 15 to 78 tests.
- Added `tests/__init__.py`, removed the `sys.path` patching from every test file.
- Added `pyproject.toml` and a GitHub Actions workflow (tests + ruff on 3.10–3.12).
- Syllables now carry their `onset` and their position in the verse.
- Code and docstrings standardised on English.
- `web/data.js`, `data/stats.csv` and `.cache/` are generated, and no longer tracked.

## v3.0 (2026-09-13) – Similarity engine, chains, evaluation, viewer, audio

### The engine is now a similarity metric, not a string comparison
- `rhymemap/phonology.py` places every ARPAbet phoneme in an articulatory feature
  space: vowels by height, backness, rounding, tenseness, offglide and
  r-colouring; consonants by place, manner and voicing. Codas are compared by a
  Levenshtein alignment whose substitution cost is the feature distance between
  two consonants.
- `rhymemap/similarity.py` scores a syllable pair in [0, 1] and clusters on it.
  An identical onset scales the score down: identical onset plus identical rime
  is repetition, not rhyme, and a rime-only score rates "cat"/"cat" a perfect 1.
- `rhymemap/chains.py` finds repeated multisyllabic spans, so
  "levitatin' / devastatin' / ricochetin'" surfaces as one five-syllable chain
  instead of fifteen unrelated syllables.

### It is measured, not asserted
- `eval/` holds a 13-verse gold set, a scorer (pairwise and B-cubed), an
  ablation runner and a parameter sweep. `make eval` regenerates everything.
- The similarity engine beats the v1 baseline: pairwise F1 0.648 -> 0.865.
- The chain engine scores **worse** than the baseline at line-final grouping
  (0.454). It has the highest precision and the lowest recall of any
  configuration: it answers a different question. Kept in the table, and
  `similarity` is the default because of it.
- Metrics alone do **not** identify the artist: every classifier lands at or
  below chance and no metric separates artists (ANOVA p = 0.29-0.96). The
  artist-similarity and dendrogram figures draw structure this corpus cannot
  support.
- Annotations are model-made to a documented protocol, and the gold file says so.

### Viewer
- Hover traces a rhyme group across the verse; the sidebar isolates one on click;
  the engine selector re-analyses the verse live. Colours are hashed from the
  label, so the 26-class CSS limit is gone (Rap God has 56 groups, or 257 under
  the chain engine).
- Paste-your-own-lyrics through a stdlib local server. Analysis stays in Python
  so the browser and the terminal cannot disagree about what rhymes.

### Audio
- Word timings from JSON, WebVTT/SRT or Audacity labels drive karaoke-style
  playback. Forced alignment stays optional and uninstalled.

### Engineering
- 329 tests, up from 15. ruff clean. CI runs tests, lint and the full pipeline.

---

## v4.0 (2026-09-14) – Any song, a real package, and CI that gates the deploy

### Any song, not just captioned ones
- "Analyse any song from a link" only ever worked when the video happened to
  publish captions. Most music videos do not, so the feature failed at random
  from the outside: same code, same kind of link, "no captions".
- Lyrics now resolve through four sources in descending order of trust:
  manual captions → LRCLIB synced → automatic captions → LRCLIB plain.
- LRCLIB sits **above** automatic captions on purpose. ASR of singing mishears
  rhyme endings specifically, which is the one thing this project measures, so
  human lyrics with coarser timing beat a machine's guess with finer timing.
- `rhymemap/sources/titles.py` turns "Eminem - Rap God (Explicit) [Official
  Video] (4K)" into artist and track. A malformed query does not error, it just
  matches nothing — so a bug here is indistinguishable from a song that is
  genuinely absent everywhere.
- Extraction is retried across YouTube's player clients, which are blocked
  independently; when it is refused outright, oEmbed still yields the title and
  the lyrics lookup proceeds. Cookies handle "confirm you're not a bot", and are
  never read unless asked for.

### Honest playback
- Line-timed lyrics light the whole line. Dividing a line's span across its
  words would look plausible, render identically to measured data, and be
  fabricated. `Song.sync` is `"word"`, `"line"` or `"none"`, and the page says
  which it has and where the words came from.

### A real package
- `src/` → `rhymemap/`. A top-level `src` in site-packages collides with every
  other project that ships one.
- Only the library is distributed; `analysis` and `scripts` are repository
  tooling and were polluting site-packages with two more generic names.
- The wheel had been shipping **without `rhymemap/sources/`** — an explicit
  `packages = [...]` list does not recurse, and the repository being on
  `sys.path` hid it during development.

### CI
- Pages deployed without waiting for the tests: both workflows fired on the same
  push and ran side by side, so a commit whose tests failed still published.
- The install was written out three times and had already drifted once.
  One composite action now.
- Added: a job that builds and installs the wheel and imports it from outside
  the source tree, concurrency groups, job timeouts, read-only permissions, and
  a check that **no test touches the network** — the song loader is
  network-bound by nature, and such a test passes locally for whoever wrote it.

### Engineering
- 449 tests, up from 329. ruff clean. CI green on 3.10–3.12.
- Lines had no spaces in the DOM: words were separated by CSS margin alone, so
  copying lyrics off the page gave "butimonlygoingtogetthisonechance".

### Not verified
- No call to youtube.com or lrclib.net has ever run. The environment this was
  built in denies both hosts by policy, so every network path is exercised
  against recorded payloads through substituted seams.


---

## v4.1 (2026-09-14) – One deployment, not two

### The static build is gone
- GitHub Pages served a read-only copy: the analysis baked in at build time, no
  engine behind it. It could display an analysis and never produce one.
- So it opened with a link box that could not work. Hiding the box did not fix
  it either - the page then spent its hero explaining what it could not do, and
  people still went looking for the box. That is not a demo, it is an apology.
- One deployment now: the whole application, at a URL, with the link box
  working. `render.yaml` and a deploy button make it one click, free, no card.
- Removed with it: `scripts/build_static.py`, the Pages workflow, the
  `RHYMEMAP_STATIC` flag and every branch in the viewer that tested it.

### Why not run it in the browser instead
- Pyodide would remove the server entirely. It cannot work: a browser cannot
  fetch the lyrics. YouTube forbids cross-origin reads of caption tracks, and
  LRCLIB's CORS policy rejects browser requests too. That leaves ~20 MB of
  WebAssembly to analyse text pasted in by hand, which the server already does.

### Effects
- The backgrounds were measured and found to be, effectively, absent: aurora
  peaked at 37/255 against a #08080c page and topography averaged 0.4. Raised to
  116 and 122. Topography was also drawing disconnected scratches - the
  marching-squares step handled two of sixteen corner configurations.
