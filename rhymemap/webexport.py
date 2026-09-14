"""Export analysed verses to web/data.js for the browser viewer.

    python -m rhymemap.webexport [--input CSV] [--limit N] [--engine ENGINE]

The same serialisation is used by ``scripts/serve_web.py`` so that pasted lyrics
and pre-exported verses reach the page in one shape.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from rhymemap.analyzer import DEFAULT_DATASET, DatasetError, iter_verses
from rhymemap.cache import flush_all
from rhymemap.labeling import ENGINE_CHOICES, ENGINE_SIMILARITY, label_verse
from rhymemap.metrics import compute_metrics
from rhymemap.phonetics import process_verse

PROJECT_ROOT = Path(__file__).resolve().parent.parent
WEB_DIR = PROJECT_ROOT / "web"


def _group_summary(verse, chains=None) -> list[dict]:
    """Per-rhyme-group summary, strongest first.

    With the chain engine the strength is the chain's own
    ``length x similarity x occurrences``; otherwise it is the syllable count,
    so the list is ordered sensibly either way.

    Each group also carries what it is called and why: the exact rime, a few
    example words, and where in the verse it falls (for the position map).
    """
    counts: dict[str, int] = {}
    for syl in verse.syllables():
        if syl.rhyme_label:
            counts[syl.rhyme_label] = counts.get(syl.rhyme_label, 0) + 1

    by_label = {c.label: c for c in (chains or [])}
    described = verse.metadata.get("groups") or {}
    groups = []
    for label, count in counts.items():
        chain = by_label.get(label)
        name = described.get(label)
        groups.append({
            "label": label,
            "syllables": count,
            "length": chain.length if chain else 1,
            "occurrences": len(chain.occurrences) if chain else count,
            "similarity": round(chain.similarity, 3) if chain else None,
            "strength": round(chain.strength, 2) if chain else float(count),
            "rime": name.rime if name else "",
            "exemplars": name.exemplars if name else [],
            "positions": name.positions if name else [],
        })
    # Longest first, then strongest. Pure strength ordering buries the
    # multisyllabic chains beneath one-syllable groups that simply recur a lot,
    # and the long chains are the structure worth looking at.
    groups.sort(key=lambda g: (-g["length"], -g["strength"], g["label"]))
    return groups


def verse_to_dict(verse, artist: str, track: str, engine: str, chains=None, text: str = "",
                  audio: str = "", song=None) -> dict:
    """Serialise a labelled verse, keeping the phonetic detail for tooltips."""
    lines = []
    for line in verse.lines:
        words = []
        for word in line.words:
            words.append({
                "full_text": word.text,
                "syllables": [
                    {
                        "text": syl.text,
                        "label": syl.rhyme_label,
                        "nucleus": syl.nucleus,
                        "coda": " ".join(syl.coda),
                        "onset": " ".join(syl.onset),
                        # Present only when an alignment was supplied.
                        "start": syl.start,
                        "end": syl.end,
                    }
                    for syl in word.syllables
                ],
            })
        lines.append(words)

    return {
        "artist": artist,
        "track": track,
        "engine": engine,
        # Kept so the viewer can re-run another engine over the same verse.
        "text": text or "\n".join(line.text for line in verse.lines),
        "lines": lines,
        "metrics": compute_metrics(verse),
        "groups": _group_summary(verse, chains),
        # "en" or "dar", detected from the lyrics. The viewer says which one it
        # read the verse as, because that choice changes every phoneme under it
        # and a reader looking at Moroccan rhyme groups should be told the
        # engine knew it was Moroccan.
        "language": verse.metadata.get("language", "en"),
        # Empty unless --audio/--timings were given; the viewer hides its player.
        "audio": audio,
        "timed": any(syl.start is not None for syl in verse.syllables()),
        # Present for songs loaded from a link: lets the viewer embed the
        # original player and show where the lyrics came from.
        "source": {
            "kind": song.source,
            "video_id": song.video_id,
            "url": song.url,
            "thumbnail": song.thumbnail,
            "duration": song.duration,
            "captions": song.caption_kind,
            "language": song.language,
            # Which source in the chain supplied these lyrics, and how finely it
            # can be synchronised: "word", "line" or "none". The viewer shows
            # both, because a reader is entitled to know whether they are
            # looking at a human transcription or a machine's guess.
            "provider": getattr(song, "provider", ""),
            "sync": getattr(song, "sync", "none"),
            # [start, end] per lyric line, when the timing is line-level. Named
            # apart from "lines" above, which is the text.
            "line_times": [[line.start, line.end] for line in getattr(song, "lines", [])],
            "attempts": [
                {"provider": attempt.provider, "ok": attempt.ok, "detail": attempt.detail}
                for attempt in getattr(song, "attempts", [])
            ],
        } if song is not None else None,
    }


def label_and_name(verse, engine: str, min_occurrences: int, tail_window=None):
    """Label a verse and name its groups. Returns the chains, if any.

    Shared by ``analyse_text`` and ``analyse_song``: they carried near-identical
    copies of this, and the copies drifted -- a rename added to one silently
    left the other producing "F", "G", "J" instead of real names.
    """
    if engine == "chains":
        from rhymemap.chains import assign_chain_labels
        from rhymemap.naming import rename_groups

        chains = assign_chain_labels(verse, min_occurrences=min_occurrences)
        verse.metadata["groups"] = rename_groups(verse, chains)
        return chains

    label_verse(verse, engine=engine, min_occurrences=min_occurrences, tail_window=tail_window)
    return None


def analyse_text(lyrics: str, artist: str, track: str, engine: str = ENGINE_SIMILARITY,
                 min_occurrences: int = 2, tail_window=None, timings=None, audio: str = "") -> dict:
    """Run the pipeline over raw lyrics and return the viewer payload."""
    verse = process_verse(lyrics, artist=artist)
    chains = label_and_name(verse, engine, min_occurrences, tail_window)

    if timings:
        from rhymemap.timing import attach_timings, timing_coverage

        matched = attach_timings(verse, timings)
        print(f"  timings: matched {matched} words ({timing_coverage(verse):.0%} of the verse)")

    return verse_to_dict(verse, artist, track, engine, chains, text=lyrics, audio=audio)


def analyse_song(song, engine: str = ENGINE_SIMILARITY, min_occurrences: int = 2,
                 tail_window=None, on_progress=None) -> dict:
    """Analyse a Song from rhymemap.sources, keeping its provenance in the payload.

    ``on_progress(fraction, stage)`` is called as the work proceeds. The fraction
    is measured, not timed: phoneme lookup and syllabification are the expensive
    part and happen one line at a time, so lines completed is a real measure of
    how much of the analysis is done.
    """
    def report(fraction, stage):
        if on_progress is not None:
            on_progress(fraction, stage)

    # Lines carry the analysis; labelling and serialising are the short tail.
    verse = process_verse(
        song.lyrics, artist=song.artist,
        on_line=lambda done, total: report(done / max(total, 1) * 0.85, "sounding out the words"),
    )
    report(0.88, "grouping the rhymes")
    chains = label_and_name(verse, engine, min_occurrences, tail_window)
    report(0.97, "naming the groups")

    if song.timings:
        from rhymemap.timing import attach_timings

        attach_timings(verse, song.timings)

    return verse_to_dict(verse, song.artist, song.title, engine, chains,
                         text=song.lyrics, song=song)


def build(csv_path: str, limit, min_occurrences: int, tail_window, engine: str) -> list[dict]:
    verses = []
    for track, artist, lyrics in iter_verses(csv_path):
        if limit is not None and len(verses) >= limit:
            break
        try:
            verses.append(analyse_text(lyrics, artist, track, engine, min_occurrences, tail_window))
        except Exception as exc:
            print(f"  !! {track}: {type(exc).__name__}: {exc}")
    return verses


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", "-i", default=DEFAULT_DATASET, help=f"lyrics CSV (default: {DEFAULT_DATASET})")
    parser.add_argument("--output", "-o", default=str(WEB_DIR / "data.js"), help="output JS file")
    parser.add_argument("--limit", "-n", type=int, default=None, help="export at most N verses")
    parser.add_argument("--min-occurrences", type=int, default=2, help="minimum signature count to label")
    parser.add_argument("--tail-window", type=int, default=None, help="only label the last N syllables per line")
    parser.add_argument("--engine", "-e", default=ENGINE_SIMILARITY, choices=ENGINE_CHOICES, help="rhyme engine")
    parser.add_argument("--demo", action="store_true", help="also include dataset/demo_rap_god.txt")
    parser.add_argument("--timings", type=Path, default=None,
                        help="word-timing file (JSON, VTT/SRT or Audacity labels) for karaoke playback")
    parser.add_argument("--audio", default="", help="audio filename inside web/ to play alongside")
    args = parser.parse_args(argv)

    timings = None
    if args.timings:
        from rhymemap.timing import TimingError, load_timings

        try:
            timings = load_timings(args.timings)
            print(f"loaded {len(timings)} word timings from {args.timings}")
        except TimingError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1

    try:
        verses = build(args.input, args.limit, args.min_occurrences, args.tail_window, args.engine)
    except DatasetError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    demo = PROJECT_ROOT / "dataset" / "demo_rap_god.txt"
    if args.demo and demo.exists():
        verses.insert(0, analyse_text(demo.read_text(encoding="utf-8"), "Eminem",
                                      "Rap God (full verse)", args.engine, args.min_occurrences,
                                      timings=timings, audio=args.audio))

    if not verses:
        print(f"error: nothing to export from {args.input}", file=sys.stderr)
        return 1

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output, "w", encoding="utf-8") as handle:
        handle.write("const rhymeData = ")
        json.dump(verses, handle, ensure_ascii=False, indent=2)
        handle.write(";\n")
    flush_all()

    print(f"exported {len(verses)} verses to {output} ({output.stat().st_size / 1024:.0f} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
