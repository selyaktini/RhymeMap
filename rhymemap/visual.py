"""ANSI colour rendering of a labelled verse in the terminal."""

from __future__ import annotations

import os
import sys

from .models import Verse

# Background colours paired with black text, chosen to stay distinguishable.
COLORS = [
    "\033[41;30m", "\033[42;30m", "\033[43;30m",
    "\033[44;30m", "\033[45;30m", "\033[46;30m",
    "\033[48;5;202;30m", "\033[48;5;13;30m", "\033[48;5;51;30m",
    "\033[48;5;118;30m", "\033[48;5;214;30m", "\033[48;5;99;30m",
    "\033[48;5;196;30m", "\033[48;5;28;30m", "\033[48;5;20;30m",
    "\033[48;5;130;30m", "\033[48;5;200;30m", "\033[48;5;240;30m",
]
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"


def colors_enabled(stream=None) -> bool:
    """Respect NO_COLOR and disable escapes when output is piped to a file."""
    if os.environ.get("NO_COLOR"):
        return False
    stream = stream or sys.stdout
    return hasattr(stream, "isatty") and stream.isatty()


class VisualEngine:
    """Renders a verse, colouring each syllable by its rhyme label."""

    def __init__(self, use_color=None):
        self.label_to_color: dict[str, str] = {}
        self.color_index = 0
        self.use_color = colors_enabled() if use_color is None else use_color

    def _color_for(self, label: str) -> str:
        if not label or not self.use_color:
            return ""
        if label not in self.label_to_color:
            self.label_to_color[label] = COLORS[self.color_index % len(COLORS)]
            self.color_index += 1
        return self.label_to_color[label]

    def _format_word(self, word) -> str:
        if not word.syllables:
            return word.text
        parts = []
        for syl in word.syllables:
            color = self._color_for(syl.rhyme_label)
            parts.append(color + syl.text + RESET if color else syl.text)
        return "".join(parts)

    def display(self, verse: Verse, legend: bool = False) -> None:
        bold = BOLD if self.use_color else ""
        reset = RESET if self.use_color else ""
        artist = verse.metadata.get("artist", "Unknown")
        print(f"\n{bold}Artist: {artist}{reset}")
        print("=" * 70)
        for line in verse.lines:
            print(" ".join(self._format_word(w) for w in line.words))
        print("=" * 70)
        if legend:
            self.print_legend(verse)

    def print_legend(self, verse: Verse, limit: int = 20) -> None:
        """List each rhyme group: what it is called, how big, and examples."""
        counts: dict[str, int] = {}
        for syl in verse.syllables():
            if syl.rhyme_label:
                counts[syl.rhyme_label] = counts.get(syl.rhyme_label, 0) + 1
        if not counts:
            print("(no rhyme groups above the occurrence threshold)")
            return

        described = verse.metadata.get("groups") or {}
        ordered = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))

        print(f"Rhyme groups ({len(ordered)}):")
        for label, count in ordered[:limit]:
            name = described.get(label)
            color = self._color_for(label)
            swatch = f"{color}  {RESET}" if color else "  "

            size = (f"{name.length}-syl x{name.occurrences}"
                    if name and name.length > 1 else f"{count} syl")
            detail = ""
            if name and name.exemplars:
                detail = "  " + ", ".join(name.exemplars[:3])
            if name and name.rime:
                detail += f"   [{name.rime}]"
            print(f"  {swatch} {label:<26} {size:>12}{detail}")

        if len(ordered) > limit:
            print(f"  ... and {len(ordered) - limit} more")
        print()
