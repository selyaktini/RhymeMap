"""Multisyllabic rhyme chain detection.

Labelling one syllable at a time cannot see that

    levitatin' / devastatin' / demonstratin'

is a single four-syllable rhyme. The per-syllable engine assigns each of those
twelve syllables to whichever group its own sound falls in, and the structure —
the thing a listener actually hears — is never represented.

This module looks for repeated *spans*. It slides windows of 1..N syllables over
the verse, clusters windows that sound alike, and keeps the longest, strongest
chain covering each syllable.

Cost control: the pairwise score between two windows is the mean of the
per-syllable scores at each position, so the per-syllable matrix is computed once
over the verse's distinct rhyme keys and every window comparison becomes a
lookup. The lookups are done as numpy gathers, which keeps a 1500-syllable verse
in the low seconds.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .similarity import DEFAULT_WEIGHTS, _KeyedSyllable, rhyme_key, syllable_similarity

# A window longer than this is almost always two chains that happen to abut.
DEFAULT_MAX_WINDOW = 5

# Minimum times a span must recur to count as a chain.
DEFAULT_MIN_OCCURRENCES = 2

# Maximum number of lines between consecutive occurrences of one chain.
#
# Rhyme is local. Without this, every syllable joins some chain, because in a
# 1476-syllable verse drawn from ~400 distinct sounds any span finds a partner
# somewhere -- 80 lines away, where no listener would hear it as a rhyme.
# Raising the similarity threshold does not fix that: at 0.94 coverage was still
# 91%. Proximity is the constraint that was missing, not strictness.
#
# The default is a couplet-width window. Measured on the Rap God demo, the gap
# controls coverage directly (chain density / multisyllabic coverage):
#   gap 1 -> 78.3% / 41.0%      gap 4 -> 91.9% / 54.9%
#   gap 2 -> 86.0% / 47.6%      no gap -> 99.3% / 79.7%
# Phase 4 tunes this against the annotated gold set.
DEFAULT_MAX_LINE_GAP = 2


@dataclass
class RhymeChain:
    """A repeated multisyllabic span."""

    length: int                                   # syllables per occurrence
    occurrences: list[int] = field(default_factory=list)   # start indices in the stream
    similarity: float = 0.0                       # mean pairwise score between occurrences
    label: str = ""

    @property
    def strength(self) -> float:
        """length x mean similarity x occurrence count.

        Longer spans and more repetitions both make a chain more salient, and
        the similarity term stops a long-but-loose match from outranking a
        short exact one.
        """
        return self.length * self.similarity * len(self.occurrences)

    def covers(self) -> set[int]:
        """Every stream index this chain occupies."""
        return {i for start in self.occurrences for i in range(start, start + self.length)}

    def __repr__(self) -> str:
        return (f"RhymeChain(label={self.label!r}, length={self.length}, "
                f"n={len(self.occurrences)}, sim={self.similarity:.2f}, "
                f"strength={self.strength:.2f})")


def _key_similarity_matrix(keys, weights):
    """Dense per-key similarity matrix over the verse's distinct syllables."""
    import numpy as np

    stand_ins = [_KeyedSyllable.from_key(k) for k in keys]
    n = len(stand_ins)
    matrix = np.eye(n, dtype=float)
    for i in range(n):
        for j in range(i + 1, n):
            score = syllable_similarity(stand_ins[i], stand_ins[j], weights)
            matrix[i, j] = matrix[j, i] = score
    return matrix


def _windows_for_length(syllables, length: int):
    """Start indices of every window of `length` that stays inside one line.

    A rhyme chain does not span a line break, and excluding those windows also
    keeps the candidate count down.
    """
    starts = []
    for start in range(len(syllables) - length + 1):
        span = syllables[start:start + length]
        if all(s.line_id == span[0].line_id for s in span):
            starts.append(start)
    return starts


