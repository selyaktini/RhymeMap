"""Rhyme signatures and label assignment (the v1 exact-match engine).

This module groups syllables by an exact string signature. It is kept as the
documented baseline that the similarity engine in ``rhymemap/similarity.py`` is
measured against, so the ablation in ``eval/`` has something honest to compare
to. Its defaults reproduce the original v1 behaviour exactly.
"""

from __future__ import annotations

import re
from collections import defaultdict

from .models import Syllable, Verse

# Consonants grouped by natural class. Two codas that differ but stay inside a
# family (e.g. "T" vs "K", both plosives) can then be treated as a slant rhyme.
CONSONANT_FAMILIES = {
    "M": "NAS", "N": "NAS", "NG": "NAS",
    "S": "SIB", "Z": "SIB", "SH": "SIB", "ZH": "SIB",
    "P": "PLO", "B": "PLO", "T": "PLO", "D": "PLO", "K": "PLO", "G": "PLO",
    "F": "FRI", "V": "FRI", "TH": "FRI", "DH": "FRI",
    "R": "LIQ", "L": "LIQ",
    "W": "GLI", "Y": "GLI",
    "HH": "ASP",
}

_NUCLEUS_RE = re.compile(r"([A-Z]+)([0-2])")


def label_for_index(index: int) -> str:
    """Map 0,1,2,... to A,B,...,Z,AA,AB,... (spreadsheet-column style).

    The original implementation indexed a 26-letter alphabet modulo its length,
    so the 27th rhyme group silently reused the label of the first. A single
    verse of dense lyrics passes 26 groups easily, so this was live corruption
    rather than an edge case.
    """
    if index < 0:
        raise ValueError("label index must be non-negative")
    letters = ""
    n = index
    while True:
        letters = chr(ord("A") + n % 26) + letters
        n = n // 26 - 1
        if n < 0:
            break
    return letters


class RhymeRegistry:
    """Assigns a stable label to each distinct rhyme signature."""

    def __init__(self):
        self.mapping: dict[str, str] = {}
        self.next_index = 0

    def get_label(self, signature: str) -> str:
        if signature not in self.mapping:
            self.mapping[signature] = label_for_index(self.next_index)
            self.next_index += 1
        return self.mapping[signature]


def encode_coda(coda, use_consonant_families: bool = False) -> str:
    """Render a coda as a signature fragment.

    With ``use_consonant_families`` the phonemes are replaced by their natural
    class, which is what makes "loud"/"out" (both ``AW`` + plosive) collide.
    """
    if not coda:
        return ""
    if use_consonant_families:
        return "-".join(CONSONANT_FAMILIES.get(c, c) for c in coda)
    return "".join(coda)


def get_syllable_signature(
    syllable: Syllable,
    use_consonant_families: bool = False,
    include_stress: bool = True,
) -> str:
    """Exact-match signature for a syllable, or "" if it should be ignored.

    Defaults reproduce v1: ``"{vowel}_{stress}_{coda}"`` with the raw coda.
    Unstressed syllables in the middle of a line are dropped, on the assumption
    that they are not where a listener hears the rhyme.
    """
    nucleus_text = str(syllable.nucleus)
    if not nucleus_text:
        return ""

    match = _NUCLEUS_RE.match(nucleus_text)
    if match:
        vowel_sound, stress = match.groups()
    else:
        vowel_sound, stress = nucleus_text, "0"

    if stress == "0" and not syllable.is_terminal:
        return ""

    coda = encode_coda(syllable.coda, use_consonant_families=use_consonant_families)
    if include_stress:
        return f"{vowel_sound}_{stress}_{coda}"
    return f"{vowel_sound}_{coda}"


def candidate_syllables(
    line,
    tail_window: int | None = None,
    only_terminal: bool = False,
) -> list[Syllable]:
    """Syllables of a line that are eligible to carry a rhyme label.

    ``only_terminal`` keeps just the line-final syllable (classic end-rhyme);
    ``tail_window`` keeps the last N syllables. ``only_terminal`` wins if both
    are supplied.
    """
    syllables = [syl for word in line.words for syl in word.syllables]
    if only_terminal:
        return [syl for syl in syllables if syl.is_terminal]
    if tail_window is not None and tail_window > 0:
        return syllables[-tail_window:]
    return syllables


def assign_rhyme_labels(
    verse: Verse,
    min_occurrences: int = 3,
    tail_window: int | None = None,
    only_terminal: bool = False,
    use_consonant_families: bool = False,
    include_stress: bool = True,
) -> RhymeRegistry:
    """Label rhyming syllables in place; returns the registry that was used.

    Two passes: count every signature, then label only those reaching
    ``min_occurrences``.
    """
    counter: dict[str, int] = defaultdict(int)

    for line in verse.lines:
        for syl in candidate_syllables(line, tail_window, only_terminal):
            sig = get_syllable_signature(syl, use_consonant_families, include_stress)
            if sig:
                counter[sig] += 1

    frequent = {sig for sig, count in counter.items() if count >= min_occurrences}

    registry = RhymeRegistry()
    for line in verse.lines:
        for syl in candidate_syllables(line, tail_window, only_terminal):
            sig = get_syllable_signature(syl, use_consonant_families, include_stress)
            if sig in frequent:
                syl.rhyme_label = registry.get_label(sig)
    return registry
