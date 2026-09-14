"""Text -> phonemes -> syllables.

Pipeline for one word:

    clean_word -> phonemes_for_word -> extract_syllables -> [Syllable]

Phoneme lookup prefers CMUdict (a plain dictionary hit) and only falls back to
``g2p_en``'s neural grapheme-to-phoneme model for out-of-vocabulary words, which
is where rap lyrics spend a lot of their vocabulary ("finna", "skrrt", ad-libs).
Both tiers are memoised on disk; see ``rhymemap/cache.py``.
"""

from __future__ import annotations

import re

from . import darija
from .cache import PHONEME_CACHE, SYLLABLE_CACHE
from .models import Line, Nucleus, Syllable, Verse, Word

# ---------------------------------------------------------------------------
# Lazy backends
#
# Constructing G2p() costs ~4.6s (it loads a tagger and model weights). Building
# it at import time made every command pay that, including `make test`, which
# for in-vocabulary words never needs it at all. Both backends are therefore
# created on first use.
# ---------------------------------------------------------------------------

_g2p = None


class PhoneticBackendUnavailable(RuntimeError):
    """Raised when an out-of-vocabulary word needs g2p_en and it is not usable."""


def g2p_available() -> bool:
    """True if the neural fallback can actually run (package + NLTK corpora)."""
    try:
        _get_g2p()
        return True
    except PhoneticBackendUnavailable:
        return False


def _get_g2p():
    global _g2p
    if _g2p is None:
        try:
            from g2p_en import G2p

            _g2p = G2p()
        except ImportError as exc:
            raise PhoneticBackendUnavailable(
                "g2p_en is required for out-of-vocabulary words.\n"
                "Install it with: pip install -r requirements.txt"
            ) from exc
        except LookupError as exc:
            raise PhoneticBackendUnavailable(
                "g2p_en needs NLTK corpora that are not installed.\n"
                "Fetch them with: python -m scripts.fetch_nltk_data"
            ) from exc
    return _g2p


def clean_word(text: str) -> str:
    """Strip punctuation, lowercase, and trim whitespace."""
    return re.sub(r"[^\w\s]", "", text).lower().strip()


def extract_nuclei(word_text: str, line_id: int, word_id: int, is_last_word: bool,
                   language: str = "en") -> list[Nucleus]:
    """Vowel phonemes of a word as Nucleus objects.

    Retained as public API. Note that ``process_line`` no longer calls this:
    it derives the same objects from the syllable split, which avoids a second
    phoneme lookup per word.
    """
    vowels = [p for p in phonemes_for_word(word_text, language) if p and p[-1].isdigit()]
    nuclei = [
        Nucleus(
            phoneme=v,
            stress=int(v[-1]),
            line_id=line_id,
            word_id=word_id,
            is_terminal=False,
        )
        for v in vowels
    ]
    if is_last_word and nuclei:
        nuclei[-1].is_terminal = True
    return nuclei


def nuclei_from_syllables(syllables, line_id: int, word_id: int, is_last_word: bool) -> list[Nucleus]:
    """Build the Nucleus list from an already-computed syllable split.

    Equivalent to ``extract_nuclei`` but free: the phonemes were resolved when
    the syllables were built.
    """
    nuclei = []
    for syl in syllables:
        phoneme = syl.nucleus
        if not phoneme:
            continue
        stress = int(phoneme[-1]) if phoneme[-1].isdigit() else 0
        nuclei.append(
            Nucleus(
                phoneme=phoneme,
                stress=stress,
                line_id=line_id,
                word_id=word_id,
                is_terminal=False,
            )
        )
    if is_last_word and nuclei:
        nuclei[-1].is_terminal = True
    return nuclei


# ---------------------------------------------------------------------------
# Syllabification
# ---------------------------------------------------------------------------


def split_word_text(word_text: str, num_syllables: int) -> list[str]:
    """Split a word's spelling into ``num_syllables`` display chunks.

    Approximate by construction: it divides the orthography into equal spans
    rather than aligning letters to phonemes, so the coloured boundaries can sit
    a character or two off the true syllable break. It only affects display.
    """
    if num_syllables <= 1:
        return [word_text]
    length = len(word_text)
    step = length / num_syllables
    parts = []
    for i in range(num_syllables):
        start = int(i * step)
        end = int((i + 1) * step) if i < num_syllables - 1 else length
        parts.append(word_text[start:end])
    return parts


def _cluster_to_list(cluster) -> list[str]:
    """Normalise a syllabify Cluster/Empty into a list of phoneme strings."""
    if not cluster:
        return []
    return [p for p in str(cluster).split() if p and p != "empty"]


