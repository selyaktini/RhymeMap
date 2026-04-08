from g2p_en import G2p
from .models import Syllable, Nucleus, Word, Line, Verse
import string
import re
from syllabify import syllabify


# Initialize G2p once at module level to avoid reloading it constantly
g2p = G2p()

def clean_word(text):
    """Remove punctuation and lowercase the word."""
    return re.sub(r'[^\w\s]', '', text).lower().strip()

def extract_nuclei(word_text, line_id, word_id, is_last_word):
    """Transform a word into a list of Nucleus objects."""
    # 1. Get phonemes from g2p
    phonemes = g2p(word_text)

    # 2. Filter vowels 
    vowels = [v for v in phonemes if v[-1].isdigit()]

    # 3. Create list of vowels for each word
    nuclei = [Nucleus(phoneme = v, 
                    stress = int(v[-1]),
                    line_id = line_id,
                    word_id = word_id,
                    is_terminal = False
                    ) for v in vowels]

    # 4. Verify if it is the last vowel in a ligne 
    if (is_last_word and nuclei):
        nuclei[-1].is_terminal = True 
    
    return nuclei      # Return list[Nucleus]

def process_line(line_text, line_id):
    words = line_text.split()
    line_obj = Line(text=line_text, line_id=line_id)

    for i, raw_word in enumerate(words):
        cleaned = clean_word(raw_word)
        nuclei = extract_nuclei(cleaned, line_id, i, i == len(words)-1)
        syllables = extract_syllables(cleaned, line_id, i, i == len(words)-1)

        word_obj = Word(
            text=cleaned,
            syllables=syllables,
            nuclei=nuclei,
            line_id=line_id,
            word_id=i,
            is_last_word=(i == len(words)-1)
        )
        line_obj.words.append(word_obj)

    return line_obj


def process_verse(raw_text, artist="Unknown"):
    """Entry point: Transforms raw lyrics into a Verse object."""
    # 2. Loop through lines to call process_line()
    # 3. Assemble and return Verse object

    # 1. Split text into lines
    raw_text = raw_text.strip() # pour enlever les espaces inutiles
    lines = raw_text.split('\n')

    verse_obj = Verse(metadata = {"artist" : artist}) #TODO: Gestion of verese_id and other metadata
    line_id = 0
    for line_text in lines:
        line_text = line_text.strip()
        if line_text == "":
            continue
        verse_obj.lines.append(process_line(line_text, line_id))
        line_id += 1

    return verse_obj      # Return Verse object


# ------------------------------------ end of old implementation --------- 

# Divide a word into syllables (very approximate)
def split_word_text(word_text, num_syllables):
    if num_syllables <= 1:  # If just one syllable return the singleton
        return [word_text]
    length = len(word_text)  # else divide into equal (+-1) syllables 
    step = length / num_syllables
    parts = []
    for i in range(num_syllables):
        start = int(i * step)
        end = int((i + 1) * step) if i < num_syllables - 1 else length
        parts.append(word_text[start:end])
    return parts



# This function is to call in case syllabify return an exception
# It divide phonemes of a word into syllables just with vowels
# each vowel is the start of a syllable and next consonants are the next elements(approximatif approach)
# Even if its very approximate but functional for most words 
# returns Syllable object 
def heuristic_syllables(phonemes, word_text):
    syll_phon = []
    current = []
    for ph in phonemes:
        current.append(ph)
        if any(c.isdigit() for c in ph):
            syll_phon.append(current)
            current = []
    if current:
        if syll_phon:
            syll_phon[-1].extend(current)
        else:
            syll_phon.append(current)

    num_syll = len(syll_phon)
    syll_texts = split_word_text(word_text, num_syll) if num_syll else [word_text]
    syllables = []
    for i, syl_ph in enumerate(syll_phon):
        nucleus = ''
        coda = []
        for j, p in enumerate(syl_ph):
            if p[-1].isdigit():
                nucleus = p
                coda = [str(x) for x in syl_ph[j+1:]]
                break
        if not nucleus:
            nucleus = ' '.join(syl_ph)
        syllables.append(Syllable(
            text=syll_texts[i] if i < len(syll_texts) else word_text,
            nucleus=nucleus,
            coda=coda,
            is_terminal=False
        ))
    return syllables


# The main function to extract syllables (use *split_word_text()* and *heuristic_syllables()*)
def extract_syllables(word_text, line_id, word_id, is_last_word):
    try:
        result = syllabify(word_text)    # If word exist
    except Exception:                    # Else we use heuristic_syllables function
        phonemes = g2p(word_text)
        return heuristic_syllables(phonemes, word_text)

    if hasattr(result, 'words') and result.words:    # If result is a Sentence (list of words , possible return value for syllabify lib)
        word_obj = result.words[0]                   # Take the first words 
    elif hasattr(result, 'syllables'):
        word_obj = result                            # else take result if alreadt word (syllables attribute)
    else:
        return []                                    # If neither, return empty list 

    num_syll = len(word_obj.syllables)               
    syll_texts = split_word_text(word_text, num_syll) if num_syll else [word_text]

    syllables = []
    for i, syl in enumerate(word_obj.syllables):
        nucleus = str(syl.nucleus) if hasattr(syl.nucleus, '__str__') else syl.nucleus
        coda = [str(c) for c in syl.coda] if syl.coda else []
        is_terminal = (is_last_word and i == num_syll - 1)
        text_part = syll_texts[i] if i < len(syll_texts) else word_text
        syllables.append(Syllable(
            text=text_part,
            nucleus=nucleus,
            coda=coda,
            is_terminal=is_terminal
        ))
    return syllables




# Process verse stay the same 
# process_line slightly changed 









































