from g2p_en import G2p
from .models import Nucleus, Word, Line, Verse
import string
import re 


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
    """Transform a raw line into a Line object containing Words."""  
    # 1. Split line_text into words and create line object
    words = line_text.split()
    line_obj = Line(text = line_text,
                    line_id = line_id)

    # 2. For each word: 
    #    - Clean it
    #    - Create Word object
    #    - Get nuclei
    i = 0
    for current_word in words:
        i += 1
        cleaned = clean_word(current_word)
        word_obj = Word(text=cleaned, line_id=line_id, word_id=i-1)
        word_obj.is_last_word = i == len(words)
        word_obj.nuclei = extract_nuclei(cleaned, 
                                              line_id, 
                                              word_id = i - 1,
                                              is_last_word = (i == len(words)))

        line_obj.words.append(word_obj)
        
    return line_obj     # Return Line object

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



