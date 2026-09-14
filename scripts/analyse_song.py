"""Analyse any song from a link, in the terminal.

    python -m scripts.analyse_song "https://www.youtube.com/watch?v=..."
    python -m scripts.analyse_song --file lyrics.txt --artist "Nas"

Lyrics and word timings both come from the video's captions, so one fetch gives
the rhyme analysis and, in the viewer, the karaoke playback.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from rhymemap.cache import flush_all
from rhymemap.labeling import ENGINE_CHOICES, ENGINE_SIMILARITY, label_verse
from rhymemap.metrics import compute_metrics
from rhymemap.phonetics import process_verse
from rhymemap.sources import SourceError, from_text, load
from rhymemap.visual import VisualEngine

_PROVIDERS = {
    "captions": "captions",
    "lrclib-synced": "LRCLIB (community lyrics)",
    "lrclib-plain": "LRCLIB (community lyrics)",
    "pasted": "your own text",
}


def _provenance(song) -> str:
    """Where the words came from and how finely they can be synchronised."""
    name = _PROVIDERS.get(song.provider, song.provider or "unknown source")
    if song.provider == "captions":
        name = f"{song.caption_kind} captions" + (f" ({song.language})" if song.language else "")

    if song.sync == "word":
        timing = f"{len(song.timings)} word timings"
    elif song.sync == "line":
        timing = f"{len(song.lines)} line timings"
    else:
        timing = "no timing"
    return f"{name}, {timing}"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("url", nargs="?", help="YouTube link (any form), or a video id")
    parser.add_argument("--file", "-f", type=Path, help="analyse a local lyrics file instead")
    parser.add_argument("--artist", "-a", default=None, help="override the artist name")
    parser.add_argument("--engine", "-e", default=ENGINE_SIMILARITY, choices=ENGINE_CHOICES)
    parser.add_argument("--min-occurrences", type=int, default=2)
    parser.add_argument("--legend", action="store_true", help="list the rhyme groups")
    parser.add_argument("--lyrics-only", action="store_true", help="print the fetched lyrics and stop")
    args = parser.parse_args(argv)

    if not args.url and not args.file:
        parser.error("give a link or --file")

    try:
        if args.file:
            if not args.file.exists():
                print(f"error: no such file: {args.file}", file=sys.stderr)
                return 1
            song = from_text(args.file.read_text(encoding="utf-8"),
                             title=args.file.stem, artist=args.artist or "Unknown")
        else:
            print(f"fetching {args.url} ...", file=sys.stderr)
            song = load(args.url)
    except SourceError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.artist:
        song.artist = args.artist

    print(f"\n{song.artist} - {song.title}")
    if song.source == "youtube":
        print(f"  {song.line_count} lines, {_provenance(song)}")
        for attempt in song.attempts:
            if not attempt.ok:
                print(f"    tried {attempt}")
    print()

    if args.lyrics_only:
        print(song.lyrics)
        return 0

    verse = process_verse(song.lyrics, artist=song.artist)
    label_verse(verse, engine=args.engine, min_occurrences=args.min_occurrences)

    VisualEngine().display(verse, legend=args.legend)
    metrics = compute_metrics(verse)
    print(f"density {metrics['density']}%   multi {metrics['multi']}%   "
          f"diversity {metrics['diversity']}%   groups {metrics['signatures']}   "
          f"syllables {metrics['syllables']}")
    flush_all()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
