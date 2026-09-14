"""Loading and aggregating the generated stats table."""

from __future__ import annotations

import pandas as pd

from .config import FEATURE_COLUMNS, STATS_FILE


class StatsNotFound(FileNotFoundError):
    """Raised when stats.csv has not been generated yet."""


def load_stats(path=None) -> pd.DataFrame:
    """Read stats.csv, dropping rows with missing metrics."""
    path = path or STATS_FILE
    try:
        df = pd.read_csv(path)
    except FileNotFoundError as exc:
        raise StatsNotFound(
            f"{path} not found. Generate it first:\n"
            f"    make stats      (or: python -m scripts.generate_stats)"
        ) from exc

    present = [c for c in FEATURE_COLUMNS if c in df.columns]
    missing = [c for c in FEATURE_COLUMNS if c not in df.columns]
    if missing:
        print(f"note: {path} predates columns {missing}; regenerate with `make stats` for the full analysis.")
    return df.dropna(subset=present)


def get_artist_means(df: pd.DataFrame) -> pd.DataFrame:
    """Mean of each metric per artist."""
    present = [c for c in FEATURE_COLUMNS if c in df.columns]
    return df.groupby("Artist")[present].mean().reset_index()