def _cluster_windows(window_keys, key_matrix, threshold: float, floor: float = 0.0,
                     anchor: float = 0.0, method: str = "average"):
    """Cluster window types that sound alike.

    A pair of windows must clear three separate bars:

    * the **mean** similarity across positions reaches ``threshold``;
    * **every** position reaches ``floor`` — otherwise a long window passes on a
      couple of strong positions while the rest disagree;
    * the **final** position reaches ``anchor``, because a multisyllabic rhyme is
      anchored at its end.

    `window_keys` is an (M, L) integer array of key indices. Returns a list of
    cluster ids, one per row.
    """
    import numpy as np
    from scipy.cluster.hierarchy import fcluster, linkage
    from scipy.spatial.distance import squareform

    count = len(window_keys)
    if count == 0:
        return []
    if count == 1:
        return [1]

    length = window_keys.shape[1]
    total = np.zeros((count, count), dtype=float)
    minimum = np.ones((count, count), dtype=float)
    final = None

    # One gather per position, rather than scoring every window pair directly.
    for position in range(length):
        column = window_keys[:, position]
        gathered = key_matrix[np.ix_(column, column)]
        total += gathered
        minimum = np.minimum(minimum, gathered)
        final = gathered

    similarity = total / length
    # A pair failing the floor or the anchor is pushed to zero similarity, which
    # makes its distance 1.0 and keeps the two windows in separate clusters.
    similarity = np.where(minimum >= floor, similarity, 0.0)
    if final is not None and anchor > 0:
        similarity = np.where(final >= anchor, similarity, 0.0)

    distance = 1.0 - similarity
    np.fill_diagonal(distance, 0.0)
    distance[distance < 0] = 0.0
    # Guard against float asymmetry, which squareform rejects.
    distance = (distance + distance.T) / 2.0

    linked = linkage(squareform(distance, checks=False), method=method)
    return list(fcluster(linked, t=1.0 - threshold, criterion="distance"))


def detect_chains(
    verse,
    weights=None,
    threshold: float | None = None,
    max_window: int = DEFAULT_MAX_WINDOW,
    min_occurrences: int = DEFAULT_MIN_OCCURRENCES,
    max_line_gap: int = DEFAULT_MAX_LINE_GAP,
) -> list[RhymeChain]:
    """Find the multisyllabic rhyme chains in a verse.

    Chains are selected greedily by strength: the strongest chain claims its
    syllables, and later chains may only use what is left. Because strength is
    proportional to length, a four-syllable chain outranks the one-syllable
    fragments inside it, which is what stops long chains from being shredded.
    """
    import numpy as np

    weights = weights or DEFAULT_WEIGHTS
    threshold = threshold if threshold is not None else weights["cluster_threshold"]

    syllables = verse.syllables()
    if len(syllables) < 2:
        return []

    keys = sorted({rhyme_key(s) for s in syllables if s.nucleus})
    if not keys:
        return []
    key_index = {key: i for i, key in enumerate(keys)}
    key_matrix = _key_similarity_matrix(keys, weights)

    # Stream of key indices; -1 marks a syllable with no usable nucleus.
    stream = np.array([key_index.get(rhyme_key(s), -1) if s.nucleus else -1 for s in syllables])
    line_of_start = [s.line_id for s in syllables]

    candidates: list[RhymeChain] = []

    for length in range(min(max_window, len(syllables)), 0, -1):
        starts = [s for s in _windows_for_length(syllables, length)
                  if not (stream[s:s + length] < 0).any()]
        if len(starts) < min_occurrences:
            continue

        window_keys = np.array([stream[s:s + length] for s in starts])

        # Identical spans collapse to one row; the clustering only needs types.
        unique_rows, inverse = np.unique(window_keys, axis=0, return_inverse=True)
        inverse = inverse.ravel()
        cluster_ids = _cluster_windows(
            unique_rows, key_matrix, threshold,
            floor=weights.get("min_position_similarity", 0.0),
            anchor=weights.get("anchor_similarity", 0.0),
        )
        if not cluster_ids:
            continue
        row_cluster = np.array(cluster_ids)[inverse]

        for cluster in np.unique(row_cluster):
            members = [starts[i] for i in np.nonzero(row_cluster == cluster)[0]]
            if len(members) < min_occurrences:
                continue
            for run in _split_by_locality(members, line_of_start, max_line_gap):
                if len(run) < min_occurrences:
                    continue
                similarity = _mean_pairwise(run, stream, key_matrix, length)
                if similarity < threshold:
                    continue
                candidates.append(RhymeChain(length=length, occurrences=sorted(run), similarity=similarity))

    return _select_greedily(candidates, min_occurrences)


