from .models import Verse

COLORS = [
    "\033[41;30m", "\033[42;30m", "\033[43;30m",
    "\033[44;30m", "\033[45;30m", "\033[46;30m",
    "\033[48;5;202;30m", "\033[48;5;13;30m", "\033[48;5;51;30m",
    "\033[48;5;118;30m", "\033[48;5;214;30m", "\033[48;5;99;30m",
    "\033[48;5;196;30m", "\033[48;5;28;30m", "\033[48;5;20;30m",
    "\033[48;5;130;30m", "\033[48;5;200;30m", "\033[48;5;240;30m"
]
RESET = "\033[0m"
BOLD = "\033[1m"

class VisualEngine:
    def __init__(self):
        self.label_to_color = {}
        self.color_idx = 0

    def _get_color(self, label):
        if not label:
            return ""
        if label not in self.label_to_color:
            self.label_to_color[label] = COLORS[self.color_idx % len(COLORS)]
            self.color_idx += 1
        return self.label_to_color[label]

    def _format_word(self, word):
        if not word.syllables:
            return word.text
        parts = []
        for syl in word.syllables:
            if syl.rhyme_label:
                color = self._get_color(syl.rhyme_label)
                parts.append(color + syl.text + RESET)
            else:
                parts.append(syl.text)
        return ''.join(parts)

    def display(self, verse):
        print(f"\n{BOLD}Artist: {verse.metadata.get('artist', 'Unknown')}{RESET}")
        print("=" * 60)

        for line in verse.lines:
            colored_words = [self._format_word(w) for w in line.words]
            print(' '.join(colored_words))
        print("=" * 60 + "\n")