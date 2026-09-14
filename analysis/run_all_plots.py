"""Generate every analysis figure into data/.

    python -m analysis.run_all_plots [--show] [--stats CSV]
"""

from __future__ import annotations

import argparse
import sys

from .config import FIGURES_DIR
from .data_loader import StatsNotFound, load_stats
from .plots import (
    artist_dendrogram,
    artist_similarity,
    boxplot_density,
    scatter_all_tracks,
    scatter_artist_averages,
    similarity_heatmap,
)

# Artists that get their own per-track heatmap, when present in the data.
FEATURED_ARTISTS = ["Drake", "Eminem", "Kendrick Lamar", "J. Cole"]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--stats", default=None, help="stats CSV (default: data/stats.csv)")
    parser.add_argument("--show", action="store_true", help="also display figures interactively")
    args = parser.parse_args(argv)

    try:
        df = load_stats(args.stats)
    except StatsNotFound as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if df.empty:
        print("error: stats file has no usable rows", file=sys.stderr)
        return 1

    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    print(f"generating figures from {len(df)} tracks into {FIGURES_DIR}/")

    scatter_all_tracks(df, FIGURES_DIR / "scatter_all.png", args.show)
    scatter_artist_averages(df, FIGURES_DIR / "artist_averages.png", args.show)
    boxplot_density(df, FIGURES_DIR / "boxplot_density.png", args.show)
    artist_similarity(df, FIGURES_DIR / "artist_similarity.png", args.show)
    artist_dendrogram(df, FIGURES_DIR / "artist_dendrogram.png", args.show)

    for artist in FEATURED_ARTISTS:
        if artist in set(df["Artist"]):
            safe = artist.replace(" ", "_").replace(".", "")
            similarity_heatmap(df, artist, FIGURES_DIR / f"similarity_{safe}.png", args.show)

    print("done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
