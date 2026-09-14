"""Continuous rhyme scoring and similarity-based grouping.

The v1 engine grouped syllables whose signature strings were identical. This
module replaces that with a score in [0, 1] built from articulatory distances
(``rhymemap/phonology.py``), and groups syllables by clustering that score instead of
hashing a key.

Three ideas do the work:

1. **The rime dominates.** A rhyme is carried by the nucleus and the coda, in
   that order, so those get most of the weight.
2. **Stress matters.** A stressed and an unstressed syllable rarely rhyme to the
   ear even when their phonemes agree.
3. **An identical onset is evidence against a rhyme.** "cat"/"cat" is repetition,
   not rhyme, and the same is true of "lookin'"/"lookin'". A naive rime-only
   score rates those a perfect 1.0. Penalising a shared onset is what separates
   rhyming from repeating.
"""

from __future__ import annotations

from dataclasses import dataclass

from .phonology import cluster_distance, parse_vowel, vowel_distance

# ---------------------------------------------------------------------------
# Tunable weights.
#
# Kept in one dict so the configuration is a single defensible object rather
# than constants scattered through the scoring code. `eval/` sweeps these.
# ---------------------------------------------------------------------------

# Tuned against eval/gold.json; see eval/tuning.json for the sweeps.
#
# The sweeps are coordinate-wise, and combining each parameter's individual best
# makes the model *worse* (B-cubed F1 0.901 against 0.924 for the untuned set),
# so only changes that also help jointly are adopted here. At present that is
# `nucleus` alone, raised from 0.60 to 0.70, which lifts pairwise F1 from 0.830
# to 0.865 and B-cubed F1 from 0.924 to 0.942.
#
# With a 13-verse gold set these margins are small. Treat the values as
# reasonable defaults supported by evidence, not as a converged optimum.
DEFAULT_WEIGHTS = {
    # Contribution of each component to the raw score. Normalised by their sum,
    # so only the ratios matter.
    "nucleus": 0.70,     # the vowel: the core of the rhyme
    "coda": 0.30,        # consonants after the vowel
    "stress": 0.10,      # stressed/unstressed agreement

    # Multiplicative penalty applied when both syllables have the *same*
    # non-empty onset. 0.0 disables it; 1.0 forbids shared onsets entirely.
    "onset_identity_penalty": 0.35,

    # Credit for matching stress exactly vs. merely both being stressed
    # (primary 1 vs. secondary 2).
    "stress_partial_credit": 0.80,

    # Pairs scoring below this are treated as unrelated when clustering.
    "cluster_threshold": 0.78,

    # Chain detection only. Every position of a multisyllabic window must clear
    # this floor, not just the window's mean. Averaging alone let a 5-syllable
    # window pass on two good positions and three bad ones, which swept ~99% of
    # a verse into some chain.
    "min_position_similarity": 0.70,

    # Extra similarity demanded of the final syllable of a window. Multisyllabic
    # rhymes are anchored at their end: "levitatin'"/"devastatin'" agree most
    # tightly on the last syllable, and a window whose end does not match is two
    # spans that happen to abut.
    "anchor_similarity": 0.80,
}


def stress_similarity(a: int, b: int, partial: float) -> float:
    """1.0 for identical stress, `partial` for two differently-stressed
    stressed syllables, 0.0 when one is stressed and the other is not."""
    if a == b:
        return 1.0
    if a > 0 and b > 0:
        return partial
    return 0.0


def syllable_similarity(a, b, weights=None) -> float:
    """Rhyme score in [0, 1] between two Syllable objects."""
    w = weights or DEFAULT_WEIGHTS

    base_a, stress_a = parse_vowel(a.nucleus)
    base_b, stress_b = parse_vowel(b.nucleus)

    nucleus_sim = 1.0 - vowel_distance(base_a, base_b)
    coda_sim = 1.0 - cluster_distance(a.coda, b.coda)
    stress_sim = stress_similarity(stress_a, stress_b, w["stress_partial_credit"])

    total_weight = w["nucleus"] + w["coda"] + w["stress"]
    score = (
        w["nucleus"] * nucleus_sim
        + w["coda"] * coda_sim
        + w["stress"] * stress_sim
    ) / total_weight

    # Identical onset: the pair is (part of) the same word rather than a rhyme.
    # Scaling by the penalty is a subtraction proportional to the score, which
    # keeps the result inside [0, 1] without a separate clamp.
    onset_a = tuple(p.upper() for p in a.onset)
    onset_b = tuple(p.upper() for p in b.onset)
    if onset_a and onset_a == onset_b:
        score *= 1.0 - w["onset_identity_penalty"]

    return max(0.0, min(1.0, score))