def heuristic_syllables(phonemes: list[str], word_text: str) -> list[Syllable]:
    """Fallback split used when the word is not in CMUdict.

    Starts a new syllable at each vowel and attaches the following consonants to
    it as the coda. Crude, but it keeps unknown words in the analysis instead of
    dropping them.
    """
    groups: list[list[str]] = []
    current: list[str] = []
    for phoneme in phonemes:
        current.append(phoneme)
        if any(c.isdigit() for c in phoneme):
            groups.append(current)
            current = []
    if current:
        if groups:
            groups[-1].extend(current)
        else:
            groups.append(current)

    texts = split_word_text(word_text, len(groups)) if groups else [word_text]
    syllables = []
    for i, group in enumerate(groups):
        onset: list[str] = []
        nucleus = ""
        coda: list[str] = []
        for j, phoneme in enumerate(group):
            if phoneme and phoneme[-1].isdigit():
                nucleus = phoneme
                onset = [str(p) for p in group[:j]]
                coda = [str(p) for p in group[j + 1:]]
                break
        if not nucleus:
            # Consonant-only fragment; keep it as its own unit.
            nucleus = " ".join(group)
        syllables.append(
            Syllable(
                text=texts[i] if i < len(texts) else word_text,
                nucleus=nucleus,
                coda=coda,
                onset=onset,
                is_terminal=False,
                syl_index=i,
            )
        )
    return syllables


# Clitics that ``clean_word`` flattens by stripping the apostrophe. CMUdict has
# the apostrophised forms, so restoring them recovers the real pronunciation.
_CLITICS = ("ll", "ve", "re", "nt", "s", "d", "m")


def lookup_variants(word: str):
    """Spelling variants to try against CMUdict before giving up on a word.

    Rap lyrics are full of two patterns that push words out of the dictionary
    for no phonetic reason: g-dropping ("comin'") and apostrophes removed during
    cleaning ("dont", "yall"). Both are recoverable by spelling, which is both
    cheaper and more accurate than asking the neural model to guess.
    """
    yield word
    if word.endswith("in"):
        yield word + "g"                      # comin -> coming
    for clitic in _CLITICS:
        if word.endswith(clitic) and len(word) > len(clitic) + 1:
            base = word[: -len(clitic)]
            yield base + "n't" if clitic == "nt" else base + "'" + clitic


def _syllabify_one(word_text: str) -> list[dict]:
    """Run syllabify on one spelling; ``[]`` if it is not in the dictionary."""
    try:
        from syllabify import syllabify

        result = syllabify(word_text)
    except Exception:
        return []

    word_obj = None
    if getattr(result, "words", None):
        word_obj = result.words[0]
    elif hasattr(result, "syllables"):
        word_obj = result
    if word_obj is None:
        return []

    return [
        {
            "onset": _cluster_to_list(syl.onset),
            "nucleus": str(syl.nucleus),
            "coda": _cluster_to_list(syl.coda),
        }
        for syl in word_obj.syllables
    ]


def _syllable_parts(word_text: str, language: str = "en") -> list[dict]:
    """Return ``[{onset, nucleus, coda}, ...]`` for a word, cached on disk.

    The one place where a word's language is decided. Everything downstream --
    phonemes, syllables, nuclei, signatures, chains -- is built from what this
    returns, so routing here is enough to carry a Darija word through the whole
    engine without any other stage knowing there are two languages.

    A Moroccan verse switches language mid-bar, so the choice is per word rather
    than per song, and it goes in three tiers:

    1. Unmistakably Darija -- an Arabizi digit, or the curated word list. These
       outrank CMUdict, which is the point of curating them.
    2. CMUdict, through the spelling variants above.
    3. Whatever CMUdict could not name, once the verse is known to be Darija
       (see ``darija.detect_language``). In an English verse this stays with the
       neural model, which is right for the ad-libs and slang that put an
       English word out of vocabulary; in a Darija verse that model has nothing
       useful to say -- it read "kayshuf" as K EY1 Z HH AH0 F -- so Darija takes
       it. This tier is what covers the inflections no word list can: Darija
       turns one verb into ktbt, ktbti, ktbna, kaykteb, ghaykteb, makatbch.
    """
    key = word_text if language == "en" else f"{language}:{word_text}"
    cached = SYLLABLE_CACHE.get(key)
    if cached is not None:
        return cached

    is_darija = darija.is_darija(word_text) or (
        language == "dar" and word_text in darija.DARIJA_CLITICS
    )
    if is_darija:
        parts = darija.arabizi_syllables(word_text)
    else:
        parts = []
        for variant in lookup_variants(word_text):
            parts = _syllabify_one(variant)
            if parts:
                break
        if not parts and language == "dar":
            parts = darija.arabizi_syllables(word_text)

    SYLLABLE_CACHE.set(key, parts)
    return parts


