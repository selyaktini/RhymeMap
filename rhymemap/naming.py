"""Names for rhyme groups, derived from how they sound.

Groups used to be labelled A, B, C, ... Z, AA, AB, in order of first appearance.
That is a spreadsheet column, not a name, and it has three problems:

* **It says nothing.** "Group AB" carries no information about the sound. With
  257 groups in one verse most labels are two-letter noise.
* **It is unstable.** The letter depends on reading order, so the same rhyme
  gets a different label in every song -- and even between two engines on the
  same song. Nothing can be compared or remembered.
* **It cannot be spoken.** People discussing a verse say "the *-ames* rhyme" or
  "the *lookin' boy* chain". Nobody says "group AB".

So a group is named after its own rime. `flames / fame / shame` becomes
**-ames**; `nod / God / Asgard` becomes **-od**; a multisyllabic chain is named
by the span it repeats, **lookin' boy**.

The name is computed from the phonetics, which makes it stable: the same rhyme
is called the same thing in every song, under every engine. Since the colour is
hashed from the name, the colour becomes stable too -- `-ames` is the same hue
wherever it appears.

Spelling is taken from a real word in the group rather than generated from
ARPAbet. English orthography is too irregular to synthesise ("-ite" or "-yte"?
"-oh" or "-ow"?), and a word that is actually in the verse is both correct and
recognisable. The exact rime is kept alongside for anyone who wants it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

TRUE_VOWELS = frozenset("aeiou")
# 'y' is a vowel in "rhyme" and a consonant in "yeah". Treating it as a vowel
# everywhere made a group of AE words come out as "-yeah" instead of "-eah", so
# it counts only when it is not the first letter.
VOWELS = frozenset("aeiouy")

# Fallback rendering, used only when a group has no usable spelling to borrow.
VOWEL_SPELLING = {
    "AA": "ah", "AE": "a", "AH": "uh", "AO": "aw", "AW": "ow", "AY": "y",
    "EH": "e", "ER": "er", "EY": "ay", "IH": "i", "IY": "ee", "OW": "oh",
    "OY": "oy", "UH": "uu", "UW": "oo",
}
CONSONANT_SPELLING = {
    "B": "b", "CH": "ch", "D": "d", "DH": "th", "F": "f", "G": "g", "HH": "h",
    "JH": "j", "K": "k", "L": "l", "M": "m", "N": "n", "NG": "ng", "P": "p",
    "R": "r", "S": "s", "SH": "sh", "T": "t", "TH": "th", "V": "v", "W": "w",
    "Y": "y", "Z": "z", "ZH": "zh",
    # Darija, spelled back the way it was written: Arabizi, not ARPAbet. A
    # group of Moroccan rhymes should be called "-a3" and "-i9", because that
    # is what the reader is looking at on the page. Without these the fallback
    # lowercases the phoneme name and offers "-aain".
    "AIN": "3", "HS": "7", "Q": "9", "Q2": "2", "X": "kh", "GH": "gh",
    "SD": "s", "DD": "d", "TD": "t", "ZD": "z",
}

_STRESS = re.compile(r"\d$")

# Function words are frequent but make poor names: a group is not memorable as
# "-im" or "-of", even when those are its commonest members. They are skipped
# when choosing the label, and fallen back to only if a group has nothing else.
FUNCTION_WORDS = frozenset("""
a an the and but or nor of to in on at for with from by as is it its im i you
your youre me my we us our they them their he she his her be been being am are
was were do dont does did so that this these those what when who how if up no
not now get got just aint cause coz em ya yeah oh uh ah
""".split()) | frozenset("""
w f l b d o dyal dyali li hada hadi had dak dik chi kol kola koulchi ghir
ana nta nti huwa hiya hna homa rah raha rani rak kayn kayna machi walo ma
mn men 3la m3a 3nd bach bla wla walla ila daba hit 7it wach fin kifach chnou
ta wa7ed wahed lli melli safi yallah ah iyeh la
""".split())
"""Words that make poor group names. The Darija half is the same idea as the
English half -- nobody remembers a rhyme called "-w" -- and it matters more
here, because Darija writes its prepositions as single letters and they fall at
the front of half the bars in a verse."""


@dataclass
class GroupName:
    """What a rhyme group is called, and why."""

    label: str                                  # "-ames", "lookin' boy"
    rime: str = ""                              # "EY1 M Z" -- the exact phonetics
    exemplars: list[str] = field(default_factory=list)   # ["flames", "fame", "shame"]
    length: int = 1                             # syllables per occurrence
    occurrences: int = 0
    positions: list[float] = field(default_factory=list)  # 0..1 through the verse
    alternatives: list[str] = field(default_factory=list)  # other spellings, for collisions


def strip_stress(phoneme: str) -> str:
    return _STRESS.sub("", str(phoneme).strip().upper())


def spell_rime(nucleus: str, coda) -> str:
    """Render a rime from ARPAbet, for when no real spelling is available."""
    vowel = VOWEL_SPELLING.get(strip_stress(nucleus), strip_stress(nucleus).lower())
    tail = "".join(CONSONANT_SPELLING.get(strip_stress(c), strip_stress(c).lower()) for c in coda)
    return vowel + tail


def vowel_groups(word: str) -> list[int]:
    """Start index of each run of vowel letters: 'asteroid' -> [0, 3, 6]."""
    starts = []
    previous_was_vowel = False
    for i, char in enumerate(word):
        is_vowel = char in TRUE_VOWELS or (char == "y" and i > 0)
        if is_vowel and not previous_was_vowel:
            starts.append(i)
        previous_was_vowel = is_vowel
    return starts


def rime_from_spelling(word: str, syllable_index: int = 0) -> str:
    """The tail of a word from the vowel of its `syllable_index`-th syllable.

    'flames' -> 'ames'; 'asteroid' with index 2 -> 'oid'.

    Deliberately orthographic: a name has to be one a person recognises, and the
    letters of a word that is actually in the verse beat anything synthesised
    from phonemes.

    Vowel *runs* are counted rather than vowel letters, so a digraph ('oi',
    'ea') is one syllable's worth. Silent 'e' would add a spurious group, but
    indexing forward from the start rather than back from the end means it is
    never reached: 'shame' takes group 0 and yields 'ame', not 'e'.
    """
    cleaned = re.sub(r"[^\w']", "", word or "").lower()
    starts = vowel_groups(cleaned)
    if not starts:
        return cleaned
    return cleaned[starts[min(syllable_index, len(starts) - 1)]:]


def _clean(word: str) -> str:
    return re.sub(r"[^\w'-]", "", (word or "").strip().lower())


def _clean_span(span: str) -> str:
    """Like `_clean` but keeps the spaces between words.

    A chain name is a phrase -- "they say lookin boy" -- and collapsing it to
    "theysaylookinboy" makes it unreadable, which is the whole thing this naming
    scheme exists to avoid.
    """
    return re.sub(r"\s+", " ", re.sub(r"[^\w'\- ]", "", (span or "").strip().lower())).strip()


def pick_exemplars(words, limit: int = 3, on_rime=None) -> list[str]:
    """The clearest words to show for a group.

    Words carrying the group's modal rime come first, then non-function words,
    then by frequency. Ties break on length and alphabetically so the same group
    shows the same examples on every run.
    """
    preferred = {_clean(w) for w in (on_rime or []) if _clean(w)}

    counts: dict[str, int] = {}
    for word in words:
        cleaned = _clean(word)
        if cleaned:
            counts[cleaned] = counts.get(cleaned, 0) + 1

    def rank(item):
        word, count = item
        return (0 if word in preferred else 1,
                1 if word in FUNCTION_WORDS else 0,
                -count, len(word), word)

    return [word for word, _ in sorted(counts.items(), key=rank)[:limit]]


def canonical_rime(syllables) -> tuple[str, tuple]:
    """The modal (nucleus, coda) of a group.

    A similarity-clustered group holds near-matches rather than identical
    sounds, so there is no single rime -- but there is a commonest one, and that
    is what the group is heard as. Taking the first member's rime instead made
    the label and the phonetics disagree ("-im" labelled a group whose rime was
    printed as `IH T`).
    """
    counts: dict[tuple, int] = {}
    for syl in syllables:
        key = (strip_stress(syl.nucleus), tuple(strip_stress(c) for c in syl.coda))
        counts[key] = counts.get(key, 0) + 1
    if not counts:
        return "", ()
    return max(counts.items(), key=lambda kv: (kv[1], -len(kv[0][1])))[0]


def label_candidates(occurrences, syllables) -> list[str]:
    """Spellings that could name this group, best first.

    Only words whose own rime matches the group's modal rime are considered, so
    the name describes the sound the group is actually built on. Function words
    are ranked last: "-im" and "-of" are accurate and useless.
    """
    nucleus, coda = canonical_rime(syllables)

    scored: dict[str, list] = {}
    for (word, index), syl in zip(occurrences, syllables, strict=False):
        tail = rime_from_spelling(word, index)
        if not tail:
            continue
        key = (strip_stress(syl.nucleus), tuple(strip_stress(c) for c in syl.coda))
        entry = scored.setdefault(tail, [0, 0, word])
        entry[0] += 1                                   # how often this spelling appears
        if key == (nucleus, coda):
            entry[1] += 1                               # ...on the group's modal rime

    if not scored:
        return []

    def rank(item):
        tail, (count, on_rime, _word) = item
        return (
            0 if on_rime else 1,   # describes the sound the group is built on
            # A tail with no true vowel is not a rime at all -- "j" from the
            # letter-name in "J.J. Fad" once labelled a whole group.
            0 if any(c in TRUE_VOWELS for c in tail) else 1,
            0 if len(tail) >= 2 else 1,     # a single letter reads as a typo
            len(tail),             # shortest tail = the rime with least onset left on it
            -count,
            tail,
        )

    # Shortest wins here, deliberately, and function words are *not* demoted for
    # the label. "-or" from "for" names the rime better than "-ormal" from
    # "normal"; the function-word rule belongs to the examples, where a reader
    # needs a word worth looking at, not to the name.
    return [tail for tail, _ in sorted(scored.items(), key=rank)]


def name_single_group(syllables, occurrences) -> GroupName:
    """Name a one-syllable-per-occurrence group, e.g. '-ames'.

    `occurrences` is ``[(word, syllable_index), ...]`` -- the syllable index
    matters because the rime lives in the syllable that was labelled, not in the
    first one: 'asteroid' should yield '-oid', never '-asteroid'.
    """
    words = [word for word, _ in occurrences]
    candidates = label_candidates(occurrences, syllables)
    nucleus, coda = canonical_rime(syllables)

    tail = candidates[0] if candidates else spell_rime(nucleus, coda)
    rime = " ".join([nucleus, *coda]).strip()

    name = GroupName(label=f"-{tail}" if tail else "-?", rime=rime,
                     exemplars=pick_exemplars(words, on_rime=_on_rime_words(occurrences, syllables)))
    name.alternatives = candidates[1:5]
    return name


def _on_rime_words(occurrences, syllables) -> list[str]:
    """Words that carry the group's modal rime, for showing as examples."""
    nucleus, coda = canonical_rime(syllables)
    out = []
    for (word, _), syl in zip(occurrences, syllables, strict=False):
        key = (strip_stress(syl.nucleus), tuple(strip_stress(c) for c in syl.coda))
        if key == (nucleus, coda):
            out.append(word)
    return out


