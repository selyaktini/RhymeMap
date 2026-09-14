"""Shared paths and plotting configuration for the analysis module."""

from __future__ import annotations

import os
from pathlib import Path

import matplotlib

# Select a non-interactive backend before pyplot is imported unless a display is
# present. `make plots` must work over SSH and in CI, where the old plt.show()
# calls would either block or fail.
if not os.environ.get("DISPLAY") and os.environ.get("MPLBACKEND") is None:
    matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402  (import order is deliberate)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
STATS_FILE = DATA_DIR / "stats.csv"
FIGURES_DIR = DATA_DIR

COLORS = plt.cm.tab10.colors

# Metric columns used for similarity/clustering.
FEATURE_COLUMNS = ["Density", "Multi", "Diversity", "Signatures", "Syll."]


def interactive() -> bool:
    """True when figures can be shown on screen rather than only written out."""
    return matplotlib.get_backend().lower() not in {"agg", "pdf", "ps", "svg", "template"}
