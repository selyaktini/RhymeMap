"""Core data structures for RhymeMapper.

A verse is decomposed as Verse -> Line -> Word -> Syllable.  The Syllable is the
unit the rhyme engine reasons about: everything downstream (signatures,
similarity scoring, chain detection, colouring) operates on syllables.

Dataclasses are used for the generated ``__init__``/``__repr__``/``__eq__``.
"""

from dataclasses import dataclass, field


@dataclass
class Syllable:
    """One syllable, split into its phonological constituents.

    A syllable is ``onset + nucleus + coda`` (e.g. "strength" -> onset
    ``["S", "T", "R"]``, nucleus ``"EH1"``, coda ``["NG", "K", "TH"]``).

    The onset is deliberately kept even though classical rhyme only depends on
    the rime (nucleus + coda): the similarity engine needs it to penalise
    identical-onset pairs, which are repetition rather than rhyme.
    """

    text: str                                  # Orthographic slice, for display
    nucleus: str                               # Vowel phoneme with stress, e.g. "AA1"
    coda: list[str]                            # Consonants after the nucleus
    onset: list[str] = field(default_factory=list)   # Consonants before the nucleus
    is_terminal: bool = False                  # Last syllable of the last word of a line
    rhyme_label: str = ""                      # Assigned rhyme group, e.g. "A", "AB"

    # Position in the verse. Filled in by the phonetic pass and used by the
    # chain detector to reconstruct the syllable stream.
    line_id: int = 0
    word_id: int = 0
    syl_index: int = 0                         # Index of this syllable within its word

    # Playback times in seconds, filled in by rhymemap.timing when an alignment is
    # supplied. None everywhere when there is no audio.
    start: float | None = None
    end: float | None = None


@dataclass
class Nucleus:
    """A vowel phoneme with its stress and position.

    Predates the Syllable type and is kept because it is part of the public
    surface exercised by the test-suite. It is now derived from the syllable
    split rather than computed with a second, separate g2p pass.
    """

    phoneme: str      # e.g. "OW1"
    stress: int       # 0 = unstressed, 1 = primary, 2 = secondary
    line_id: int
    word_id: int
    is_terminal: bool = False   # True if this is the last vowel of the line


@dataclass
class Word:
    """A cleaned word and its phonetic decomposition."""

    text: str
    syllables: list[Syllable] = field(default_factory=list)
    nuclei: list[Nucleus] = field(default_factory=list)
    line_id: int = 0
    word_id: int = 0
    is_last_word: bool = False

    # Playback times in seconds; see rhymemap.timing.
    start: float | None = None
    end: float | None = None


@dataclass
class Line:
    """One line of lyrics."""

    text: str
    words: list[Word] = field(default_factory=list)
    line_id: int = 0
    rhyme_label: str = ""


@dataclass
class Verse:
    """A group of lines, plus whatever metadata the caller supplies."""

    lines: list[Line] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)   # e.g. {"artist": "Eminem"}
    verse_id: int = 0

    def syllables(self) -> list[Syllable]:
        """Flatten the verse into a single ordered syllable stream."""
        return [syl for line in self.lines for word in line.words for syl in word.syllables]
