"""Demo entry point.

    python -m rhymemap.main                 # coloured verse + dataset table
    python -m rhymemap.main --file X.txt    # analyse your own lyrics
"""

from __future__ import annotations

import argparse
from pathlib import Path

from .analyzer import DEFAULT_DATASET, DatasetError, analyze_dataset
from .cache import flush_all
from .labeling import ENGINE_CHOICES, ENGINE_HELP, ENGINE_SIMILARITY, label_verse
from .metrics import compute_metrics
from .phonetics import process_verse
from .visual import VisualEngine

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEMO_LYRICS = PROJECT_ROOT / "dataset" / "demo_rap_god.txt"


def show_verse(path: Path, artist: str, min_occurrences: int, tail_window, legend: bool, engine: str) -> None:
    """Analyse one lyrics file and print it with rhyming syllables coloured."""
    if not path.exists():
        print(f"error: lyrics file not found: {path}")
        return

    verse = process_verse(path.read_text(encoding="utf-8"), artist=artist)
    label_verse(verse, engine=engine, min_occurrences=min_occurrences, tail_window=tail_window)

    VisualEngine().display(verse, legend=legend)
    metrics = compute_metrics(verse)
    print(
        f"density {metrics['density']}%   multi {metrics['multi']}%   "
        f"diversity {metrics['diversity']}%   groups {metrics['signatures']}   "
        f"syllables {metrics['syllables']}"
    )


def show_dataset(csv_path: str, min_occurrences: int, engine: str) -> None:
    """Print the per-track metric table for a corpus."""
    print(f"\n=== Corpus analysis: {csv_path} ===")
    try:
        rows = analyze_dataset(csv_path, min_occurrences=min_occurrences, progress=False, engine=engine)
    except DatasetError as exc:
        print(f"error: {exc}")
        return
    if not rows:
        print("no usable rows")
        return

    header = "{:<28} {:<16} {:>9} {:>8} {:>10} {:>7} {:>7}".format(
        "Track", "Artist", "Density", "Multi", "Diversity", "Groups", "Syll."
    )
    print(header)
    print("-" * len(header))
    for row in rows:
        print("{:<28} {:<16} {:>8.1f}% {:>7.1f}% {:>9.1f}% {:>7} {:>7}".format(
            row["Track Name"][:27], row["Artist"][:15], row["Density"],
            row["Multi"], row["Diversity"], row["Signatures"], row["Syll."],
        ))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--file", "-f", type=Path, default=DEMO_LYRICS, help="lyrics text file to visualise")
    parser.add_argument("--artist", "-a", default="Eminem", help="artist name for the header")
    parser.add_argument("--min-occurrences", type=int, default=3, help="minimum signature count to label (default: 3)")
    parser.add_argument("--tail-window", type=int, default=8, help="only label the last N syllables per line (default: 8)")
    parser.add_argument("--legend", action="store_true", help="list the rhyme groups after the verse")
    parser.add_argument("--dataset", default=DEFAULT_DATASET, help="corpus CSV for the summary table")
    parser.add_argument("--no-dataset", action="store_true", help="skip the corpus table")
    parser.add_argument("--engine", "-e", default=ENGINE_SIMILARITY, choices=ENGINE_CHOICES,
                        help="; ".join(f"{k}: {v}" for k, v in ENGINE_HELP.items()))
    args = parser.parse_args(argv)

    show_verse(args.file, args.artist, args.min_occurrences, args.tail_window, args.legend, args.engine)
    if not args.no_dataset:
        show_dataset(args.dataset, args.min_occurrences, args.engine)
    flush_all()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
