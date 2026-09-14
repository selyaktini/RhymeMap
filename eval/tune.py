"""Sweep the similarity weights against the gold set.

    python -m eval.tune [--param cluster_threshold] [--json eval/tuning.json]

Reports pairwise and B-cubed F1 for each value so the defaults in
``DEFAULT_WEIGHTS`` are chosen from evidence rather than taste.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from rhymemap.similarity import DEFAULT_WEIGHTS

from .ablation import GOLD_PATH, evaluate, load_gold

PROJECT_ROOT = Path(__file__).resolve().parent.parent

SWEEPS = {
    "cluster_threshold": [0.60, 0.66, 0.70, 0.74, 0.78, 0.82, 0.86, 0.90, 0.94],
    "onset_identity_penalty": [0.0, 0.15, 0.25, 0.35, 0.50, 0.65],
    "nucleus": [0.40, 0.50, 0.60, 0.70, 0.80],
    "coda": [0.10, 0.20, 0.30, 0.40, 0.50],
    "stress": [0.0, 0.05, 0.10, 0.20, 0.30],
}


def sweep(param: str, values, gold, engine: str = "similarity") -> list[dict]:
    rows = []
    for value in values:
        config = {
            "name": f"{param}={value}",
            "kind": "engine",
            "engine": engine,
            "weights": dict(DEFAULT_WEIGHTS, **{param: value}),
            "description": f"{param} set to {value}",
        }
        result = evaluate(config, gold)
        rows.append({
            "value": value,
            "pairwise_f1": round(result["pairwise"].f1, 4),
            "bcubed_f1": round(result["bcubed"].f1, 4),
            "mean_groups": result["mean_groups"],
        })
        print(f"  {param:<24} {value:<6} pairwise F1 {result['pairwise'].f1:.3f}   "
              f"B3 F1 {result['bcubed'].f1:.3f}   groups {result['mean_groups']}")
    return rows


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--param", default=None, choices=sorted(SWEEPS), help="sweep one parameter (default: all)")
    parser.add_argument("--gold", default=str(GOLD_PATH))
    parser.add_argument("--json", default=str(PROJECT_ROOT / "eval" / "tuning.json"))
    args = parser.parse_args(argv)

    gold = load_gold(args.gold)
    params = [args.param] if args.param else list(SWEEPS)

    out = {}
    for param in params:
        print(f"\nsweeping {param}")
        rows = sweep(param, SWEEPS[param], gold)
        best = max(rows, key=lambda r: r["bcubed_f1"])
        out[param] = {"current_default": DEFAULT_WEIGHTS.get(param), "rows": rows, "best_by_bcubed": best}
        print(f"  -> best B3 F1 at {param}={best['value']} ({best['bcubed_f1']:.3f}); "
              f"current default is {DEFAULT_WEIGHTS.get(param)}")

    Path(args.json).write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(f"\nwrote {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