def rhyme_key(syllable) -> tuple:
    """The phonetic identity of a syllable, for deduplication.

    Two syllables with the same key score identically against everything, so
    the pairwise matrix only has to be built over distinct keys. A dense verse
    repeats sounds heavily, which makes this a large saving.
    """
    base, stress = parse_vowel(syllable.nucleus)
    return (
        base,
        stress,
        tuple(p.upper() for p in syllable.coda),
        tuple(p.upper() for p in syllable.onset),
    )


@dataclass
class _KeyedSyllable:
    """A stand-in Syllable carrying only what the scorer reads."""

    nucleus: str
    coda: list
    onset: list

    @classmethod
    def from_key(cls, key) -> _KeyedSyllable:
        base, stress, coda, onset = key
        return cls(nucleus=f"{base}{stress}", coda=list(coda), onset=list(onset))


def similarity_matrix(keys, weights=None):
    """Condensed pairwise *distance* vector over distinct rhyme keys."""
    import numpy as np

    stand_ins = [_KeyedSyllable.from_key(k) for k in keys]
    n = len(stand_ins)
    condensed = np.zeros(n * (n - 1) // 2, dtype=float)

    pos = 0
    for i in range(n):
        for j in range(i + 1, n):
            condensed[pos] = 1.0 - syllable_similarity(stand_ins[i], stand_ins[j], weights)
            pos += 1
    return condensed


def cluster_syllables(syllables, weights=None, threshold=None, method="average") -> dict:
    """Group syllables by rhyme similarity.

    Returns ``{rhyme_key: cluster_id}``. Agglomerative clustering with average
    linkage: a syllable joins a group when its *mean* similarity to that group
    clears the threshold, which stops one loose pair from chaining two otherwise
    distinct rhyme families together.
    """
    w = weights or DEFAULT_WEIGHTS
    cutoff = 1.0 - (threshold if threshold is not None else w["cluster_threshold"])

    keys = sorted({rhyme_key(s) for s in syllables if s.nucleus})
    if not keys:
        return {}
    if len(keys) == 1:
        return {keys[0]: 0}

    from scipy.cluster.hierarchy import fcluster, linkage

    condensed = similarity_matrix(keys, w)
    assignments = fcluster(linkage(condensed, method=method), t=cutoff, criterion="distance")
    return {key: int(cid) for key, cid in zip(keys, assignments, strict=True)}


def group_sizes(assignment: dict) -> dict:
    """``{cluster_id: number_of_distinct_keys}`` for an assignment."""
    sizes: dict[int, int] = {}
    for cid in assignment.values():
        sizes[cid] = sizes.get(cid, 0) + 1
    return sizes


# ---------------------------------------------------------------------------
# Verse-level labelling
# ---------------------------------------------------------------------------


def assign_similarity_labels(
    verse,
    weights=None,
    threshold=None,
    min_occurrences: int = 3,
    tail_window: int | None = None,
    only_terminal: bool = False,
    skip_unstressed_midline: bool = True,
):
    """Label a verse's syllables by clustering them on rhyme similarity.

    The similarity counterpart of ``engine.assign_rhyme_labels``: same candidate
    selection and same ``min_occurrences`` threshold, but groups come from
    clustering a continuous score rather than from exact signature equality.

    ``skip_unstressed_midline`` keeps v1's rule that an unstressed syllable in
    the middle of a line is not where a listener hears the rhyme. Without it the
    schwas dominate every cluster.
    """
    from .engine import RhymeRegistry, candidate_syllables

    candidates = []
    for line in verse.lines:
        for syl in candidate_syllables(line, tail_window, only_terminal):
            if not syl.nucleus:
                continue
            if skip_unstressed_midline:
                _, stress = parse_vowel(syl.nucleus)
                if stress == 0 and not syl.is_terminal:
                    continue
            candidates.append(syl)

    if not candidates:
        return RhymeRegistry()

    assignment = cluster_syllables(candidates, weights, threshold)

    counts: dict[int, int] = {}
    for syl in candidates:
        cid = assignment.get(rhyme_key(syl))
        if cid is not None:
            counts[cid] = counts.get(cid, 0) + 1

    frequent = {cid for cid, n in counts.items() if n >= min_occurrences}

    registry = RhymeRegistry()
    for syl in candidates:
        cid = assignment.get(rhyme_key(syl))
        if cid in frequent:
            syl.rhyme_label = registry.get_label(f"cluster-{cid}")
    return registry
