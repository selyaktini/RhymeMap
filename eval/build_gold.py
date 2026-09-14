"""Build eval/gold.json from the annotations recorded here.

The annotations below are hand-made line-final rhyme groupings, kept in source
so each one sits next to the reasoning for it. Running this script pairs them
with the exact line text from the corpus and writes a self-contained gold file.

Re-run with:  python -m eval.build_gold
"""

from __future__ import annotations

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT = PROJECT_ROOT / "eval" / "gold.json"

PROTOCOL = (
    "Two lines are placed in the same group when their final stressed vowel and "
    "everything after it match, or differ only by a slant-rhyme margin (same "
    "vowel, coda differing by at most one voicing or place feature). A line that "
    "rhymes with no other line in its verse forms a singleton group. Only "
    "line-final rhyme is annotated: it is the part of the judgement that is "
    "reproducible between annotators. Internal and multisyllabic rhyme is "
    "deliberately out of scope here, because agreement on it is much weaker."
)

PROVENANCE = (
    "Annotated by Claude (Opus 5) following the protocol above, not by a human "
    "expert, and not verified against a second annotator. Treat it as a "
    "reproducible reference rather than ground truth: the ablation it supports "
    "compares engines against one consistent standard, which is what the "
    "comparison needs, but absolute F1 values carry the annotator's bias. "
    "Independent re-annotation is the single highest-value improvement to this "
    "evaluation."
)

# --- Verses drawn from dataset/artists_sample.csv ---------------------------
# Each entry: track name in the CSV -> list of line-index groups.
CORPUS_ANNOTATIONS = {
    "Lose Yourself (Verse 1)": {
        "groups": [[0, 1, 2], [3], [4, 5, 6, 7], [8, 14], [9, 10, 11, 12], [13], [15]],
        "notes": "heavy/spaghetti/ready share the stressed rime; forgettin' adds a syllable "
                 "and is kept apart. loud/out/now/blaow all on /aw/. choked/no/ropes/broke "
                 "on /ow/. gravity/rhapsody pair on /ae..i/ across six lines.",
    },
    "DNA. (Verse 1)": {
        "groups": [[0, 1, 2, 3, 14, 15], [4, 5], [6, 7], [8, 9], [10, 11, 12, 13]],
        "notes": "The DNA refrain bookends the verse. immaculate/accurate, head/dead, "
                 "seven/represent on /e/+nasal, and the four -ation lines.",
    },
    "Middle Child (Verse 1)": {
        "groups": [[0], [1, 3], [2], [4, 5, 6, 7], [8, 9, 10, 11], [12, 13, 14], [15]],
        "notes": "once/lunch on /uhn/+sibilant. Kodak/back/mad/rack on /ae/+stop. "
                 "clips/list/hit/lit on /ih/+coda. day/stayed/afraid on /ey/.",
    },
    "Tuscan Leather (Verse 1)": {
        "groups": [[0, 1, 2, 3], [4, 5, 6, 7], [8, 9], [10, 11], [12, 13], [14, 15]],
        "notes": "established/cabin/palace/planet is a slant chain on stressed /ae/ plus an "
                 "unstressed syllable. Then the -ly quatrain and three couplets.",
    },
    "Stan (Verse 1)": {
        "groups": [[0, 3], [1, 2, 4], [5, 6], [7]],
        "notes": "bottom/got 'em/jot 'em is the core. callin'/somethin' pair on unstressed "
                 "/ihn/. daughter/father on /aa-dh-er/ vs /ao-t-er/, within the slant margin.",
    },
    "Rap God (Excerpt)": {
        "groups": [[0, 1, 2, 3, 4]],
        "notes": "God/nod/NASCAR/God/Asgard: every line lands on stressed /aa/ + coda.",
    },
    "HUMBLE. (Verse 1)": {
        "groups": [[0, 1], [2], [3, 5, 6], [4]],
        "notes": "for me/for me. Photoshop/marks/socks on /aa/ + stop or cluster. "
                 "Pryor is left alone: /ay-er/ does not reach the others.",
    },
    "Alright (Verse 1)": {
        "groups": [[0], [1, 5], [2, 3], [4]],
        "notes": "I/alright on /ay/; yah/yah verbatim.",
    },
    "No Role Modelz (Verse 1)": {
        "groups": [[0, 3, 4], [1, 2]],
        "notes": "Phil/Ville/ill on /ihl/, knew/you on /uw/.",
    },
    "Wet Dreamz (Verse 1)": {
        "groups": [[0, 1], [2], [3]],
        "notes": "well/myself on /ehl/. curls and by rhyme with nothing in the excerpt.",
    },
    "God's Plan (Verse 1)": {
        "groups": [[0], [1], [2, 3, 4]],
        "notes": "with me/for me/with me. Line 1 ends on the ad-lib 'yuh', so it is a "
                 "singleton under a strictly line-final rule even though the ear hears 'me'.",
    },
    "In My Feelings (Verse 1)": {
        "groups": [[0, 1], [2]],
        "notes": "ridin'/beside me on /ayd/.",
    },
}

