"""Articulatory feature tables and phoneme distances.

The v1 engine asked "are these two signature strings equal?". Rhyme is not a
string-equality relation: "bit" and "beat" nearly rhyme, "bit" and "bought" do
not, and no amount of exact matching expresses that difference. This module
places every ARPAbet phoneme in a feature space so the question becomes "how far
apart are these two sounds?".

Vowels are positioned by the standard articulatory parameters (height, backness,
rounding, tenseness) plus the target of any offglide, which is what separates the
diphthongs. Consonants are described by place, manner and voicing — the natural
classes that phonology already uses to explain which sounds pattern together.

All distances are normalised to [0, 1].
"""

from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# Vowels
#
# height   0 = low (AA)          -> 1 = high (IY, UW)
# backness 0 = front (IY)        -> 1 = back (UW)
# round    0 = unrounded         -> 1 = rounded
# tense    0 = lax (IH, EH)      -> 1 = tense (IY, EY)
# glide    offglide target for diphthongs, as (height, backness), else None
# rhotic   ER carries r-colouring, which dominates its perception
# ---------------------------------------------------------------------------

VOWELS: dict[str, dict] = {
    #        height  back  round  tense  glide         rhotic
    "IY": {"height": 1.00, "back": 0.00, "round": 0.0, "tense": 1.0, "glide": None,         "rhotic": False},
    "IH": {"height": 0.80, "back": 0.10, "round": 0.0, "tense": 0.0, "glide": None,         "rhotic": False},
    "EY": {"height": 0.70, "back": 0.05, "round": 0.0, "tense": 1.0, "glide": (1.00, 0.00), "rhotic": False},
    "EH": {"height": 0.50, "back": 0.10, "round": 0.0, "tense": 0.0, "glide": None,         "rhotic": False},
    "AE": {"height": 0.15, "back": 0.15, "round": 0.0, "tense": 0.0, "glide": None,         "rhotic": False},
    "AA": {"height": 0.00, "back": 0.90, "round": 0.0, "tense": 1.0, "glide": None,         "rhotic": False},
    "AO": {"height": 0.25, "back": 1.00, "round": 1.0, "tense": 1.0, "glide": None,         "rhotic": False},
    "OW": {"height": 0.60, "back": 0.90, "round": 1.0, "tense": 1.0, "glide": (1.00, 1.00), "rhotic": False},
    "UH": {"height": 0.80, "back": 0.85, "round": 1.0, "tense": 0.0, "glide": None,         "rhotic": False},
    "UW": {"height": 1.00, "back": 1.00, "round": 1.0, "tense": 1.0, "glide": None,         "rhotic": False},
    "AH": {"height": 0.40, "back": 0.50, "round": 0.0, "tense": 0.0, "glide": None,         "rhotic": False},
    "ER": {"height": 0.50, "back": 0.50, "round": 0.0, "tense": 1.0, "glide": None,         "rhotic": True},
    "AY": {"height": 0.05, "back": 0.60, "round": 0.0, "tense": 1.0, "glide": (1.00, 0.00), "rhotic": False},
    "AW": {"height": 0.05, "back": 0.50, "round": 0.0, "tense": 1.0, "glide": (1.00, 1.00), "rhotic": False},
    "OY": {"height": 0.30, "back": 0.95, "round": 1.0, "tense": 1.0, "glide": (1.00, 0.00), "rhotic": False},
}

# Relative importance of each vowel dimension. Height and backness carry the
# vowel's identity; rounding and tenseness are audible but secondary; a
# mismatched offglide (bait vs bet) is a large perceptual difference.
VOWEL_FEATURE_WEIGHTS = {
    "height": 1.00,
    "back": 0.90,
    "round": 0.35,
    "tense": 0.30,
    "glide": 0.80,
    "rhotic": 0.90,
}

_STRESS_RE = re.compile(r"^([A-Z]+)([0-2])?$")