def phonemes_for_word(word_text: str, language: str = "en") -> list[str]:
    """Return ARPAbet phonemes for a word, using CMUdict then g2p.

    Results are cached in memory and on disk, keyed by the cleaned word.
    """
    if not word_text:
        return []

    key = word_text if language == "en" else f"{language}:{word_text}"
    cached = PHONEME_CACHE.get(key)
    if cached is not None:
        return list(cached)

    # syllabify already resolves in-vocabulary words against CMUdict, so the
    # phonemes can be reassembled from the syllable split instead of loading a
    # second copy of the dictionary. Materialising CMUdict here cost more than
    # the neural fallback it was meant to avoid.
    parts = _syllable_parts(word_text, language)
    if parts:
        phonemes = []
        for part in parts:
            phonemes.extend(part["onset"])
            if part["nucleus"]:
                phonemes.append(part["nucleus"])
            phonemes.extend(part["coda"])
    else:
        # Genuinely out of vocabulary: pay for the neural model, once, ever.
        phonemes = [p for p in _get_g2p()(word_text) if p != " "]

    PHONEME_CACHE.set(key, phonemes)
    return phonemes


def extract_syllables(word_text: str, line_id: int, word_id: int, is_last_word: bool,
                      language: str = "en") -> list[Syllable]:
    """Split a word into Syllable objects, with position metadata filled in."""
    if not word_text:
        return []

    parts = _syllable_parts(word_text, language)
    if not parts:
        # Not in CMUdict: fall back to the phoneme heuristic.
        syllables = heuristic_syllables(phonemes_for_word(word_text, language), word_text)
    else:
        texts = split_word_text(word_text, len(parts))
        syllables = [
            Syllable(
                text=texts[i] if i < len(texts) else word_text,
                nucleus=part["nucleus"],
                coda=list(part["coda"]),
                onset=list(part["onset"]),
                syl_index=i,
            )
            for i, part in enumerate(parts)
        ]

    for i, syl in enumerate(syllables):
        syl.line_id = line_id
        syl.word_id = word_id
        syl.syl_index = i
        syl.is_terminal = bool(is_last_word and i == len(syllables) - 1)
    return syllables


# ---------------------------------------------------------------------------
# Line / verse assembly
# ---------------------------------------------------------------------------


def process_line(line_text: str, line_id: int, language: str = "en") -> Line:
    """Build a Line from raw text."""
    raw_words = line_text.split()
    line_obj = Line(text=line_text, line_id=line_id)

    for i, raw_word in enumerate(raw_words):
        cleaned = clean_word(raw_word)
        is_last = i == len(raw_words) - 1
        syllables = extract_syllables(cleaned, line_id, i, is_last, language)
        line_obj.words.append(
            Word(
                text=cleaned,
                syllables=syllables,
                nuclei=nuclei_from_syllables(syllables, line_id, i, is_last),
                line_id=line_id,
                word_id=i,
                is_last_word=is_last,
            )
        )
    return line_obj


def process_verse(raw_text: str, artist: str = "Unknown", verse_id: int = 0,
                  on_line=None, language: str = None) -> Verse:
    """Entry point: raw lyrics -> Verse. Blank lines are skipped.

    ``on_line(done, total)`` is called after each line when supplied. This is
    the only part of the pipeline long enough to be worth reporting: phoneme
    lookup and syllabification dominate the cost of an analysis, and they happen
    one line at a time. Counting lines is therefore a real measure of progress
    rather than a timer pretending to be one.

    ``language`` is ``"en"``, ``"dar"``, or ``None`` to detect it from the
    lyrics. It is decided once for the whole verse rather than per line, because
    a single bar is short enough to contain no Darija at all while the verse
    around it plainly is.
    """
    if language is None:
        language = darija.detect_language(raw_text)

    verse_obj = Verse(metadata={"artist": artist, "language": language}, verse_id=verse_id)
    lines = [line.strip() for line in raw_text.strip().split("\n")]
    lines = [line for line in lines if line]
    total = len(lines)

    for line_id, line_text in enumerate(lines):
        verse_obj.lines.append(process_line(line_text, line_id, language))
        if on_line is not None:
            on_line(line_id + 1, total)
    return verse_obj