# --- A dense segment of the demo verse, for multisyllabic material ----------
DEMO_SEGMENTS = [
    {
        "id": "rap_god_supersonic",
        "track": "Rap God (supersonic segment)",
        "artist": "Eminem",
        "source": "dataset/demo_rap_god.txt",
        "line_range": [55, 71],
        "groups": [[0], [1, 2], [3], [4, 5], [6, 7, 8, 9, 10], [11, 12, 13], [14, 15]],
        "notes": "human/superhuman. levitatin'/celebratin' on /eytihn/. "
                 "music/confuse it/fuse it/lose it/use all land on /uwz/. "
                 "you/to/too on bare /uw/. brung me/hungry on /uhng/+/iy/.",
    },
]


def main() -> int:
    from rhymemap.analyzer import iter_verses

    by_track = {track: (artist, lyrics) for track, artist, lyrics in iter_verses()}
    verses = []

    for track, annotation in CORPUS_ANNOTATIONS.items():
        if track not in by_track:
            print(f"warning: {track!r} is not in the corpus; skipping")
            continue
        artist, lyrics = by_track[track]
        lines = [ln.strip() for ln in lyrics.split("\n") if ln.strip()]
        verses.append({
            "id": track.lower().replace(" ", "_").replace("(", "").replace(")", "").replace(".", ""),
            "track": track,
            "artist": artist,
            "source": "dataset/artists_sample.csv",
            "lines": lines,
            "end_rhyme_groups": annotation["groups"],
            "notes": annotation["notes"],
        })

    demo_lines = (PROJECT_ROOT / "dataset" / "demo_rap_god.txt").read_text(encoding="utf-8").split("\n")
    for segment in DEMO_SEGMENTS:
        start, end = segment["line_range"]
        lines = [ln.strip() for ln in demo_lines[start:end] if ln.strip()]
        verses.append({
            "id": segment["id"],
            "track": segment["track"],
            "artist": segment["artist"],
            "source": segment["source"],
            "lines": lines,
            "end_rhyme_groups": segment["groups"],
            "notes": segment["notes"],
        })

    problems = validate(verses)
    if problems:
        for problem in problems:
            print(f"error: {problem}")
        return 1

    payload = {
        "format_version": 1,
        "description": "Line-final rhyme groupings for RhymeMapper evaluation.",
        "protocol": PROTOCOL,
        "provenance": PROVENANCE,
        "verse_count": len(verses),
        "line_count": sum(len(v["lines"]) for v in verses),
        "verses": verses,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    artists = {v["artist"] for v in verses}
    print(f"wrote {OUTPUT}")
    print(f"  {len(verses)} verses, {payload['line_count']} lines, {len(artists)} artists")
    return 0


def validate(verses) -> list[str]:
    """Every line index must appear exactly once across a verse's groups."""
    problems = []
    for verse in verses:
        count = len(verse["lines"])
        flat = [i for group in verse["end_rhyme_groups"] for i in group]
        if sorted(flat) != list(range(count)):
            missing = sorted(set(range(count)) - set(flat))
            extra = sorted(set(flat) - set(range(count)))
            duplicated = sorted({i for i in flat if flat.count(i) > 1})
            problems.append(
                f"{verse['id']}: groups cover {sorted(set(flat))} for {count} lines"
                f"{f'; missing {missing}' if missing else ''}"
                f"{f'; out of range {extra}' if extra else ''}"
                f"{f'; duplicated {duplicated}' if duplicated else ''}"
            )
    return problems


if __name__ == "__main__":
    raise SystemExit(main())