def _split_by_locality(starts, line_of_start, max_line_gap: int) -> list[list[int]]:
    """Split one cluster's occurrences into locally-clustered runs.

    Occurrences separated by more than ``max_line_gap`` lines belong to
    different rhyme events even when they sound identical.
    """
    if max_line_gap is None or max_line_gap <= 0:
        return [list(starts)]

    runs: list[list[int]] = []
    current: list[int] = []
    for start in sorted(starts):
        if current and line_of_start[start] - line_of_start[current[-1]] > max_line_gap:
            runs.append(current)
            current = []
        current.append(start)
    if current:
        runs.append(current)
    return runs


def _mean_pairwise(starts, stream, key_matrix, length: int) -> float:
    """Mean similarity over every pair of occurrences in a cluster."""
    if len(starts) < 2:
        return 1.0
    total = 0.0
    pairs = 0
    for i in range(len(starts)):
        for j in range(i + 1, len(starts)):
            a, b = starts[i], starts[j]
            total += sum(key_matrix[stream[a + k], stream[b + k]] for k in range(length)) / length
            pairs += 1
    return total / pairs if pairs else 1.0


def _select_greedily(candidates: list[RhymeChain], min_occurrences: int) -> list[RhymeChain]:
    """Resolve overlaps, strongest chain first.

    Within a chain, occurrences are also kept non-overlapping: a span repeated at
    positions 4 and 5 of a 3-syllable window is one sound, not two.
    """
    from .engine import RhymeRegistry

    chosen: list[RhymeChain] = []
    used: set[int] = set()

    # Length first, then strength. Strength alone does not work: it is
    # proportional to occurrence count, and a one-syllable "chain" recurring 150
    # times outweighs any four-syllable chain recurring three times. Ordering by
    # strength therefore let the short chains claim the whole verse before a long
    # one was ever considered, which is exactly the shredding this module exists
    # to prevent. Sorting by length first makes a long chain win against the
    # fragments inside it, and strength then ranks chains of equal length.
    for chain in sorted(candidates, key=lambda c: (-c.length, -c.strength, c.occurrences)):
        kept: list[int] = []
        claimed: set[int] = set()
        for start in chain.occurrences:
            span = set(range(start, start + chain.length))
            if span & used or span & claimed:
                continue
            kept.append(start)
            claimed |= span
        if len(kept) < min_occurrences:
            continue
        chain.occurrences = kept
        used |= claimed
        chosen.append(chain)

    chosen.sort(key=lambda c: -c.strength)
    registry = RhymeRegistry()
    for i, chain in enumerate(chosen):
        chain.label = registry.get_label(f"chain-{i}")
    return chosen


def assign_chain_labels(verse, **kwargs) -> list[RhymeChain]:
    """Detect chains and write their labels onto the verse's syllables."""
    for syl in verse.syllables():
        syl.rhyme_label = ""

    chains = detect_chains(verse, **kwargs)
    syllables = verse.syllables()
    for chain in chains:
        for start in chain.occurrences:
            for offset in range(chain.length):
                syllables[start + offset].rhyme_label = chain.label
    return chains


def chain_metrics(verse, chains: list[RhymeChain]) -> dict:
    """Chain-aware metrics for a verse."""
    syllables = verse.syllables()
    total = len(syllables)
    if not total:
        return {"chain_density": 0.0, "multi_score": 0.0, "chains": 0,
                "longest_chain": 0, "mean_chain_length": 0.0}

    covered = set()
    multi_covered = set()
    for chain in chains:
        covered |= chain.covers()
        if chain.length >= 2:
            multi_covered |= chain.covers()

    lengths = [c.length for c in chains]
    return {
        "chain_density": round(len(covered) / total * 100, 1),
        "multi_score": round(len(multi_covered) / total * 100, 1),
        "chains": len(chains),
        "longest_chain": max(lengths, default=0),
        "mean_chain_length": round(sum(lengths) / len(lengths), 2) if lengths else 0.0,
    }
