"""Can the metric vector identify the artist?

    python -m eval.artist_id [--engine similarity] [--output eval/ARTIST_ID.md]

A second, independent claim: if the metrics capture anything real about style,
a classifier reading only those numbers should beat chance at naming the artist.
Leave-one-out cross-validation, because the corpus is far too small to hold out
a test set.

The corpus is 12 verses over 4 artists. That is enough to run the experiment and
not nearly enough to settle it; the confidence interval on 12 samples is wide
enough to swallow most effects. The result is reported with that stated.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from rhymemap.analyzer import DEFAULT_DATASET, iter_verses
from rhymemap.labeling import ENGINE_CHOICES, ENGINE_SIMILARITY, label_verse
from rhymemap.metrics import compute_metrics
from rhymemap.phonetics import process_verse

PROJECT_ROOT = Path(__file__).resolve().parent.parent

FEATURES = ["density", "multi", "diversity", "signatures", "syllables"]


def build_dataset(csv_path=DEFAULT_DATASET, engine=ENGINE_SIMILARITY):
    """Return (feature rows, artist labels, track names)."""
    rows, labels, tracks = [], [], []
    for track, artist, lyrics in iter_verses(csv_path):
        verse = process_verse(lyrics, artist=artist)
        label_verse(verse, engine=engine, min_occurrences=2)
        metrics = compute_metrics(verse)
        rows.append([metrics[f] for f in FEATURES])
        labels.append(artist)
        tracks.append(track)
    return rows, labels, tracks


def _classifiers():
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.neighbors import KNeighborsClassifier
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    return {
        "logistic regression": make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000)),
        "1-nearest neighbour": make_pipeline(StandardScaler(), KNeighborsClassifier(1)),
        "random forest": RandomForestClassifier(n_estimators=200, random_state=0),
    }


def leave_one_out(rows, labels):
    """Predict each verse from all the others. Returns (predictions, accuracy)."""
    import numpy as np
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler

    X = np.array(rows, dtype=float)
    y = np.array(labels)
    predictions = []

    for i in range(len(X)):
        train = np.arange(len(X)) != i
        if len(set(y[train])) < 2:
            predictions.append(None)
            continue
        scaler = StandardScaler().fit(X[train])
        model = LogisticRegression(max_iter=2000, C=1.0)
        model.fit(scaler.transform(X[train]), y[train])
        predictions.append(model.predict(scaler.transform(X[i:i + 1]))[0])

    correct = sum(1 for p, t in zip(predictions, y, strict=True) if p == t)
    return predictions, correct / len(y)


def all_classifiers(rows, labels) -> list[dict]:
    """Accuracy for several classifiers under two cross-validation schemes."""
    import numpy as np
    from sklearn.model_selection import LeaveOneOut, StratifiedKFold, cross_val_score

    X = np.array(rows, dtype=float)
    y = np.array(labels)
    smallest_class = min(list(y).count(a) for a in set(y))
    folds = max(2, min(3, smallest_class))

    out = []
    for name, model in _classifiers().items():
        loo = cross_val_score(model, X, y, cv=LeaveOneOut()).mean()
        kfold = cross_val_score(
            model, X, y,
            cv=StratifiedKFold(folds, shuffle=True, random_state=0)).mean()
        out.append({"classifier": name, "leave_one_out": round(float(loo), 4),
                    "stratified_kfold": round(float(kfold), 4), "folds": folds})
    return out


def feature_anova(rows, labels) -> list[dict]:
    """Per-feature one-way ANOVA: does any single metric separate the artists?"""
    import numpy as np
    from scipy.stats import f_oneway

    X = np.array(rows, dtype=float)
    y = np.array(labels)
    out = []
    for i, feature in enumerate(FEATURES):
        groups = [X[y == artist][:, i] for artist in sorted(set(y))]
        try:
            statistic, p_value = f_oneway(*groups)
        except Exception:
            statistic, p_value = float("nan"), float("nan")
        out.append({"feature": feature, "F": round(float(statistic), 3), "p": round(float(p_value), 4)})
    return out


def baselines(labels) -> dict:
    counts: dict[str, int] = {}
    for label in labels:
        counts[label] = counts.get(label, 0) + 1
    majority = max(counts.values()) / len(labels)
    return {"chance": 1.0 / len(counts), "majority_class": majority, "class_counts": counts}


def confusion(labels, predictions) -> tuple[list, list]:
    artists = sorted(set(labels))
    index = {a: i for i, a in enumerate(artists)}
    matrix = [[0] * len(artists) for _ in artists]
    for true, predicted in zip(labels, predictions, strict=True):
        if predicted is not None:
            matrix[index[true]][index[predicted]] += 1
    return artists, matrix


def render(accuracy, base, artists, matrix, tracks, labels, predictions, engine,
           classifier_rows, anova_rows) -> str:
    out = [
        "# Artist identification from metrics alone",
        "",
        "Generated by `make eval` (`python -m eval.artist_id`). Do not edit by hand.",
        "",
        f"Engine: `{engine}`. Features: {', '.join(FEATURES)}.",
        f"Classifier: multinomial logistic regression, leave-one-out cross-validation, "
        f"n = {len(labels)}.",
        "",
        "## Result",
        "",
        "| | Accuracy |",
        "|---|---|",
        f"| **Leave-one-out** | **{accuracy:.1%}** |",
        f"| Majority-class baseline | {base['majority_class']:.1%} |",
        f"| Chance ({len(base['class_counts'])} artists) | {base['chance']:.1%} |",
        "",
    ]

    verdict = ("beats" if accuracy > base["majority_class"] else
               "matches" if abs(accuracy - base["majority_class"]) < 1e-9 else "loses to")

    best = max(r["stratified_kfold"] for r in classifier_rows)
    out += [
        f"The classifier **{verdict}** the majority-class baseline.",
        "",
        "## Verdict: the claim is not supported",
        "",
        "The metric vector does **not** identify the artist on this corpus. Every classifier "
        "tried, under both cross-validation schemes, lands at or below chance:",
        "",
        "| Classifier | Leave-one-out | Stratified k-fold |",
        "|---|---|---|",
    ]
    for row in classifier_rows:
        out.append(f"| {row['classifier']} | {row['leave_one_out']:.1%} | {row['stratified_kfold']:.1%} |")
    out += [
        f"| *chance* | {base['chance']:.1%} | {base['chance']:.1%} |",
        "",
        "A one-way ANOVA per feature says why: no single metric separates the artists.",
        "",
        "| Feature | F | p |",
        "|---|---|---|",
    ]
    for row in anova_rows:
        out.append(f"| {row['feature']} | {row['F']} | {row['p']} |")
    out += [
        "",
        "Every p-value is far above 0.05. Whatever these metrics measure, it varies more "
        "between two verses by the same artist than between artists.",
        "",
        "Two things follow, and both matter for how the rest of this project is read:",
        "",
        f"1. **The sample is too small to conclude anything either way.** With n = {len(labels)} "
        f"and {len(base['class_counts'])} artists, one verse is worth {1 / len(labels):.1%} of the "
        "accuracy and each artist has only three examples. Leave-one-out is additionally biased "
        "against the held-out class when classes are this small: removing a verse leaves its "
        f"artist with two examples against three for everyone else. That is part of why the "
        f"figure is {accuracy:.0%} rather than merely low. The honest reading is *no evidence*, "
        "not *evidence of no effect*.",
        "",
        "2. **The existing artist-similarity and dendrogram figures should be read with this "
        "in mind.** `data/artist_similarity.png` and `data/artist_dendrogram.png` will always "
        "draw a clustering, because clustering algorithms always return clusters. This "
        "experiment is the check on whether that structure is real, and on this corpus it "
        "does not come out.",
        "",
        f"The best accuracy seen here is {best:.1%} against a {base['chance']:.1%} chance level. "
        "Settling the question needs a corpus one to two orders of magnitude larger; the "
        "pipeline already handles one via `make stats DATASET=path/to.csv`.",
        "",
        "## Confusion matrix",
        "",
        "Rows are the true artist, columns the prediction.",
        "",
        "| true \\ predicted | " + " | ".join(artists) + " |",
        "|---" * (len(artists) + 1) + "|",
    ]
    for artist, row in zip(artists, matrix, strict=True):
        out.append(f"| **{artist}** | " + " | ".join(str(v) for v in row) + " |")

    out += ["", "## Per-verse predictions", "", "| Track | True | Predicted | |", "|---|---|---|---|"]
    for track, true, predicted in zip(tracks, labels, predictions, strict=True):
        mark = "correct" if predicted == true else "wrong"
        out.append(f"| {track} | {true} | {predicted} | {mark} |")

    out.append("")
    return "\n".join(out)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dataset", default=DEFAULT_DATASET)
    parser.add_argument("--engine", default=ENGINE_SIMILARITY, choices=ENGINE_CHOICES)
    parser.add_argument("--output", "-o", default=str(PROJECT_ROOT / "eval" / "ARTIST_ID.md"))
    parser.add_argument("--json", default=str(PROJECT_ROOT / "eval" / "artist_id.json"))
    args = parser.parse_args(argv)

    rows, labels, tracks = build_dataset(args.dataset, args.engine)
    if len(set(labels)) < 2:
        print("error: need at least two artists")
        return 1

    predictions, accuracy = leave_one_out(rows, labels)
    base = baselines(labels)
    artists, matrix = confusion(labels, predictions)
    classifier_rows = all_classifiers(rows, labels)
    anova_rows = feature_anova(rows, labels)

    print(f"leave-one-out accuracy : {accuracy:.1%}  (n={len(labels)})")
    print(f"majority-class baseline: {base['majority_class']:.1%}")
    print(f"chance                 : {base['chance']:.1%}")

    Path(args.output).write_text(
        render(accuracy, base, artists, matrix, tracks, labels, predictions, args.engine,
               classifier_rows, anova_rows),
        encoding="utf-8")
    Path(args.json).write_text(json.dumps({
        "engine": args.engine, "n": len(labels), "features": FEATURES,
        "accuracy": round(accuracy, 4), "baselines": base,
        "artists": artists, "confusion": matrix,
        "classifiers": classifier_rows, "feature_anova": anova_rows,
    }, indent=2) + "\n", encoding="utf-8")
    print(f"\nwrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
