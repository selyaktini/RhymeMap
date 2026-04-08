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
        self.mapping = {}  # Store {"AY1": "A", "OW1": "B"}
        self.alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        self.next_letter_index = 0

    def get_label(self, signature: str) -> str:
        if signature not in self.mapping:
            # Assign a new letter if phoneme unknown
            self.mapping[signature] = self.alphabet[self.next_letter_index % len(self.alphabet)]
            self.next_letter_index += 1
        return self.mapping[signature]

def get_syllable_signature(syllable):
    """Signature if rhyme : nucleus without stress + coda with families."""
    nucleus = str(syllable.nucleus)
    if not nucleus:
        return ""
    nucleus_clean = re.sub(r'\d', '', nucleus)
    coda_parts = []
    for c in syllable.coda:
        c_str = str(c)
        c_clean = re.sub(r'\d', '', c_str)
        family = CONSONANT_FAMILIES.get(c_clean, c_clean)
        coda_parts.append(family)
    coda_str = '-'.join(coda_parts) if coda_parts else ''
    return f"{nucleus_clean}-{coda_str}" if coda_str else nucleus_clean

def assign_rhyme_labels(verse: Verse, min_occurrences=3, only_terminal=False):
    """
    Colore les syllabes dont la signature apparaît au moins min_occurrences fois.
    only_terminal=True ne considère que la dernière syllabe de chaque mot.
    color syllables with min_occurrences , only_terminal=True see only last syllable of each word
    """
    counter = defaultdict(int)

    # 1. Count signatures 
    for line in verse.lines:
        for word in line.words:
            if only_terminal:
                syllables_to_check = [word.syllables[-1]] if word.syllables else []
            else:
                syllables_to_check = word.syllables
            for syl in syllables_to_check:
                sig = get_syllable_signature(syl)
                if sig:
                    counter[sig] += 1

    # 2. keep only frequent_sigs 
    frequent_sigs = {sig for sig, cnt in counter.items() if cnt >= min_occurrences}

    # 3. Assign labels
    registry = RhymeRegistry()
    for line in verse.lines:
        for word in line.words:
            if only_terminal:
                syllables_to_check = [word.syllables[-1]] if word.syllables else []
            else:
                syllables_to_check = word.syllables
            for syl in syllables_to_check:
                sig = get_syllable_signature(syl)
                if sig and sig in frequent_sigs:
                    syl.rhyme_label = registry.get_label(sig)

