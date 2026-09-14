"""Parsers for the caption formats YouTube serves.

Captions are the key to analysing an arbitrary song: one fetch yields the lyrics
*and* the timings, so the rhyme analysis and the karaoke playback come from the
same source with no alignment step and no ML model.

Two formats matter:

``json3``
    YouTube's own. Events carry ``segs``, each with a ``tOffsetMs`` relative to
    the event start, which gives genuine **word-level** timing -- exactly what
    the syllable highlighting wants.

``vtt``
    WebVTT, which everything speaks but which usually times whole lines.

Automatic captions are the hard case. They scroll: each event repeats the tail
of the previous one so the viewer sees a rolling two-line window, and reading
them naively produces every line two or three times. ``dedupe_rolling`` undoes
that.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from .timing import WordTiming, parse_vtt

# YouTube sprinkles these through automatic captions.
_NOISE = re.compile(r"^\[(music|applause|laughter|silence|inaudible|__)\]$", re.I)
_BRACKETED = re.compile(r"\[[^\]]*\]")


@dataclass
class CaptionCue:
    """One caption event: its text, and the timing of each word in it."""

    text: str
    words: list[WordTiming] = field(default_factory=list)


def _clean_segment(text: str) -> str:
    return text.replace("​", "").replace("\n", " ").strip()


def is_noise(text: str) -> bool:
    """True for caption cues that are stage directions rather than lyrics."""
    stripped = text.strip()
    return not stripped or bool(_NOISE.match(stripped))


def strip_brackets(text: str) -> str:
    """Remove [Music], [Applause] and friends from inside a line."""
    return _BRACKETED.sub(" ", text)


def parse_json3(payload) -> list[CaptionCue]:
    """Parse YouTube's json3 captions into cues.

    Word-level timing comes through whenever the events carry per-segment
    offsets, which automatic captions normally do.
    """
    data = json.loads(payload) if isinstance(payload, (str, bytes)) else payload
    events = data.get("events") or []

    cues: list[CaptionCue] = []

    for event in events:
        segments = event.get("segs")
        if not segments:
            continue

        start_ms = event.get("tStartMs")
        if start_ms is None:
            continue
        duration_ms = event.get("dDurationMs") or 0

        words: list[str] = []
        cue_words: list[WordTiming] = []
        for i, segment in enumerate(segments):
            text = _clean_segment(segment.get("utf8", ""))
            if not text:
                continue

            offset = segment.get("tOffsetMs")
            word_start = (start_ms + offset) / 1000 if offset is not None else start_ms / 1000

            # A segment's end is the next segment's start, or the event's end.
            next_offset = None
            for later in segments[i + 1:]:
                if later.get("tOffsetMs") is not None and _clean_segment(later.get("utf8", "")):
                    next_offset = later["tOffsetMs"]
                    break
            if next_offset is not None:
                word_end = (start_ms + next_offset) / 1000
            else:
                word_end = (start_ms + duration_ms) / 1000 if duration_ms else word_start + 0.4

            for token in text.split():
                if not is_noise(token):
                    words.append(token)
                    cue_words.append(WordTiming(token, word_start, max(word_end, word_start)))

        line = " ".join(words).strip()
        if line and not is_noise(line):
            cues.append(CaptionCue(line, cue_words))

    return cues


def parse_vtt_captions(payload: str) -> list[CaptionCue]:
    """Parse WebVTT captions into cues.

    WebVTT cues usually hold a whole line, so word times are spread evenly
    across the cue. That is coarse, but it keeps the karaoke highlight moving in
    roughly the right place, and json3 is preferred whenever it is available.
    """
    out: list[CaptionCue] = []

    for cue in parse_vtt(payload):
        text = strip_brackets(cue.word).strip()
        if not text or is_noise(text):
            continue

        words = text.split()
        if not words:
            continue
        step = max(cue.duration, 0.001) / len(words)
        timings = [WordTiming(word, cue.start + i * step, cue.start + (i + 1) * step)
                   for i, word in enumerate(words)]
        out.append(CaptionCue(text, timings))

    return out


def dedupe_rolling(cues: list[CaptionCue]) -> list[CaptionCue]:
    """Collapse the rolling repetition of automatic captions.

    Auto-captions scroll: each cue repeats the tail of the one before so the
    viewer keeps a two-line window on screen. Read literally that yields every
    lyric two or three times, which would wreck the analysis outright -- a
    repeated line rhymes perfectly with itself, so density and chain counts
    would both be inflated by a duplicate that was never sung twice.

    Each cue is reduced to what it adds to the running text, and its word
    timings are trimmed to match so the karaoke highlight stays aligned.
    """
    output: list[CaptionCue] = []
    previous_words: list[str] = []

    for cue in cues:
        words = cue.text.split()
        if not words:
            continue

        # Longest suffix of the previous cue that prefixes this one.
        overlap = 0
        for size in range(min(len(previous_words), len(words)), 0, -1):
            if [w.lower() for w in previous_words[-size:]] == [w.lower() for w in words[:size]]:
                overlap = size
                break

        remainder = words[overlap:]
        if remainder:
            # Drop the timings of the repeated prefix alongside its words, so
            # the first (correct) occurrence keeps its own time.
            output.append(CaptionCue(" ".join(remainder), cue.words[overlap:]))
        previous_words = words

    return output


def split_lines_by_pauses(timings: list[WordTiming], sensitivity: float = 1.9,
                          floor: float = 0.28, minimum_words: int = 2) -> list[str]:
    """Recover lyric lines from word timings by looking for pauses.

    Caption cues are timing windows, not lyric lines: a cue may hold a line and
    a half, or half a line. That matters more here than in a subtitle viewer,
    because line-final rhyme is most of what the analysis is about -- merge two
    lines and the rhyme at the join disappears.

    A rapper breathes between lines, so the gap between the last word of a line
    and the first of the next is reliably larger than the gaps inside it. The
    threshold is derived from the song's own median gap rather than fixed, since
    a double-time verse and a slow hook have completely different spacing.
    """
    if len(timings) < 2:
        return [" ".join(t.word for t in timings)] if timings else []

    gaps = [max(0.0, timings[i + 1].start - timings[i].end) for i in range(len(timings) - 1)]
    ordered = sorted(gaps)
    median = ordered[len(ordered) // 2]
    threshold = max(floor, median * sensitivity) if median > 0 else floor

    lines: list[str] = []
    current: list[str] = [timings[0].word]
    for i, gap in enumerate(gaps):
        # Don't break so early that a line is left as one stray word.
        if gap >= threshold and len(current) >= minimum_words:
            lines.append(" ".join(current))
            current = []
        current.append(timings[i + 1].word)
    if current:
        lines.append(" ".join(current))

    return lines


def cues_to_verse(cues: list[CaptionCue], dedupe: bool = True,
                  resplit_lines: bool = True) -> tuple[str, list[WordTiming]]:
    """Reduce cues to the lyrics block and word timings the analyser expects."""
    if dedupe:
        cues = dedupe_rolling(cues)

    lines: list[str] = []
    timings: list[WordTiming] = []
    for cue in cues:
        text = strip_brackets(cue.text).strip()
        if not text or is_noise(text):
            continue
        lines.append(text)
        timings.extend(cue.words)

    # Prefer the pause-derived line breaks when the captions carry real
    # word-level timing; cue boundaries are about screen space, not phrasing.
    if resplit_lines and len(timings) >= 4:
        by_pause = split_lines_by_pauses(timings)
        if by_pause:
            lines = by_pause

    return "\n".join(lines), timings