def name_chain(spans) -> GroupName:
    """Name a multisyllabic chain after the span it repeats.

    The commonest span wins, then the longest -- a chain occurring as both
    "lookin boy" and "day lookin boy" is better known by the fuller phrase.
    """
    counts: dict[str, int] = {}
    for span in spans:
        cleaned = _clean_span(span)
        if cleaned:
            counts[cleaned] = counts.get(cleaned, 0) + 1

    ordered = sorted(counts.items(), key=lambda kv: (-kv[1], -len(kv[0]), kv[0]))
    exemplars = [span for span, _ in ordered[:3]]
    name = GroupName(label=exemplars[0] if exemplars else "chain", exemplars=exemplars)
    name.alternatives = [span for span, _ in ordered[1:5]]
    return name


def deduplicate(names: list[GroupName]) -> list[GroupName]:
    """Make labels unique without making them ugly.

    Two groups can legitimately land on the same spelling -- the same rime under
    different stress, or two chains whose commonest span is the same phrase. The
    first keeps the plain name and later ones take a numeric suffix, so the
    common case stays clean.
    """
    taken: set[str] = set()
    for name in names:
        if name.label not in taken:
            taken.add(name.label)
            continue

        # Two groups can share a spelling while sounding different ("-at" for
        # both AH-T and AE-N). A second real spelling from the group describes
        # it far better than a tacked-on number, so try those first.
        for alternative in name.alternatives:
            candidate = f"-{alternative}"
            if candidate not in taken:
                name.label = candidate
                break
        else:
            base, suffix = name.label, 2
            while f"{base} {suffix}" in taken:
                suffix += 1
            name.label = f"{base} {suffix}"
        taken.add(name.label)
    return names


