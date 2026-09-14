"""Batch analysis of a lyrics CSV.

This is the one implementation of the corpus pipeline. ``scripts/generate_stats``
is a thin CLI over it; previously the two files each carried their own copy of
the loop with divergent metric definitions.
"""

from __future__ import annotations

from pathlib import Path

from .labeling import ENGINE_SIMILARITY, label_verse
from .metrics import compute_metrics, metrics_to_row
from .phonetics import process_verse

LYRICS_COLUMNS = ("artist_verses", "raw_lyrics", "lyrics")
DEFAULT_DATASET = "dataset/artists_sample.csv"


class DatasetError(Exception):
    """Raised for a missing or unusable dataset, with an actionable message."""


def _read_csv(csv_path):
    import pandas as pd

    path = Path(csv_path)
    if not path.exists():
        raise DatasetError(
            f"Dataset not found: {path}\n"
            f"Expected a CSV with columns: track_name, artist, and one of {', '.join(LYRICS_COLUMNS)}.\n"
            f"The repository ships {DEFAULT_DATASET}; pass --input to use another file."
        )
    try:
        return pd.read_csv(path)
    except Exception as exc:
        raise DatasetError(f"Could not read {path} as CSV: {exc}") from exc


def _pick_lyrics_column(df):
    for column in LYRICS_COLUMNS:
        if column in df.columns:
            return column
    raise DatasetError(
        f"No lyrics column found. Looked for {', '.join(LYRICS_COLUMNS)}; "
        f"the file has: {', '.join(map(str, df.columns))}"
    )


def iter_verses(csv_path=DEFAULT_DATASET, max_rows=None):
    """Yield ``(track, artist, lyrics)`` triples from a lyrics CSV."""

    df = _read_csv(csv_path)
    lyrics_column = _pick_lyrics_column(df)
    for column in ("track_name", "artist"):
        if column not in df.columns:
            raise DatasetError(f"Dataset {csv_path} is missing required column '{column}'.")

    for i, row in df.iterrows():
        if max_rows is not None and i >= max_rows:
            break
        lyrics = row[lyrics_column]
        if not isinstance(lyrics, str) or not lyrics.strip():
            continue
        # Some exports escape newlines inside the CSV field.
        yield str(row["track_name"]), str(row["artist"]), lyrics.replace("\\n", "\n")


def analyze_dataset(
    csv_path=DEFAULT_DATASET,
    min_occurrences: int = 3,
    tail_window: int | None = None,
    only_terminal: bool = False,
    max_rows=None,
    progress=False,
    engine: str = ENGINE_SIMILARITY,
    **engine_options,
) -> list[dict]:
    """Analyse every verse in a CSV and return metric rows, densest first."""
    rows = []
    for track, artist, lyrics in iter_verses(csv_path, max_rows=max_rows):
        try:
            verse = process_verse(lyrics, artist=artist)
            label_verse(
                verse,
                engine=engine,
                min_occurrences=min_occurrences,
                tail_window=tail_window,
                only_terminal=only_terminal,
                **engine_options,
            )
            metrics = compute_metrics(verse)
            rows.append(metrics_to_row(track, artist, metrics))
            if progress:
                print(f"  ok  {track[:40]:<40} density={metrics['density']:>5}%  multi={metrics['multi']:>5}%")
        except Exception as exc:                      # keep going on one bad row
            print(f"  !!  {track[:40]:<40} skipped: {type(exc).__name__}: {exc}")

    rows.sort(key=lambda r: r["Density"], reverse=True)
    return rows
