import re 
from collections import defaultdict 
from .models import Verse

CONSONANT_FAMILIES = {
    'M': 'NAS', 'N': 'NAS', 'NG': 'NAS',
    'S': 'SIB', 'Z': 'SIB', 'SH': 'SIB', 'ZH': 'SIB',
    'P': 'PLO', 'B': 'PLO', 'T': 'PLO', 'D': 'PLO', 'K': 'PLO', 'G': 'PLO',
    'F': 'FRI', 'V': 'FRI', 'TH': 'FRI', 'DH': 'FRI',
    'R': 'LIQ', 'L': 'LIQ',
    'W': 'GLI', 'Y': 'GLI',
    'HH': 'ASP',
}

class RhymeRegistry:
    def __init__(self):
        self.mapping = {}
        self.alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        self.next_letter_index = 0

    def get_label(self, signature: str) -> str:
        if signature not in self.mapping:
            self.mapping[signature] = self.alphabet[self.next_letter_index % len(self.alphabet)]
            self.next_letter_index += 1
        return self.mapping[signature]

def get_syllable_signature(syllable):
    """Génère une signature basée sur le son, le stress et le coda."""
    # syllable est un objet Syllable (text, nucleus, coda, is_terminal)
    nucleus_text = str(syllable.nucleus)
    if not nucleus_text:
        return ""

    # Extraction du son et du stress (ex: AE1 -> AE, 1)
    match = re.match(r"([A-Z]+)([0-2])", nucleus_text)
    if not match:
        vowel_sound = nucleus_text
        stress = "0"
    else:
        vowel_sound, stress = match.groups()

    # FILTRE : On ignore les rimes sur syllabes non-accentuées en milieu de vers
    if stress == "0" and not syllable.is_terminal:
        return ""

    coda = "".join(syllable.coda)
    return f"{vowel_sound}_{stress}_{coda}"

def assign_rhyme_labels(verse: Verse, min_occurrences=3, tail_window=2, only_terminal=False):
    counter = defaultdict(int)
    
    # 1. Premier passage : Compter les occurrences
    for line in verse.lines:
        all_line_syllables = []
        for word in line.words:
            all_line_syllables.extend(word.syllables)

        if tail_window is not None and tail_window > 0:
            syllables_to_check = all_line_syllables[-tail_window:]
        else:
            syllables_to_check = all_line_syllables

        for syl in syllables_to_check:
            sig = get_syllable_signature(syl)
            if sig:
                counter[sig] += 1

    frequent_sigs = {sig for sig, cnt in counter.items() if cnt >= min_occurrences}

    # 2. Second passage : Assigner les labels
    registry = RhymeRegistry()
    for line in verse.lines:
        all_line_syllables = []
        for word in line.words:
            all_line_syllables.extend(word.syllables)

        if tail_window is not None and tail_window > 0:
            syllables_to_check = all_line_syllables[-tail_window:]
        else:
            syllables_to_check = all_line_syllables

        for syl in syllables_to_check:
            sig = get_syllable_signature(syl)
            if sig in frequent_sigs:
                syl.rhyme_label = registry.get_label(sig)
