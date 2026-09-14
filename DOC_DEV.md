# RhymeMapper – Developer Documentation

1. [Overview](#overview)
2. [Structure](#structure)
3. [Data models](#models)
4. [Phonetics](#phonetics)
5. [Rhyme engine](#engine)
5b. [Similarity engine](#similarity)
5c. [Chain detection](#chains)
5d. [Audio sync](#timing)
5e. [Naming rhyme groups](#naming)
5f. [Song resolution](#sources)
6. [Metrics](#metrics)
7. [Visualisation](#visual)
8. [Batch analysis](#batch)
9. [Analysis & plotting](#analysis)
10. [Caching](#caching)
11. [Makefile](#makefile)
12. [Testing](#testing)
13. [Dependencies](#dependencies)

---

## 1. Overview <a name="overview"></a>

RhymeMapper converts lyrics into phonemes, splits them into syllables, extracts
each syllable's onset / nucleus / coda, groups syllables that rhyme, and reports
the result as coloured text, metrics, and figures.

---

## 2. Structure <a name="structure"></a>

`rhymemap/` is the distributed package. `scripts/` and `analysis/` are
repository tooling: importable from a clone, deliberately not installed, because
two more generic top-level names in site-packages is the collision the `src/` →
`rhymemap/` rename existed to remove.

```
rhymemap/                   the library (the only thing pip installs)
  models.py      dataclasses (Syllable, Nucleus, Word, Line, Verse)
  cache.py       two-tier persistent memoisation
  phonetics.py   cleaning, phoneme lookup, syllabification
  phonology.py   articulatory feature tables and distances
  similarity.py  syllable scoring and clustering
  chains.py      multisyllabic span detection
  engine.py      v1 signatures and label assignment
  labeling.py    engine registry and selection
  naming.py      names a rhyme group after its own rime
  metrics.py     the single definition of every metric
  timing.py      word timings, attached to a verse
  captions.py    caption parsing, rolling-cue dedup, line recovery
  sources/       turning a link into lyrics (see 5f)
    __init__.py  Song, and the resolver chain
    youtube.py   yt-dlp extraction, client rotation, oEmbed fallback
    lrclib.py    the LRCLIB lyrics database
    lrc.py       the LRC synced-lyrics format
    titles.py    "Artist - Track (Official Video)" -> artist, track
  visual.py      ANSI colour rendering
  analyzer.py    the corpus pipeline
  webexport.py   verse -> viewer payload
  main.py        demo CLI
scripts/                    repository tooling, not distributed
  serve_web.py         the viewer with a live analysis endpoint
  analyse_song.py      analyse one link from the terminal
  generate_stats.py    corpus -> data/stats.csv
  align_audio.py       optional forced alignment
  fetch_nltk_data.py   downloads the NLTK corpora g2p_en needs
analysis/                   figures, not distributed
  config.py      paths, palette, headless backend selection
  data_loader.py stats loading and per-artist means
  plots.py       figure functions
  run_all_plots.py  generates every figure
eval/            gold set, ablation, artist-ID experiment
tests/           unit tests
dataset/         input corpora + the demo verse
data/            generated stats.csv and figures
web/             browser viewer
```

---

## 3. Data models (`rhymemap/models.py`) <a name="models"></a>

### `Syllable`
- `text` – orthographic slice used for display. **Approximate**: the spelling is
  divided into equal spans rather than aligned to phonemes, so a boundary can sit
  a character or two off. Display only; it never affects matching.
- `nucleus` – vowel phoneme with stress, e.g. `"AA1"`.
- `coda` – consonants after the nucleus.
- `onset` – consonants before the nucleus. Kept because the similarity engine
  needs it: identical onset *and* identical rime is repetition, not rhyme.
- `is_terminal` – last syllable of the last word of a line.
- `rhyme_label` – assigned group, e.g. `"A"`, `"AB"`.
- `line_id`, `word_id`, `syl_index` – position, used to rebuild the syllable stream.

### `Nucleus`
A vowel with its stress and position. Predates `Syllable` and is retained as
public API; it is now **derived from the syllable split** rather than computed by
a second, independent phoneme pass.

### `Word`, `Line`, `Verse`
Containers. `Verse.syllables()` flattens the whole verse into one ordered list.

---

## 4. Phonetics (`rhymemap/phonetics.py`) <a name="phonetics"></a>

- `clean_word(text)` – strip punctuation, lowercase, trim.
- `lookup_variants(word)` – spellings to try against CMUdict before giving up:
  the word itself, then g-dropping (`comin` → `coming`), then clitic restoration
  (`dont` → `don't`, `hes` → `he's`). On the bundled corpus this resolves 21 of
  38 out-of-vocabulary words, and does so *more accurately* than the neural
  model, which returned `D AA1 N T` for `dont` and `TH AE1 T S` for `thats`.
- `phonemes_for_word(word)` – ARPAbet phonemes, reassembled from the syllable
  split for dictionary words and from `g2p_en` for the rest.
- `extract_syllables(...)` – the main entry point; returns `Syllable` objects with
  onset, nucleus, coda, position and `is_terminal` filled in.
- `heuristic_syllables(...)` – fallback for words CMUdict does not contain: start
  a new syllable at each vowel, attach following consonants as the coda.
- `process_line` / `process_verse` – assemble `Line` and `Verse` objects.

Both backends are constructed lazily. `G2p()` costs ~3.8s to build, and is only
needed for genuinely unknown words; building it at import time made every
command pay it, including `make test`.

---

## 5. Rhyme engine (`rhymemap/engine.py`) <a name="engine"></a>

### `label_for_index(i)`
Maps `0,1,2,…` to `A,B,…,Z,AA,AB,…`. The previous implementation indexed a
26-letter alphabet modulo its length, so the 27th group silently reused the first
group's label. A single dense verse exceeds 26 groups easily — *Rap God* produces
56 — so this corrupted real output rather than an edge case.

### `encode_coda(coda, use_consonant_families=False)`
Renders a coda as a signature fragment. With `use_consonant_families` each
consonant is replaced by its natural class from `CONSONANT_FAMILIES`
(NAS, PLO, SIB, FRI, LIQ, GLI, ASP), which is what lets `loud` and `out` — both
`AW` + plosive — group together.

> Earlier versions of this document stated that signatures used consonant
> families by default. They did not: `CONSONANT_FAMILIES` was defined and never
> referenced, and the signature used the raw coda. Family encoding is now
> implemented and available, but **off by default** so the exact-match behaviour
> stays reproducible as an evaluation baseline.

### `get_syllable_signature(syllable, use_consonant_families=False, include_stress=True)`
Returns `"{vowel}_{stress}_{coda}"`, or `""` for syllables that should be
ignored — currently unstressed syllables that are not line-final.

### `candidate_syllables(line, tail_window=None, only_terminal=False)`
Which syllables of a line may carry a label. `only_terminal` keeps just the
line-final syllable (classic end rhyme); `tail_window` keeps the last N.
`only_terminal` was previously accepted as a parameter and ignored.

### `assign_rhyme_labels(verse, ...)`
Two passes — count every signature, then label those reaching
`min_occurrences`. Returns the `RhymeRegistry` it used.

> `line.rhyme_label` exists on the model but is **not** written by this function,
> contrary to earlier documentation. Labels live on syllables.

---

## 5b. Similarity engine (`rhymemap/phonology.py`, `rhymemap/similarity.py`) <a name="similarity"></a>

The exact engine asks *"are these two signature strings equal?"*. Rhyme is not an
equality relation: "bit"/"beat" nearly rhyme, "bit"/"bought" do not, and exact
matching cannot express the difference. The similarity engine replaces the
string comparison with a score in [0, 1].

### `rhymemap/phonology.py` — the feature space

- **Vowels** are placed by height, backness, rounding, tenseness, the target of
  any offglide, and r-colouring. `vowel_distance` is their weighted distance.
- **Consonants** are described by place, manner and voicing; `manner_distance`
  encodes which manners sound alike (plosive/affricate are close, plosive/
  approximant are not).
- **Codas** are compared by `cluster_distance`: a Levenshtein alignment whose
  substitution cost is the feature distance between two consonants rather than
  0/1 on equality. This is what makes `-nt`/`-nd` near (0.10) and `-nt`/`-ks`
  far (0.48).

Both distances are rescaled by the largest distance attainable in their table.
Without that step the weighted averages never approached 1.0, the usable range
was compressed into roughly [0, 0.64], and unrelated pairs such as "cat"/"dog"
outscored genuine near-rhymes.

### `rhymemap/similarity.py` — scoring and grouping

```
score = (w_nucleus·nucleus_sim + w_coda·coda_sim + w_stress·stress_sim) / Σw
score ×= (1 − onset_identity_penalty)   if both onsets are non-empty and equal
```

The onset term is the part naive implementations miss: "cat"/"cat" and
`lookin'`/`lookin'` have a perfect rime, so a rime-only score rates them 1.0.
They are repetition, not rhyme. Two *empty* onsets are not penalised — sharing
"no onset" is not sharing an onset.

Observed ordering on the reference pairs:

| Pair | Score |
|---|---|
| cat / hat (perfect) | 1.00 |
| loud / out (slant) | 0.94 |
| bit / feet (near) | 0.87 |
| **cat / cat (repetition)** | **0.65** |
| cat / dog (unrelated) | 0.55 |
| cat / cool (unrelated) | 0.20 |

All weights live in `DEFAULT_WEIGHTS`, a single documented dict, so the
configuration is one object to defend and one object for `eval/` to sweep.

Grouping is agglomerative clustering with **average** linkage over the pairwise
distance matrix. Average linkage matters: with single linkage one loose pair
chains two unrelated rhyme families into a single group. The matrix is built
over *distinct* rhyme keys rather than syllable instances, since a dense verse
repeats sounds heavily.

### `rhymemap/labeling.py` — engine selection

Every CLI takes `--engine {exact, families, similarity}` and dispatches through
`label_verse`. `exact` is the v1 baseline, preserved so the evaluation in
`eval/` has something honest to compare against.

On the bundled corpus:

| Engine | Mean density | Mean multi | Mean groups |
|---|---|---|---|
| exact | 29.3% | 1.1% | 6.8 |
| families | 38.5% | 1.7% | 8.5 |
| similarity | 61.6% | 6.6% | 9.2 |

These numbers show the engines behave *differently*, not that one is *better* —
a higher density is equally consistent with over-grouping. Phase 4 settles that
against a hand-annotated gold set.

---

## 5c. Chain detection (`rhymemap/chains.py`) <a name="chains"></a>

Per-syllable labelling cannot represent the structure a listener actually hears.
In

    levitatin' / devastatin' / demonstratin'

every syllable gets assigned to whichever group its own sound falls in, and the
four-syllable repeat is never represented. `rhymemap/chains.py` looks for repeated
*spans* instead.

### Method

1. Flatten the verse into a syllable stream carrying `(line_id, word_id, syl_index)`.
2. Slide windows of 1..`max_window` syllables, never crossing a line break.
3. Cluster windows of equal length; the pairwise score is the mean of the
   per-syllable scores at each position.
4. Split each cluster by locality, then keep clusters recurring at least
   `min_occurrences` times.
5. Assign greedily, **longest first**, so a long chain claims its syllables
   before the fragments inside it can.

`strength = length × mean_similarity × occurrence_count` is reported for each
chain and orders chains *of equal length*.

### Three constraints that the first version lacked

**Selection order.** Ranking candidates by strength alone does not work: strength
is proportional to occurrence count, so a one-syllable "chain" recurring 153
times (strength 147) outranks a four-syllable chain recurring three times
(strength ~11). Ordering by strength let short chains claim the whole verse
before a long one was considered — the exact shredding this module exists to
prevent. Length is therefore the primary sort key.

**Per-position floor and end anchor.** A window's mean similarity can clear the
threshold on two strong positions while the rest disagree. Every position must
now reach `min_position_similarity`, and the final position must reach
`anchor_similarity`, because multisyllabic rhymes are anchored at their end.

**Locality.** Rhyme is local. Without a proximity constraint every syllable joins
some chain, because in a 1476-syllable verse drawn from ~400 distinct sounds any
span finds a partner *somewhere* — 80 lines away, where no listener hears it.
Raising the similarity threshold does not fix this; at 0.94 coverage was still
91%. `max_line_gap` (default 2, a couplet) is the constraint that was missing:

| Max line gap | Chain density | Multisyllabic coverage |
|---|---|---|
| 1 | 78.3% | 41.0% |
| 2 (default) | 86.0% | 47.6% |
| 4 | 91.9% | 54.9% |
| none | 99.3% | 79.7% |

### Result on the demo verse

Detection takes ~2.5s for 1476 syllables. The strongest long chains it recovers:

| Length | Occurrences | Similarity | Example |
|---|---|---|---|
| 5 | 4 | 0.94 | `straight face lookin' boy` / `take place lookin' boy` |
| 5 | 3 | 0.93 | `is ricochetin'` / `I'm devastatin'` / `it's levitatin'` |
| 5 | 2 | 0.96 | `a Rap God Rap God` / `the back nod back nod` |
| 5 | 2 | 0.96 | `honesty's brutal` / `honestly futile` |

### Metrics

`chain_metrics(verse, chains)` reports `chain_density`, `multi_score` (coverage
by chains of length ≥ 2), `chains`, `longest_chain` and `mean_chain_length`.

`metrics.compute_metrics` stays the engine-agnostic view and agrees on density.
Its `multi` runs about two points higher because it also counts two *adjacent*
occurrences of a one-syllable chain as a run, which `chain_metrics` does not.

---

## 5d. Audio sync (`rhymemap/timing.py`, `scripts/align_audio.py`) <a name="timing"></a>

`notes.md` has asked for this since March: attach a time to each word so the
rhymes light up along with the track.

Forced alignment is **not** a dependency. Every aligner is heavy — WhisperX pulls
in torch, aeneas needs espeak and ffmpeg — so `scripts/align_audio.py` uses
whichever happens to be installed and prints the options when neither is.
Nothing under `rhymemap/` imports them, and `make install` is unchanged.

`rhymemap/timing.py` reads what those tools emit:

| Format | Shape |
|---|---|
| JSON | `[{"word": "palms", "start": 0.51, "end": 0.78}, ...]`, or a `{"words": [...]}` wrapper (WhisperX) |
| WebVTT / SRT | one cue per word |
| Audacity labels | `start<TAB>end<TAB>word` |

`attach_timings` walks the verse and the timing list together with a small
lookahead. Timing files and lyrics disagree constantly — ad-libs, censored words,
`y'all` against `yall` — so an unmatched word is skipped rather than dragging
every later word out of step. Syllable times are interpolated across each word by
syllable count.

In the viewer, `setupAudio` only shows the player when the verse has both an
audio file and timings; otherwise the page behaves exactly as before.

### Two things that had to be fixed to make playback work

**Seeking needs HTTP Range support.** `SimpleHTTPRequestHandler` does not
implement it, and a browser will not seek within media served without it:
setting `audio.currentTime` silently snapped back to 0, so the track could be
played from the start but never scrubbed. `Handler.send_head` now serves
`206 Partial Content` and advertises `Accept-Ranges`.

**`timeupdate` does not fire on a paused element.** Scrubbing a paused track left
the highlight where it was, so the viewer also listens for `seeked` and
`loadedmetadata`.

The highlight lookup is a binary search over the syllables sorted by start time.
`timeupdate` fires about four times a second and a linear scan of ~1500
syllables each time is wasteful enough to show up on a phone.

---

## 5e. Naming rhyme groups (`rhymemap/naming.py`) <a name="naming"></a>

Groups were labelled `A`, `B`, … `Z`, `AA`, `AB`, in order of first appearance.
That is a spreadsheet column, not a name, and it fails three ways:

* **It says nothing.** "Group AB" tells you nothing about the sound, and a dense
  verse produces 257 of them.
* **It is unstable.** The letter depends on reading order, so the same rhyme is
  called something different in every song — and under every engine on the same
  song. Nothing can be compared or remembered.
* **It cannot be spoken.** People say "the *-ames* rhyme" or "the *lookin' boy*
  chain". Nobody says "group AB".

A group is now named after its own rime:

| Engine | Before | After |
|---|---|---|
| similarity | `A` | `-im` — *women, him, slim* |
| similarity | `D` | `-ike` — *like, rhyme, while* |
| similarity | `Q` | `-eel` — *feel, wheel, appeal* |
| chains | `F` | `straight face lookin boy` |
| chains | `G` | `im devastatin` — *is ricochetin, its levitatin* |

Because the name comes from the phonetics it is **stable**: the same rhyme is
called the same thing everywhere. The colour is hashed from the name, so colour
becomes stable too — `-ames` is the same hue in every song.

### How a name is chosen

**Spelling is borrowed, not generated.** English orthography is too irregular to
synthesise from ARPAbet (`-ite` or `-yte`? `-oh` or `-ow`?), so the name is the
tail of a word that is actually in the verse. The exact rime is kept alongside
for anyone who wants it.

**The tail starts at the labelled syllable's vowel.** `rime_from_spelling`
counts vowel *runs*, so a digraph counts once, and indexes forward from the
start — which is why `shame` gives `-ame` rather than the silent `-e`, and
`asteroid` with its rime in syllable 2 gives `-oid` rather than `-asteroid`.

**The rime is the modal one.** A similarity-clustered group holds near-matches,
not identical sounds. Taking the first member's rime made the label and the
phonetics disagree — `-im` labelled a group printed as `IH T`. The commonest
`(nucleus, coda)` is what the group is heard as.

**Short tails win for the label; content words win for the examples.** The
shortest on-rime tail is the rime with least onset still clinging to it, so
`-or` from *for* beats `-ormal` from *normal*. Function words are demoted only
in the *examples*, where a reader needs something worth looking at.

**A label must contain a real vowel.** The letter-name in "J.J. Fad" once
labelled an entire group `-j`; `y` counts as a vowel only when it is not the
first letter, or a group of `AE` words comes out as `-yeah` instead of `-eah`.

**Collisions take another spelling before a number.** Two groups can honestly
land on `-at` while sounding different (`AH T` and `AE T`). The second takes its
next-best real spelling — `-atter` — and only falls back to `-at 2` if it has
none.

### Where it runs

`rename_groups(verse, chains=None)` runs after an engine has finished, from
`labeling.label_verse`, so every engine gets it and the naming has the completed
grouping to work from. Descriptions are left on `verse.metadata["groups"]` and
travel to the viewer with the rime, a few example words, and a **position map**
— where each occurrence falls across the verse. Two groups with the same count
can be spread evenly or bunched into one passage, and that difference is most of
what a rhyme scheme *is*.

---

## 5f. Song resolution (`rhymemap/sources/`) <a name="sources"></a>

Turning a YouTube link into lyrics the analyser can read.

### Why it is a chain and not a fetch

The first version read captions and stopped. That is correct when captions
exist and useless when they do not — and captioning a music video is optional,
so most do not have them. The feature appeared to break at random: identical
code, identical kind of link, "no captions, so there are no lyrics to read".

Four sources are tried in descending order of **trust**, not convenience:

| | provider | text from | timing |
|---|---|---|---|
| 1 | `captions` (manual) | a person | per word |
| 2 | `lrclib-synced` | a person | per line |
| 3 | `captions` (automatic) | a machine | per word |
| 4 | `lrclib-plain` | a person | none |

The one non-obvious placement is 2 above 3. Automatic captions carry *finer*
timing, so ordering by timing quality would put them second. They are ordered
below because ASR of singing mishears rhyme endings specifically — the vowel and
coda at the end of a line, which is exactly the signal this project measures.
Better text with coarser timing beats worse text with finer timing.

### Line timing is never converted to word timing

`Song.sync` is `"word"`, `"line"` or `"none"`, and a line-timed song keeps its
`LyricLine`s all the way to the viewer, which highlights whole lines.

Dividing a line's span across its words by syllable count would look plausible
and would render identically to measured data. It would be fabricated. The rule
is that the page never displays a precision the source does not have.

### `titles.py`

`"Eminem - Rap God (Explicit) [Official Video] (4K)"` → artist `Eminem`, track
`Rap God`.

This is the component most likely to fail silently. A malformed query does not
error, it simply matches nothing — so a parsing bug is indistinguishable from a
song genuinely absent from every database.

- A bracketed group is dropped only when **every** word in it is packaging, so
  `(Remix)`, `(Interlude)` and `(Album Version)` survive.
- A trailing dash-separated segment is dropped when it is packaging
  (`"Lose Yourself - Official Video"`), except when only two segments remain and
  the last could be a real name — `"Joey Bada$$ - 1999"` keeps its title.
- Channel suffixes are stripped only with a separator before them. `VEVO` is the
  exception: it is a brand, always upper-case and always glued on. Without that
  distinction `"NFrealmusic"` became `"NFreal"`.
- yt-dlp's own `track`/`artist` fields win when present; they are metadata from a
  matched release, not a guess.

### `youtube.py`

Two behaviours exist because of how YouTube acts rather than what it documents.

**Client rotation.** YouTube serves different payloads to its Android app, its
TV interface and its website, and blocks them independently. A refusal for one
client is often served for another, so extraction is retried across clients. The
list is intersected with the clients the installed yt-dlp actually knows, so a
version bump cannot make this pass a name yt-dlp rejects; if the list cannot be
read at all it falls back to yt-dlp's own default rather than failing.

**oEmbed fallback.** When extraction is refused outright, YouTube's public oEmbed
endpoint still returns the title and channel. That is all a lyrics database
needs, so a hard block degrades to a lyrics-only result instead of an error.

Cookies (`RHYMEMAP_COOKIES_FROM_BROWSER`, `RHYMEMAP_COOKIES`) are the documented
fix for "Sign in to confirm you're not a bot". They are never read by default:
reaching into a browser's cookie store is the user's decision.

### Testing something that cannot be reached

Every network call sits behind one substitutable function — `_import_yt_dlp()`
and `lrclib.fetch` — and everything else is pure. The whole chain is exercised
against recorded payloads: ordering, oEmbed recovery, client rotation, and a
resolver → analyser → payload run asserting the line timings align one-to-one
with the rendered lines.

Two notes for anyone extending this:

- Do **not** fake yt-dlp with `patch.dict(sys.modules, ...)`. It restores by
  clearing the dict and refilling it, which evicts everything imported inside
  the window; the analysis imports numpy, scipy and g2p_en lazily, so the next
  request dies with "cannot load module more than once per process".
- Do **not** give a network function a default of `fetcher=fetch`. A default
  binds at import time and can never afterwards be replaced.
- `load()` takes no fetcher, so a test calling it goes to the real lyrics
  database unless `lrclib.fetch` is substituted too. One test did exactly this
  and passed for weeks.

`scripts/check_no_network.py` (`make test-offline`, and a CI step) runs the suite
with every non-loopback connection blocked. It also blocks whatever `HTTPS_PROXY`
points at: behind a proxy a request to lrclib.net opens a socket to `127.0.0.1`
and the proxy makes the real call, so loopback-only filtering reports success
while traffic is leaving the machine. The first version of this script had that
hole, passed locally, and CI — with no proxy — caught four connections to
lrclib's addresses on the next push.

---


## 6. Metrics (`rhymemap/metrics.py`) <a name="metrics"></a>

| Metric | Definition |
|---|---|
| `density` | % of syllables carrying any rhyme label |
| `multi` | % of syllables inside a run of ≥2 consecutive syllables sharing **the same** label |
| `diversity` | distinct groups / total syllables |
| `signatures` | number of distinct groups |
| `syllables` | total syllable count |

> Two different formulas were previously both exported as "Multi":
> `generate_stats.py` computed signature *diversity*, while `analyzer.py` counted
> adjacent labelled syllables **without checking the labels matched**. They fed
> the same CSV column and the same plots. The names are now distinct and the
> adjacency check is real.

---

## 7. Visualisation (`rhymemap/visual.py`) <a name="visual"></a>

`VisualEngine.display(verse, legend=False)` prints the verse with each labelled
syllable on a coloured background, and optionally lists the groups by size.
Escape codes are suppressed when `NO_COLOR` is set or stdout is not a TTY.

---

## 8. Batch analysis <a name="batch"></a>

`rhymemap/analyzer.py` owns the corpus pipeline; `scripts/generate_stats.py` is a thin
CLI over it. Previously each file carried its own copy of the loop with divergent
metric definitions.

```bash
python -m scripts.generate_stats --input CSV --output CSV [--min-occurrences N]
                                 [--tail-window N] [--only-terminal] [--max-rows N]
```

The default input is `dataset/artists_sample.csv`. The previous default pointed
at `dataset/lyrics_raw.csv`, which is not in the repository, so the target failed
with a traceback; a missing or malformed dataset now produces an actionable
message.

---

## 9. Analysis & plotting (`analysis/`) <a name="analysis"></a>

`run_all_plots.py` generates: `scatter_all`, `artist_averages`,
`boxplot_density`, `artist_similarity`, `artist_dendrogram`, and a per-track
similarity heatmap for each featured artist present in the data.

> This module previously did not run at all: it had two `__main__` blocks, imports
> in the middle of the file, and referenced an undefined `df`, so `make plots`
> raised `NameError`. The artist-similarity and dendrogram figures were
> unreachable. It also called `plt.show()` unconditionally, which blocks on a
> headless machine; the backend is now selected accordingly and figures are
> closed after saving.

---

## 10. Caching (`rhymemap/cache.py`) <a name="caching"></a>

Phoneme and syllable lookups are memoised in memory and in `.cache/*.json`.
Bump `CACHE_VERSION` when the stored format or lookup semantics change. Disk I/O
is best-effort: a read-only checkout degrades to the memory tier.

Measured on `dataset/artists_sample.csv`: **7.1s cold → 0.34s warm**.

---

## 11. Makefile <a name="makefile"></a>

| Command | Action |
|---|---|
| `make install` | dependencies + NLTK corpora |
| `make test` | unit tests |
| `make demo` | colour-code the demo verse |
| `make stats` | corpus → `data/stats.csv` |
| `make plots` | all figures |
| `make web` | export `web/data.js` and open the viewer |
| `make clean` | remove caches and generated files |

`make web` opens the viewer through Python's `webbrowser` module; it previously
shelled out to `firefox`.

---

## 12. Testing <a name="testing"></a>

`./run_tests.sh` runs `unittest discover` with the project root as the top-level
import directory, so no test needs to patch `sys.path`.

- `test_models.py` – dataclass behaviour
- `test_phonetics.py` – cleaning, backoff, syllabification
- `test_engine.py` – signatures, label space, candidate selection, labelling
- `test_phonology.py` – feature tables and distances
- `test_similarity.py` – syllable scoring, clustering, label assignment
- `test_chains.py` – multisyllabic span detection
- `test_naming.py` – how a group gets its name
- `test_metrics.py` – metric definitions
- `test_timing.py` – timing formats and attachment
- `test_captions.py` – caption parsing, dedup, line recovery
- `test_titles.py` – YouTube titles → artist and track
- `test_lrc.py` – the LRC synced-lyrics format
- `test_lrclib.py` – query building, candidate scoring, lookup order
- `test_resolver.py` – the source chain, rotation, oEmbed, end to end
- `test_sources.py` – URL shapes, caption selection, error messages
- `test_server_cache.py` – the `/api/song` route and its cache
- `test_web.py` – payload shape and the server's static handling
- `test_layout.py` – the project's own paths and packaging
- `test_eval.py` – scoring metrics

Tests needing the neural fallback skip themselves when the corpora are absent.

**Nothing in the suite touches the network.** Both network seams
(`_import_yt_dlp`, `lrclib.fetch`) are substituted; a test that reached
youtube.com or lrclib.net would be flaky in CI and would silently depend on a
third party's uptime. See 5f for two patterns to avoid when adding more.

---

## 13. Dependencies <a name="dependencies"></a>

See `requirements.txt`. Note that `g2p_en` depends on `distance`, which does not
build against setuptools 60+; the README and CI workflow both document the
workaround.

---

**Version:** 2.0.0
