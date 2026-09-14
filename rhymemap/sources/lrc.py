"""Parse LRC, the format synced-lyrics databases publish.

    [ar:Eminem]
    [00:12.34]Look, I was gonna go easy on you
    [00:15.10][01:42.00]And I just don't give a fuck

Timestamps are ``[mm:ss.xx]``. A line can carry several, meaning "sing this at
each of these points" -- the usual way a chorus is stored once and repeated.

The result is line-level, not word-level. A caption track gives a time per word;
LRC gives a time per line, and inventing word times inside it by dividing the
line up would be a fabrication that looks exactly like measured data. So
``LyricLine`` is kept distinct from ``WordTiming`` all the way to the viewer,
which highlights whole lines when that is all it truly knows.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# [mm:ss.xx], [mm:ss.xxx], [mm:ss:xx] (some writers use a colon) and [mm:ss].
_STAMP = re.compile(r"\[(?P<m>\d{1,3}):(?P<s>\d{1,2})(?:[.:](?P<frac>\d{1,3}))?\]")

# [ar:...], [length:03:21] and friends: a tag, not a cue.
_META = re.compile(r"^\[[a-zA-Z#]+:")

# Trailing gap a writer leaves after the last line when the outro is instrumental.
_DEFAULT_TAIL = 4.0


@dataclass
class LyricLine:
    """One line of lyrics and when it is sung."""

    text: str
    start: float
    end: float = 0.0

    @property
    def duration(self) -> float:
        return max(0.0, self.end - self.start)


def _seconds(match: re.Match) -> float:
    frac = match.group("frac") or "0"
    # "5" means 5 tenths, "05" 5 hundredths: pad right, then scale by width.
    divisor = 10 ** len(frac)
    return int(match.group("m")) * 60 + int(match.group("s")) + int(frac) / divisor


def parse_lrc(text: str, duration: float = 0.0) -> list[LyricLine]:
    """Turn an LRC document into timed lines, sorted and with end times filled.

    Blank cues are dropped, but their timestamps are kept as the end of the line
    before them -- that is exactly what a writer means by an empty line at the
    start of an instrumental break.
    """
    cues: list[tuple[float, str]] = []

    for raw in (text or "").splitlines():
        line = raw.strip()
        if not line:
            continue

        stamps = list(_STAMP.finditer(line))
        if not stamps:
            continue

        # Metadata tags parse as neither; a line is a cue only if its stamps
        # start at position 0 and run consecutively.
        if _META.match(line) and not stamps:
            continue

        last = stamps[-1]
        body = line[last.end():].strip()
        for stamp in stamps:
            cues.append((_seconds(stamp), body))

    if not cues:
        return []

    cues.sort(key=lambda pair: pair[0])

    lines: list[LyricLine] = []
    for index, (start, body) in enumerate(cues):
        if not body:
            # A silent cue closes the previous line rather than becoming one.
            if lines and lines[-1].end == 0.0:
                lines[-1].end = start
            continue

        end = 0.0
        for later_start, _ in cues[index + 1:]:
            if later_start > start:
                end = later_start
                break
        lines.append(LyricLine(text=body, start=start, end=end))

    for line in lines:
        if line.end <= line.start:
            line.end = duration if duration > line.start else line.start + _DEFAULT_TAIL

    return lines


def to_text(lines: list[LyricLine]) -> str:
    """The plain lyrics block the analyser reads."""
    return "\n".join(line.text for line in lines)


def is_synced(text: str) -> bool:
    """True when a document carries at least one real timestamped cue."""
    return bool(parse_lrc(text))
