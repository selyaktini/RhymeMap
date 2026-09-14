"""Run every engine configuration against the gold set and write the table.

    python -m eval.ablation [--output eval/RESULTS.md] [--json eval/results.json]

Each configuration labels every gold verse, its output is projected down to a
line-level partition, and that partition is scored against the annotation.
Two trivial baselines are included: an engine has to beat "put every line in its
own group" and "put every line in one group" before any of its machinery counts
for anything.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from rhymemap.labeling import label_verse
from rhymemap.phonetics import process_verse
from rhymemap.similarity import DEFAULT_WEIGHTS

from .scoring import aggregate_pairwise, bcubed_score, groups_to_labels, mean_score, pairwise_counts, pairwise_score

PROJECT_ROOT = Path(__file__).resolve().parent.parent
GOLD_PATH = PROJECT_ROOT / "eval" / "gold.json"

# Shared across every engine so the comparison isolates the engine itself.
COMMON = {"min_occurrences": 2, "tail_window": None}

# Each configuration adds one idea to the one above it.
CONFIGURATIONS = [
    {
        "name": "all-singletons",
        "kind": "trivial",
        "description": "no grouping at all",
    },
    {
        "name": "all-one-group",
        "kind": "trivial",
        "description": "every line in a single group",
    },
    {
        "name": "exact",
        "kind": "engine",
        "engine": "exact",
        "description": "v1 baseline: vowel + stress + exact coda must match",
    },
    {
        "name": "+consonant classes",
        "kind": "engine",
        "engine": "families",
        "description": "coda consonants replaced by natural class",
    },
    {
        "name": "+vowel space",
        "kind": "engine",
        "engine": "similarity",
        "weights": dict(DEFAULT_WEIGHTS, coda=0.0),
        "description": "articulatory vowel distance, coda ignored",
    },
    {
        "name": "+feature coda",
        "kind": "engine",
        "engine": "similarity",
        "description": "vowel space plus feature-aligned coda distance",
    },
    {
        "name": "-onset penalty",
        "kind": "engine",
        "engine": "similarity",
        "weights": dict(DEFAULT_WEIGHTS, onset_identity_penalty=0.0),
        "description": "full similarity, with the repetition penalty removed",
    },
    {
        "name": "+multisyllabic chains",
        "kind": "engine",
        "engine": "chains",
        "description": "repeated multisyllabic spans, couplet locality window (gap 2)",
    },
    {
        "name": "chains (gap 4)",
        "kind": "engine",
        "engine": "chains",
        "options": {"max_line_gap": 4},
        "description": "chains with a four-line locality window",
    },
    {
        "name": "chains (gap 8)",
        "kind": "engine",
        "engine": "chains",
        "options": {"max_line_gap": 8},
        "description": "chains with an eight-line locality window",
    },
    {
        "name": "chains (no locality)",
        "kind": "engine",
        "engine": "chains",
        "options": {"max_line_gap": 0},
        "description": "chains with the locality constraint disabled",
    },
]


def load_gold(path=GOLD_PATH) -> dict:
    if not Path(path).exists():
        raise FileNotFoundError(f"{path} not found. Build it with: python -m eval.build_gold")
    return json.loads(Path(path).read_text(encoding="utf-8"))


def predict_line_partition(lines, artist: str, config: dict) -> list[int]:
    """Label a verse with one configuration and reduce it to a line partition.

    A line's rhyme identity is the label of its last labelled syllable, which is
    the line-final rhyme the gold set annotates. An unlabelled line becomes a
    singleton.
    """
    if config["kind"] == "trivial":
        return list(range(len(lines))) if config["name"] == "all-singletons" else [0] * len(lines)

    verse = process_verse("\n".join(lines), artist=artist)
    options = dict(COMMON)
    if "weights" in config:
        options["weights"] = config["weights"]
    options.update(config.get("options", {}))
    label_verse(verse, engine=config["engine"], **options)

    labels = []
    next_singleton = 0
    by_label: dict[str, int] = {}
    for line in verse.lines:
        final = ""
        for word in line.words:
            for syl in word.syllables:
                if syl.rhyme_label:
                    final = syl.rhyme_label
        if final:
            if final not in by_label:
                by_label[final] = len(by_label)
            labels.append(by_label[final])
        else:
            labels.append(10_000 + next_singleton)
            next_singleton += 1
    return labels


def evaluate(config: dict, gold: dict) -> dict:
    """Score one configuration over every gold verse."""
    per_verse = []
    for verse in gold["verses"]:
        lines = verse["lines"]
        gold_labels = groups_to_labels(verse["end_rhyme_groups"], len(lines))
        predicted = predict_line_partition(lines, verse["artist"], config)
        per_verse.append({
            "id": verse["id"],
            "artist": verse["artist"],
            "counts": pairwise_counts(predicted, gold_labels),
            "pairwise": pairwise_score(predicted, gold_labels),
            "bcubed": bcubed_score(predicted, gold_labels),
            "groups": len(set(predicted)),
        })

    artists = sorted({v["artist"] for v in per_verse})
    by_artist = {
        artist: aggregate_pairwise([v["counts"] for v in per_verse if v["artist"] == artist]).f1
        for artist in artists
    }

    return {
        "name": config["name"],
        "description": config["description"],
        "pairwise": aggregate_pairwise([v["counts"] for v in per_verse]),
        "bcubed": mean_score([v["bcubed"] for v in per_verse]),
        "by_artist": by_artist,
        "mean_groups": round(sum(v["groups"] for v in per_verse) / len(per_verse), 1),
        "per_verse": per_verse,
    }


def render_markdown(results, gold) -> str:
    artists = sorted({v["artist"] for v in gold["verses"]})
    best_pairwise = max(r["pairwise"].f1 for r in results if r["name"] not in {"all-singletons", "all-one-group"})
    best_bcubed = max(r["bcubed"].f1 for r in results if r["name"] not in {"all-singletons", "all-one-group"})

    out = [
        "# Ablation results",
        "",
        "Generated by `make eval` (`python -m eval.ablation`). Do not edit by hand.",
        "",
        f"Gold set: **{gold['verse_count']} verses, {gold['line_count']} lines, "
        f"{len(artists)} artists**.",
        "",
        "> " + gold["provenance"].replace("\n", "\n> "),
        "",
        "## Overall",
        "",
        "| Configuration | Pairwise P | Pairwise R | Pairwise F1 | B³ P | B³ R | B³ F1 | Mean groups |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in results:
        pw, b3 = r["pairwise"], r["bcubed"]
        name = r["name"]
        if pw.f1 == best_pairwise and name not in {"all-singletons", "all-one-group"}:
            name = f"**{name}**"
        out.append(
            f"| {name} | {pw.precision:.3f} | {pw.recall:.3f} | {pw.f1:.3f} | "
            f"{b3.precision:.3f} | {b3.recall:.3f} | {b3.f1:.3f} | {r['mean_groups']} |"
        )

    out += ["", "## Pairwise F1 per artist", "",
            "| Configuration | " + " | ".join(artists) + " | Overall |",
            "|---" * (len(artists) + 2) + "|"]
    for r in results:
        cells = " | ".join(f"{r['by_artist'].get(a, 0.0):.3f}" for a in artists)
        out.append(f"| {r['name']} | {cells} | {r['pairwise'].f1:.3f} |")

    out += ["", "## What each row adds", ""]
    for r in results:
        out.append(f"- **{r['name']}** — {r['description']}")

    by_name = {r["name"]: r for r in results}

    def f1(name):
        return by_name[name]["pairwise"].f1 if name in by_name else float("nan")

    out += ["", "## Reading this table", "",
            f"The best pairwise F1 is **{best_pairwise:.3f}** and the best B³ F1 is "
            f"**{best_bcubed:.3f}**.",
            "",
            "B³ is the fairer headline: pairwise weights large groups quadratically, so a "
            "configuration that merges everything is flattered by pairwise recall. Compare "
            "each engine against `all-singletons` and `all-one-group` before reading anything "
            "into its score — a row that fails to beat both has not earned its complexity.",
            "",
            "### What the ablation shows", ""]

    exact_f1 = f1("exact")
    families_f1 = f1("+consonant classes")
    vowel_f1 = f1("+vowel space")
    coda_f1 = f1("+feature coda")
    onset_f1 = f1("-onset penalty")

    out += [
        f"**Consonant classes alone barely help.** Wiring `CONSONANT_FAMILIES` into the exact "
        f"engine moves pairwise F1 from {exact_f1:.3f} to {families_f1:.3f}, and B³ F1 actually "
        f"falls ({by_name['exact']['bcubed'].f1:.3f} → {by_name['+consonant classes']['bcubed'].f1:.3f}). "
        "Bucketing consonants into seven classes is too coarse a move to be worth much on its own "
        "— which is worth knowing, since the v1 documentation described this as the headline "
        "feature.",
        "",
        f"**The vowel space is where the gain starts** ({vowel_f1:.3f}), and **feature-aligned "
        f"coda distance is what makes it work** ({coda_f1:.3f}). Treating both the vowel and the "
        "coda as points in a feature space, rather than as symbols to compare for equality, is "
        "the single change that matters.",
        "",
        f"**The onset penalty earns its place.** Removing it costs {coda_f1 - onset_f1:.3f} "
        f"pairwise F1 ({coda_f1:.3f} → {onset_f1:.3f}). Refusing to call repetition a rhyme is "
        "not a detail.",
        "",
        "### The chain engine scores worse here, and that is the honest result",
        "",
        f"`+multisyllabic chains` reaches pairwise F1 {f1('+multisyllabic chains'):.3f}, below the "
        f"{exact_f1:.3f} of the v1 baseline it was meant to improve on. Loosening its locality "
        f"window does not rescue it (best {max(f1('chains (gap 4)'), f1('chains (gap 8)'), f1('chains (no locality)')):.3f}).",
        "",
        "The precision and recall columns say what is happening. Chains have the **highest "
        "precision of any configuration** and by far the lowest recall: what they group, they "
        "group correctly, but they leave most line-final pairs ungrouped.",
        "",
        "The mechanism is that chains answer a different question. They look for repeated "
        "contiguous spans, so a line's final syllable belongs to whichever span it sits in — "
        "which is often a span beginning mid-line and matching something that is not another "
        "line's ending. This gold set annotates line-final rhyme only, so it measures chains on "
        "a task they were not built for.",
        "",
        "That explanation is a caveat, not a defence. On the evidence available, `similarity` is "
        "the better default engine and is set as the default; chains remain the right tool for "
        "*seeing* a verse's multisyllabic structure, which is what they recover on the Rap God "
        "demo. Testing that properly needs span-level annotation this gold set does not have, "
        "and that is the honest limitation to state rather than work around.",
        ""]
    return "\n".join(out)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--gold", default=str(GOLD_PATH))
    parser.add_argument("--output", "-o", default=str(PROJECT_ROOT / "eval" / "RESULTS.md"))
    parser.add_argument("--json", default=str(PROJECT_ROOT / "eval" / "results.json"))
    args = parser.parse_args(argv)

    gold = load_gold(args.gold)
    print(f"gold set: {gold['verse_count']} verses, {gold['line_count']} lines")

    results = []
    for config in CONFIGURATIONS:
        result = evaluate(config, gold)
        results.append(result)
        print(f"  {result['name']:<24} pairwise F1 {result['pairwise'].f1:.3f}   "
              f"B3 F1 {result['bcubed'].f1:.3f}")

    Path(args.output).write_text(render_markdown(results, gold), encoding="utf-8")
    Path(args.json).write_text(json.dumps([
        {
            "name": r["name"],
            "description": r["description"],
            "pairwise": r["pairwise"].as_dict(),
            "bcubed": r["bcubed"].as_dict(),
            "by_artist_pairwise_f1": {k: round(v, 4) for k, v in r["by_artist"].items()},
            "mean_groups": r["mean_groups"],
        } for r in results
    ], indent=2) + "\n", encoding="utf-8")

    print(f"\nwrote {args.output} and {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