def parse_vowel(phoneme: str) -> tuple[str, int]:
    """Split "AA1" into ("AA", 1). Unstressed or bare vowels give stress 0."""
    match = _STRESS_RE.match(str(phoneme).strip().upper())
    if not match:
        return str(phoneme).strip().upper(), 0
    base, stress = match.groups()
    return base, int(stress) if stress else 0


def _raw_vowel_distance(a: str, b: str) -> float:
    """Weighted feature distance, before range normalisation."""
    base_a, _ = parse_vowel(a)
    base_b, _ = parse_vowel(b)
    if base_a == base_b:
        return 0.0

    fa, fb = VOWELS.get(base_a), VOWELS.get(base_b)
    if fa is None or fb is None:
        # Unknown symbol: identical or maximally distant, nothing in between.
        return 0.0 if base_a == base_b else 1.0

    total = 0.0
    weight_sum = 0.0

    for key in ("height", "back", "round", "tense"):
        w = VOWEL_FEATURE_WEIGHTS[key]
        total += w * abs(fa[key] - fb[key])
        weight_sum += w

    # Offglide: no glide vs a glide is a full mismatch; two different glide
    # targets are scored by how far apart those targets are.
    w = VOWEL_FEATURE_WEIGHTS["glide"]
    ga, gb = fa["glide"], fb["glide"]
    if ga is None and gb is None:
        glide_diff = 0.0
    elif ga is None or gb is None:
        glide_diff = 1.0
    else:
        glide_diff = min(1.0, (abs(ga[0] - gb[0]) + abs(ga[1] - gb[1])) / 2)
    total += w * glide_diff
    weight_sum += w

    w = VOWEL_FEATURE_WEIGHTS["rhotic"]
    total += w * (0.0 if fa["rhotic"] == fb["rhotic"] else 1.0)
    weight_sum += w

    return min(1.0, total / weight_sum)


def _max_pairwise(symbols, fn) -> float:
    """Largest distance actually attainable between any two of `symbols`."""
    items = list(symbols)
    return max(
        (fn(a, b) for i, a in enumerate(items) for b in items[i + 1:]),
        default=1.0,
    ) or 1.0


# Averaging weighted features leaves the raw scale badly compressed: no real
# vowel pair reaches 1.0, so even unrelated vowels scored as fairly similar and
# "cat"/"dog" outranked the near-rhyme "bit"/"beat". Rescaling by the most
# distant pair in the table restores the full [0, 1] range.
_MAX_VOWEL_DISTANCE = _max_pairwise(VOWELS, _raw_vowel_distance)


def vowel_distance(a: str, b: str) -> float:
    """Distance in [0, 1] between two vowel phonemes (stress ignored)."""
    return min(1.0, _raw_vowel_distance(a, b) / _MAX_VOWEL_DISTANCE)


# ---------------------------------------------------------------------------
# Consonants
#
# place  front-to-back position, 0 = bilabial -> 1 = glottal
# manner articulation type; see MANNER_DISTANCE for how manners compare
# voice  0 = voiceless, 1 = voiced
# ---------------------------------------------------------------------------