def _span_text(syllables, start: int, length: int) -> str:
    """Readable text for a run of syllables, keeping word boundaries.

    Syllables carry their word id, so a span crossing words is rendered with a
    space where the words changed: 'lookin boy', not 'lookinboy'.
    """
    parts: list[str] = []
    previous_word = None
    for syl in syllables[start:start + length]:
        key = (syl.line_id, syl.word_id)
        if previous_word is not None and key != previous_word:
            parts.append(" ")
        parts.append(syl.text)
        previous_word = key
    return "".join(parts).strip()


def rename_groups(verse, chains=None) -> dict:
    """Replace a verse's labels with names taken from how each group sounds.

    Runs after an engine has labelled the verse, so it works the same for every
    engine. Returns ``{label: GroupName}`` keyed by the *new* label.
    """
    syllables = verse.syllables()
    total = len(syllables)
    if not total:
        return {}

    # Where each label occurs, and which word carried it.
    by_label: dict[str, list[int]] = {}
    for i, syl in enumerate(syllables):
        if syl.rhyme_label:
            by_label.setdefault(syl.rhyme_label, []).append(i)
    if not by_label:
        return {}

    # A word for each syllable position, for the exemplars.
    word_at: dict[int, tuple[str, int]] = {}
    index = 0
    for line in verse.lines:
        for word in line.words:
            for syl_index, _ in enumerate(word.syllables):
                word_at[index] = (word.text, syl_index)
                index += 1

    chain_by_label = {c.label: c for c in (chains or [])}

    ordered = sorted(by_label.items(), key=lambda kv: (-len(kv[1]), kv[0]))
    names: list[tuple[str, GroupName]] = []

    for label, indices in ordered:
        chain = chain_by_label.get(label)
        if chain is not None and chain.length > 1:
            spans = [_span_text(syllables, start, chain.length) for start in chain.occurrences]
            name = name_chain(spans)
            name.length = chain.length
            name.occurrences = len(chain.occurrences)
            name.positions = [round(start / total, 4) for start in chain.occurrences]
        else:
            occurrences = [word_at.get(i, ("", 0)) for i in indices]
            name = name_single_group([syllables[i] for i in indices], occurrences)
            name.length = 1
            name.occurrences = len(indices)
            name.positions = [round(i / total, 4) for i in indices]
        names.append((label, name))

    deduplicate([name for _, name in names])

    rename = {old: name.label for old, name in names}
    for syl in syllables:
        if syl.rhyme_label:
            syl.rhyme_label = rename.get(syl.rhyme_label, syl.rhyme_label)
    for chain in chains or []:
        chain.label = rename.get(chain.label, chain.label)

    return {name.label: name for _, name in names}
