from .models import Verse

class RhymeRegistry:
    def __init__(self):
        self.mapping = {}  # Store {"AY1": "A", "OW1": "B"}
        self.alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        self.next_letter_index = 0

    def get_label(self, phoneme: str) -> str:
        if phoneme not in self.mapping:
            # Assign a new letter if phoneme unknown
            self.mapping[phoneme] = self.alphabet[self.next_letter_index]
            self.next_letter_index += 1
        return self.mapping[phoneme]

def assign_rhyme_labels(verse: Verse):
    registry = RhymeRegistry()

    for line in verse.lines:
        # search phoneme in the end of the line 
        terminal_phoneme = None
        for word in line.words:
            if word.is_last_word:
                for nucleus in word.nuclei:
                    if nucleus.is_terminal:
                        terminal_phoneme = nucleus.phoneme
                        break
        
        # assigne a label based on phoneme 
        if terminal_phoneme:
            line.rhyme_label = registry.get_label(terminal_phoneme)
        else:
            line.rhyme_label = "?" # Just a security in case the line doesn't have a vowel 