CONSONANTS: dict[str, dict] = {
    "P":  {"place": 0.00, "manner": "plosive",     "voice": 0},
    "B":  {"place": 0.00, "manner": "plosive",     "voice": 1},
    "M":  {"place": 0.00, "manner": "nasal",       "voice": 1},
    "F":  {"place": 0.15, "manner": "fricative",   "voice": 0},
    "V":  {"place": 0.15, "manner": "fricative",   "voice": 1},
    "TH": {"place": 0.25, "manner": "fricative",   "voice": 0},
    "DH": {"place": 0.25, "manner": "fricative",   "voice": 1},
    "T":  {"place": 0.35, "manner": "plosive",     "voice": 0},
    "D":  {"place": 0.35, "manner": "plosive",     "voice": 1},
    "N":  {"place": 0.35, "manner": "nasal",       "voice": 1},
    "S":  {"place": 0.35, "manner": "fricative",   "voice": 0},
    "Z":  {"place": 0.35, "manner": "fricative",   "voice": 1},
    "L":  {"place": 0.35, "manner": "lateral",     "voice": 1},
    "R":  {"place": 0.45, "manner": "approximant", "voice": 1},
    "SH": {"place": 0.50, "manner": "fricative",   "voice": 0},
    "ZH": {"place": 0.50, "manner": "fricative",   "voice": 1},
    "CH": {"place": 0.50, "manner": "affricate",   "voice": 0},
    "JH": {"place": 0.50, "manner": "affricate",   "voice": 1},
    "Y":  {"place": 0.60, "manner": "approximant", "voice": 1},
    "K":  {"place": 0.80, "manner": "plosive",     "voice": 0},
    "G":  {"place": 0.80, "manner": "plosive",     "voice": 1},
    "NG": {"place": 0.80, "manner": "nasal",       "voice": 1},
    "W":  {"place": 0.85, "manner": "approximant", "voice": 1},
    "HH": {"place": 1.00, "manner": "fricative",   "voice": 0},
}

# Moroccan Darija adds ten consonants English has no symbol for. They live in
# their own table so the English scale above can stay fixed (see
# _MAX_CONSONANT_DISTANCE), then merge into CONSONANTS - the distance function
# never needs to know which language a phoneme came from.
#
# English stops at the velum (place 0.80). Arabic keeps going: uvular,
# pharyngeal, glottal. Those places are what an English-only table cannot
# express, and they carry a great deal of Darija rhyme.
DARIJA_CONSONANTS = {
    "Q":   {"place": 0.88, "manner": "plosive",   "voice": 0},   # ق  9
    "X":   {"place": 0.90, "manner": "fricative", "voice": 0},   # خ  kh
    "GH":  {"place": 0.90, "manner": "fricative", "voice": 1},   # غ  gh
    "HS":  {"place": 0.96, "manner": "fricative", "voice": 0},   # ح  7
    "AIN": {"place": 0.96, "manner": "fricative", "voice": 1},   # ع  3
    "Q2":  {"place": 1.00, "manner": "plosive",   "voice": 0},   # ء  2

    # Emphatics: coronal like their plain counterparts, with a secondary
    # pharyngeal constriction. Same place and manner, so nothing but the
    # `emphatic` flag separates /s/ from /sˤ/ - and in Darija that is a
    # phonemic contrast, not an accent.
    "SD": {"place": 0.35, "manner": "fricative", "voice": 0, "emphatic": True},  # ص
    "DD": {"place": 0.35, "manner": "plosive",   "voice": 1, "emphatic": True},  # ض
    "TD": {"place": 0.35, "manner": "plosive",   "voice": 0, "emphatic": True},  # ط
    "ZD": {"place": 0.35, "manner": "fricative", "voice": 1, "emphatic": True},  # ظ
}

ENGLISH_CONSONANTS = tuple(CONSONANTS)

CONSONANTS.update(DARIJA_CONSONANTS)

# How similar two manners sound. Stops and affricates share a closure; nasals
# and laterals are both sonorants; approximants sit closest to vowels.
MANNER_DISTANCE = {
    ("plosive", "affricate"): 0.35,
    ("plosive", "fricative"): 0.60,
    ("plosive", "nasal"): 0.70,
    ("plosive", "lateral"): 0.85,
    ("plosive", "approximant"): 0.90,
    ("affricate", "fricative"): 0.35,
    ("affricate", "nasal"): 0.80,
    ("affricate", "lateral"): 0.85,
    ("affricate", "approximant"): 0.90,
    ("fricative", "nasal"): 0.70,
    ("fricative", "lateral"): 0.75,
    ("fricative", "approximant"): 0.70,
    ("nasal", "lateral"): 0.45,
    ("nasal", "approximant"): 0.55,
    ("lateral", "approximant"): 0.30,
}

CONSONANT_FEATURE_WEIGHTS = {"place": 0.70, "manner": 1.00, "voice": 0.40}

