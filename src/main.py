from .phonetics import process_verse
from .engine import assign_rhyme_labels

#TODO: add function(s) to rm add lips and common sounds (yeah, skrr, ah)

def run_rhyme_mapper():
    # 1. Eminem - Lose Yourself (Cleaned for rhyme analysis)
    # Removing ad-libs like "yo" or "ope" to keep focus on terminal words
    lyrics = """
    His palms are sweaty, knees weak, arms are heavy
    There's vomit on his sweater already, mom's spaghetti
    He's nervous, but on the surface, he looks calm and ready
    To drop bombs, but he keeps on forgetting
    What he wrote down, the whole crowd goes so loud
    He opens his mouth, but the words won't come out
    He's chokin', how? Everybody's jokin' now
    The clock's run out, time's up, over, blaow
    Snap back to reality, there goes gravity
    There goes Rabbit, he choked, he's so mad
    But he won't give up that easy, no, he won't have it
    He knows his whole back's to these ropes, it don't matter
    He's dope, he knows that, but he's broke, he's so stagnant
    He knows when he goes back to this mobile home, that's when it's
    Back to the lab again, this old rhapsody
    Better go capture this moment and hope it don't pass him
    """

    print("=== RhymeMapper MVP - Eminem Test ===")
    
    # 2. Convert text to structured objects
    verse = process_verse(lyrics, artist="Eminem")
    
    # 3. Apply the rhyme labeling logic
    assign_rhyme_labels(verse)
    
    # 4. Output formatting
    print(f"Artist: {verse.metadata.get('artist', 'Unknown')}")
    print("-" * 50)
    
    for line in verse.lines:
        # Displaying the rhyme group and the line
        print(f"[{line.rhyme_label}: {line.words[-1].nuclei[-1].phoneme}] {line.text}")

if __name__ == "__main__":
    run_rhyme_mapper()
