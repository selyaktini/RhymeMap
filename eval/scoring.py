"""Clustering metrics for comparing a predicted rhyme partition to the gold one.

Both metrics are standard for evaluating clusterings against a reference when
the cluster *labels* are arbitrary — only the grouping matters.

**Pairwise P/R/F1** looks at every pair of lines in a verse and asks whether the
two partitions agree on grouping that pair. It is easy to interpret but weights
large groups quadratically: one 6-line group contributes 15 pairs while three
2-line groups contribute 3.

**B-cubed** scores each line individually by how much its predicted group
overlaps its gold group, then averages. Large groups cannot dominate, which
makes it the fairer headline number when group sizes are uneven — as they are
here, where refrains produce one big group and most other lines pair up.

Both are reported, because an engine that over-merges scores well on pairwise
recall while B-cubed precision exposes it.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Score:
    precision: float
    recall: float

    @property
    def f1(self) -> float:
        if self.precision + self.recall == 0:
            return 0.0
        return 2 * self.precision * self.recall / (self.precision + self.recall)

    def as_dict(self) -> dict:
        return {"precision": round(self.precision, 4),
                "recall": round(self.recall, 4),
                "f1": round(self.f1, 4)}


def groups_to_labels(groups, size: int) -> list[int]:
    """Turn ``[[0,2],[1]]`` into a per-line group id, e.g. ``[0,1,0]``."""
    labels = [-1] * size
    for group_id, group in enumerate(groups):
        for index in group:
            if 0 <= index < size:
                labels[index] = group_id
    # Anything unassigned becomes its own singleton.
    next_id = len(groups)
    for i, label in enumerate(labels):
        if label < 0:
            labels[i] = next_id
            next_id += 1
    return labels


def _pair_set(labels) -> set:
    """Every co-grouped index pair."""
    return {
        (i, j)
        for i in range(len(labels))
        for j in range(i + 1, len(labels))
        if labels[i] == labels[j]
    }


def pairwise_counts(predicted, gold) -> tuple[int, int, int]:
    """(true positives, false positives, false negatives) over line pairs."""
    predicted_pairs = _pair_set(predicted)
    gold_pairs = _pair_set(gold)
    true_positive = len(predicted_pairs & gold_pairs)
    return true_positive, len(predicted_pairs) - true_positive, len(gold_pairs) - true_positive


def pairwise_score(predicted, gold) -> Score:
    tp, fp, fn = pairwise_counts(predicted, gold)
    precision = tp / (tp + fp) if tp + fp else 1.0
    recall = tp / (tp + fn) if tp + fn else 1.0
    return Score(precision, recall)


def bcubed_score(predicted, gold) -> Score:
    """B-cubed precision and recall, averaged over lines."""
    if not predicted:
        return Score(1.0, 1.0)

    precision_total = 0.0
    recall_total = 0.0
    for i in range(len(predicted)):
        predicted_group = {j for j in range(len(predicted)) if predicted[j] == predicted[i]}
        gold_group = {j for j in range(len(gold)) if gold[j] == gold[i]}
        overlap = len(predicted_group & gold_group)
        precision_total += overlap / len(predicted_group)
        recall_total += overlap / len(gold_group)

    n = len(predicted)
    return Score(precision_total / n, recall_total / n)


def aggregate_pairwise(per_verse_counts) -> Score:
    """Pool pair counts across verses before computing P/R (micro-average).

    Averaging each verse's F1 would give a three-line verse the same weight as a
    sixteen-line one.
    """
    tp = sum(c[0] for c in per_verse_counts)
    fp = sum(c[1] for c in per_verse_counts)
    fn = sum(c[2] for c in per_verse_counts)
    precision = tp / (tp + fp) if tp + fp else 1.0
    recall = tp / (tp + fn) if tp + fn else 1.0
    return Score(precision, recall)


def mean_score(scores) -> Score:
    """Unweighted mean of per-verse scores, for B-cubed."""
    scores = list(scores)
    if not scores:
        return Score(1.0, 1.0)
    return Score(
        sum(s.precision for s in scores) / len(scores),
        sum(s.recall for s in scores) / len(scores),
    )