# Emphasis is scored on top of the three weights above rather than alongside
# them, so it never appears in the denominator. An English pair therefore keeps
# exactly the distance it had before Darija existed; only a pair where one side
# is emphatic pays anything. Sized like voicing, which is the contrast it most
# resembles: same place, same manner, one laryngeal/pharyngeal gesture apart.
EMPHATIC_WEIGHT = 0.40


def manner_distance(a: str, b: str) -> float:
    if a == b:
        return 0.0
    return MANNER_DISTANCE.get((a, b), MANNER_DISTANCE.get((b, a), 1.0))


def _raw_consonant_distance(a: str, b: str) -> float:
    """Weighted feature distance, before range normalisation."""
    a, b = str(a).strip().upper(), str(b).strip().upper()
    if a == b:
        return 0.0

    fa, fb = CONSONANTS.get(a), CONSONANTS.get(b)
    if fa is None or fb is None:
        return 1.0

    w = CONSONANT_FEATURE_WEIGHTS
    total = (
        w["place"] * abs(fa["place"] - fb["place"])
        + w["manner"] * manner_distance(fa["manner"], fb["manner"])
        + w["voice"] * (0.0 if fa["voice"] == fb["voice"] else 1.0)
    ) / sum(w.values())

    # Emphasis defaults to False, so this term is zero for every pair that does
    # not involve a Darija emphatic.
    if fa.get("emphatic", False) != fb.get("emphatic", False):
        total += EMPHATIC_WEIGHT / sum(w.values())

    return min(1.0, total)


# Rescaled like the vowels, but deliberately over the English table only.
# Normalising over every symbol would mean that adding a language silently
# retunes another one: the widest Darija pair (W/TD) is 8% wider than the widest
# English pair (P/W), so folding it in would shrink every English distance by
# that much and shift clusters in verses containing no Darija at all. Pinning
# the scale to English keeps those verses bit-identical; the handful of Darija
# pairs beyond the old maximum simply saturate at 1.0, which is the right answer
# for them anyway - they are as unlike each other as two consonants get.
_MAX_CONSONANT_DISTANCE = _max_pairwise(ENGLISH_CONSONANTS, _raw_consonant_distance)


def consonant_distance(a: str, b: str) -> float:
    """Distance in [0, 1] between two consonant phonemes."""
    a, b = str(a).strip().upper(), str(b).strip().upper()
    if a == b:
        return 0.0
    if a not in CONSONANTS or b not in CONSONANTS:
        return 1.0
    return min(1.0, _raw_consonant_distance(a, b) / _MAX_CONSONANT_DISTANCE)


# Cost of inserting or deleting a consonant when aligning two codas. Below 1.0
# because "sun"/"suns" is a closer pair than "sun"/"sung".
INDEL_COST = 0.75


def cluster_distance(a: list[str], b: list[str]) -> float:
    """Normalised alignment distance between two consonant clusters.

    A Levenshtein alignment whose substitution cost is the feature distance
    between the two consonants, rather than 0/1 on string equality. Normalised
    by the longer cluster so the result stays in [0, 1].
    """
    a = [str(p).strip().upper() for p in a if str(p).strip()]
    b = [str(p).strip().upper() for p in b if str(p).strip()]

    if not a and not b:
        return 0.0
    if not a or not b:
        # One cluster empty: cost is deleting the other, capped at 1.
        return min(1.0, INDEL_COST * max(len(a), len(b)) / max(len(a), len(b), 1))

    previous = [j * INDEL_COST for j in range(len(b) + 1)]
    for i, pa in enumerate(a, start=1):
        current = [i * INDEL_COST]
        for j, pb in enumerate(b, start=1):
            current.append(min(
                previous[j] + INDEL_COST,                          # delete
                current[j - 1] + INDEL_COST,                       # insert
                previous[j - 1] + consonant_distance(pa, pb),      # substitute
            ))
        previous = current

    return min(1.0, previous[-1] / max(len(a), len(b)))
