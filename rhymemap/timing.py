"""Word-level timings, so the analysis can be played back against audio.

``notes.md`` has wanted this since March: attach a time to each word and light
the rhymes up in sync with the track.

Alignment itself is left to an external tool. This module only reads the formats
those tools emit and attaches the result to a verse, which keeps the heavy
dependencies (WhisperX pulls in torch; aeneas needs espeak and ffmpeg) out of the
project entirely. Nothing here imports them, and a verse with no timings behaves
exactly as before.

Supported inputs:

* **JSON** -- ``[{"word": "palms", "start": 0.51, "end": 0.78}, ...]``, or a
  ``{"words": [...]}`` wrapper, which is what WhisperX writes.
* **WebVTT / SRT** -- one cue per word.
* **Audacity labels** -- ``start<TAB>end<TAB>word``, which any DAW can export.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from .phonetics import clean_word


@dataclass
class WordTiming:
    word: str
    start: float
    end: float

    @property
    def duration(self) -> float:
        return max(0.0, self.end - self.start)


class TimingError(ValueError):
    """Raised for a timing file that cannot be parsed."""


_TIMESTAMP = re.compile(r"(?P<h>\d+):(?P<m>\d{2}):(?P<s>\d{2})[.,](?P<ms>\d{1,3})")


def _to_seconds(text: str) -> float:
    match = _TIMESTAMP.search(text)
    if not match:
        raise TimingError(f"unrecognised timestamp: {text!r}")
    parts = match.groupdict()
    return (int(parts["h"]) * 3600 + int(parts["m"]) * 60 + int(parts["s"])
            + int(parts["ms"].ljust(3, "0")) / 1000)


def parse_json(text: str) -> list[WordTiming]:
    data = json.loads(text)
    if isinstance(data, dict):
        data = data.get("words") or data.get("segments") or []
    timings = []
    for entry in data:
        if not isinstance(entry, dict):
            continue
        word = entry.get("word") or entry.get("text") or entry.get("label")
        start, end = entry.get("start"), entry.get("end")
        if word is None or start is None or end is None:
            continue
        timings.append(WordTiming(str(word).strip(), float(start), float(end)))
    return timings


def parse_vtt(text: str) -> list[WordTiming]:
    timings = []
    lines = [line.rstrip("\n") for line in text.splitlines()]
    for i, line in enumerate(lines):
        if "-->" not in line:
            continue
        left, _, right = line.partition("-->")
        try:
            start, end = _to_seconds(left), _to_seconds(right)
        except TimingError:
            continue
        for candidate in lines[i + 1:]:
            if candidate.strip():
                timings.append(WordTiming(candidate.strip(), start, end))
                break
    return timings


def parse_labels(text: str) -> list[WordTiming]:
    timings = []
    for line in text.splitlines():
        parts = line.split("\t")
        if len(parts) < 3:
            parts = line.split()
            if len(parts) < 3:
                continue
            parts = [parts[0], parts[1], " ".join(parts[2:])]
        try:
            timings.append(WordTiming(parts[2].strip(), float(parts[0]), float(parts[1])))
        except ValueError:
            continue
    return timings


def load_timings(path) -> list[WordTiming]:
    """Read a timing file, choosing the parser by extension then by content."""
    path = Path(path)
    if not path.exists():
        raise TimingError(f"timing file not found: {path}")
    text = path.read_text(encoding="utf-8")

    suffix = path.suffix.lower()
    if suffix == ".json":
        timings = parse_json(text)
    elif suffix in {".vtt", ".srt"}:
        timings = parse_vtt(text)
    elif suffix in {".txt", ".tsv", ".labels"}:
        timings = parse_labels(text)
    else:
        timings = []
        for parser in (parse_json, parse_vtt, parse_labels):
            try:
                timings = parser(text)
            except Exception:
                continue
            if timings:
                break

    if not timings:
        raise TimingError(f"no usable word timings found in {path}")
    return timings


def attach_timings(verse, timings: list[WordTiming], tolerance: int = 6) -> int:
    """Attach timings to a verse's words in order; returns how many matched.

    Alignment is sequential with a small lookahead. Timing files and lyrics
    disagree constantly -- ad-libs, censored words, "y'all" against "yall" -- so
    a word that does not match is skipped rather than dragging the rest out of
    step. Syllable times are interpolated across each word by syllable count.
    """
    words = [word for line in verse.lines for word in line.words]
    matched = 0
    cursor = 0

    for word in words:
        target = clean_word(word.text)
        if not target:
            continue

        found = None
        for offset in range(max(0, min(tolerance, len(timings) - cursor))):
            if clean_word(timings[cursor + offset].word) == target:
                found = cursor + offset
                break
        if found is None:
            continue

        timing = timings[found]
        cursor = found + 1
        matched += 1
        word.start, word.end = timing.start, timing.end

        count = len(word.syllables)
        if count:
            step = timing.duration / count
            for i, syl in enumerate(word.syllables):
                syl.start = timing.start + i * step
                syl.end = timing.start + (i + 1) * step

    return matched


def timing_coverage(verse) -> float:
    """Fraction of the verse's words that carry a timing."""
    words = [word for line in verse.lines for word in line.words]
    if not words:
        return 0.0
    return sum(1 for word in words if word.start is not None) / len(words)
