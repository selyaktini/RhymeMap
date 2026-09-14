"""CLI: analyse a lyrics CSV and write the metrics table.

    python -m scripts.generate_stats [--input CSV] [--output CSV]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from rhymemap.analyzer import DEFAULT_DATASET, DatasetError, analyze_dataset
from rhymemap.cache import flush_all
from rhymemap.labeling import ENGINE_CHOICES, ENGINE_HELP, ENGINE_SIMILARITY
from rhymemap.metrics import CSV_COLUMNS


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", "-i", default=DEFAULT_DATASET, help=f"input lyrics CSV (default: {DEFAULT_DATASET})")
    parser.add_argument("--output", "-o", default="data/stats.csv", help="output metrics CSV (default: data/stats.csv)")
    parser.add_argument("--min-occurrences", type=int, default=3, help="minimum times a signature must appear (default: 3)")
    parser.add_argument("--tail-window", type=int, default=None, help="only consider the last N syllables of each line")
    parser.add_argument("--only-terminal", action="store_true", help="only consider line-final syllables (end rhyme)")
    parser.add_argument("--max-rows", type=int, default=None, help="stop after N rows")
    parser.add_argument("--engine", "-e", default=ENGINE_SIMILARITY, choices=ENGINE_CHOICES,
                        help="; ".join(f"{k}: {v}" for k, v in ENGINE_HELP.items()))
    parser.add_argument("--quiet", "-q", action="store_true", help="suppress per-track progress")
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)

    try:
        rows = analyze_dataset(
            args.input,
            min_occurrences=args.min_occurrences,
            tail_window=args.tail_window,
            only_terminal=args.only_terminal,
            max_rows=args.max_rows,
            progress=not args.quiet,
            engine=args.engine,
        )
    except DatasetError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if not rows:
        print(f"error: no usable rows in {args.input}", file=sys.stderr)
        return 1

    import pandas as pd

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows)[CSV_COLUMNS].to_csv(output, index=False)
    flush_all()

    print(f"\nwrote {output} ({len(rows)} tracks)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
