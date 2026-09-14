"""Verse-level metrics — the single definition used everywhere.

Before this module there were two different formulas both exported as "Multi":

  * ``scripts/generate_stats.py`` computed distinct signatures / total syllables
    (a *diversity* measure);
  * ``rhymemap/analyzer.py`` counted adjacent labelled syllables *without checking
    that the labels matched*, so "cat ... dog" scored as a multisyllabic rhyme
    purely because both syllables happened to be labelled.

They fed the same CSV column and the same plots. The names are now separated and
the adjacency check is real:

``density``     percentage of syllables carrying any rhyme label.
``multi``       percentage of syllables inside a run of >= 2 consecutive
                syllables sharing the *same* label. This is the repaired
                version of the adjacency metric and the honest measure of
                multisyllabic rhyme available to the v1 engine.
``diversity``   distinct rhyme groups / total syllables, as a percentage. High
                diversity means many small groups rather than a few large ones.
``signatures``  number of distinct rhyme groups present.
``syllables``   total syllable count.
"""

from __future__ import annotations

MIN_RUN = 2   # syllables needed to count as "multisyllabic"


def multisyllabic_runs(syllables, min_run: int = MIN_RUN) -> list[tuple[int, int, str]]:
    """Find maximal runs of consecutive syllables sharing one rhyme label.

    Returns ``[(start_index, length, label), ...]`` for runs of at least
    ``min_run``. Unlabelled syllables break a run.
    """
    runs = []
    start = 0
    while start < len(syllables):
        label = syllables[start].rhyme_label
        if not label:
            start += 1
            continue
        end = start + 1
        while end < len(syllables) and syllables[end].rhyme_label == label:
            end += 1
        if end - start >= min_run:
            runs.append((start, end - start, label))
        start = end
    return runs


def compute_metrics(verse, min_run: int = MIN_RUN) -> dict:
    """Metrics for one labelled verse. Call after ``assign_rhyme_labels``."""
    syllables = verse.syllables()
    total = len(syllables)
    if total == 0:
        return {"density": 0.0, "multi": 0.0, "diversity": 0.0, "signatures": 0, "syllables": 0}

    labelled = sum(1 for syl in syllables if syl.rhyme_label)
    groups = {syl.rhyme_label for syl in syllables if syl.rhyme_label}
    in_runs = sum(length for _, length, _ in multisyllabic_runs(syllables, min_run))

    return {
        "density": round(labelled / total * 100, 1),
        "multi": round(in_runs / total * 100, 1),
        "diversity": round(len(groups) / total * 100, 1),
        "signatures": len(groups),
        "syllables": total,
    }


# Column order shared by the stats CSV and the analysis loader.
CSV_COLUMNS = ["Track Name", "Artist", "Density", "Multi", "Diversity", "Signatures", "Syll."]


def metrics_to_row(track: str, artist: str, metrics: dict) -> dict:
    return {
        "Track Name": track,
        "Artist": artist,
        "Density": metrics["density"],
        "Multi": metrics["multi"],
        "Diversity": metrics["diversity"],
        "Signatures": metrics["signatures"],
        "Syll.": metrics["syllables"],
    }
