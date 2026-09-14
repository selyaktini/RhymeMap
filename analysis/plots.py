"""Figure generation. Every function saves to a path and closes its figure."""

from __future__ import annotations

import pandas as pd
import seaborn as sns
from scipy.cluster.hierarchy import dendrogram, linkage
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import MinMaxScaler, StandardScaler

from .config import COLORS, FEATURE_COLUMNS, interactive, plt
from .data_loader import get_artist_means


def _finish(save_path, show: bool) -> None:
    """Save and/or show one figure, then release it."""
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches="tight")
        print(f"  wrote {save_path}")
    if show and interactive():
        plt.show()
    plt.close()


def _features(df: pd.DataFrame) -> list[str]:
    return [c for c in FEATURE_COLUMNS if c in df.columns]


def scatter_all_tracks(df, save_path=None, show=False):
    """Density vs Multi, one point per track, coloured by artist."""
    plt.figure(figsize=(10, 6))
    for i, artist in enumerate(df["Artist"].unique()):
        subset = df[df["Artist"] == artist]
        plt.scatter(subset["Density"], subset["Multi"], label=artist,
                    alpha=0.7, s=80, color=COLORS[i % len(COLORS)])
    plt.xlabel("Rhyme density (%)", fontsize=12)
    plt.ylabel("Multisyllabic rhyme (%)", fontsize=12)
    plt.title("Density vs multisyllabic rhyme (all tracks)")
    plt.legend(bbox_to_anchor=(1.05, 1), loc="upper left")
    plt.grid(True, linestyle="--", alpha=0.5)
    _finish(save_path, show)


def scatter_artist_averages(df, save_path=None, show=False):
    """Mean position of each artist in the density/multi plane."""
    means = get_artist_means(df)
    plt.figure(figsize=(10, 6))
    for i, row in means.iterrows():
        plt.scatter(row["Density"], row["Multi"], s=200, color=COLORS[i % len(COLORS)])
        plt.annotate(row["Artist"], (row["Density"], row["Multi"]),
                     xytext=(5, 5), textcoords="offset points", fontsize=9)
    plt.xlabel("Mean density (%)", fontsize=12)
    plt.ylabel("Mean multisyllabic rhyme (%)", fontsize=12)
    plt.title("Artist averages: density vs multisyllabic rhyme")
    plt.grid(True, linestyle="--", alpha=0.5)
    _finish(save_path, show)


def boxplot_density(df, save_path=None, show=False):
    """Distribution of density per artist."""
    plt.figure(figsize=(12, 6))
    sns.boxplot(data=df, x="Artist", y="Density", hue="Artist", palette="Set2", legend=False)
    plt.xticks(rotation=45, ha="right")
    plt.ylabel("Rhyme density (%)")
    plt.title("Density distribution per artist")
    _finish(save_path, show)


def similarity_heatmap(df, artist=None, save_path=None, show=False, max_name_len=25, max_items=20):
    """Cosine similarity between an artist's tracks over the metric vector."""
    if artist:
        df = df[df["Artist"] == artist]
    if len(df) < 2:
        print(f"  skip similarity for {artist}: needs >= 2 tracks, has {len(df)}")
        return
    if len(df) > max_items:
        print(f"  {artist}: {len(df)} tracks, showing first {max_items}")
        df = df.head(max_items)

    features = _features(df)
    similarity = cosine_similarity(MinMaxScaler().fit_transform(df[features].values))

    names = [n[: max_name_len - 3] + "..." if len(n) > max_name_len else n for n in df["Track Name"]]
    size = max(8, len(df) * 0.6)
    plt.figure(figsize=(size, max(6, len(df) * 0.6)))
    annotate = len(df) <= 15
    sns.heatmap(similarity, annot=annotate, fmt=".2f" if annotate else "", cmap="coolwarm",
                xticklabels=names, yticklabels=names, cbar_kws={"label": "Cosine similarity"})
    plt.title(f"Track similarity - {artist}")
    plt.xticks(rotation=45, ha="right", fontsize=8)
    plt.yticks(fontsize=8)
    plt.tight_layout()
    _finish(save_path, show)


def artist_similarity(df, save_path=None, show=False):
    """Cosine similarity between artists, over their mean metric vectors."""
    means = get_artist_means(df).set_index("Artist")
    if len(means) < 2:
        print("  skip artist similarity: needs >= 2 artists")
        return
    similarity = cosine_similarity(MinMaxScaler().fit_transform(means.values))
    plt.figure(figsize=(10, 8))
    sns.heatmap(similarity, annot=True, fmt=".2f", cmap="coolwarm",
                xticklabels=means.index, yticklabels=means.index)
    plt.title("Artist similarity (cosine over mean metrics)")
    plt.tight_layout()
    _finish(save_path, show)
    return pd.DataFrame(similarity, index=means.index, columns=means.index)


def artist_dendrogram(df, save_path=None, show=False):
    """Hierarchical clustering of artists over standardised mean metrics."""
    means = get_artist_means(df).set_index("Artist")
    if len(means) < 3:
        print("  skip dendrogram: needs >= 3 artists")
        return
    linked = linkage(StandardScaler().fit_transform(means.values), method="ward")
    plt.figure(figsize=(12, 6))
    dendrogram(linked, labels=list(means.index), orientation="top", distance_sort="descending")
    plt.title("Artist clustering")
    plt.xlabel("Artist")
    plt.ylabel("Ward distance (standardised)")
    plt.tight_layout()
    _finish(save_path, show)
