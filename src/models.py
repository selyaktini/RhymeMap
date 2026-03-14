from dataclasses import dataclass, field
# @dataclass automatically generates boilerplate methods for a class
# such as __init__, __repr__, and __eq__ 
# The field() function allows customization of individual attributes (for exemple default values, default_factory) 

@dataclass
class Nucleus:
    """Represents a stressed vowel (the core of the rhyme)."""
    phoneme: str      # ex: "OW1"
    stress: int       # 0, 1, or 2
    line_id: int      # Index of row (0, 1, ...)
    word_id: int      # Index of word in a row 
    is_terminal: bool = False # True if last vowel in a ligne

@dataclass
class Word:
    """Stores a word and its associated vowel nuclei."""
    text: str
    nuclei: list[Nucleus] = field(default_factory=list)
    line_id: int = 0
    word_id: int = 0       # To match Nucleus.word_id
    is_last_word: bool = False 

@dataclass
class Line:
    """Complete structure of a line for rhyme scheme detection."""
    text: str
    words: list[Word] = field(default_factory=list) # empty in init  
    line_id: int = 0
    rhyme_label: str = "" # ex: "A", "B"..

@dataclass
class Verse:
    """Container for a group of lines (Verse, Chorus, etc.)."""
    lines: list[Line] = field(default_factory=list)
    metadata: dict = field(default_factory=dict) # for exemple : {"artist": "Eminem", "type": "Verse"..}
    verse_id: int = 0


