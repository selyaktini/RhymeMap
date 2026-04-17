from .phonetics import process_verse
from .engine import assign_rhyme_labels
from .visual import VisualEngine
from .analyzer import analyze_dataset  # À créer dans src/analyzer.py

def run_rhyme_mapper():
    """Exemple avec le couplet de 'Rap God'."""
    lyrics = """
    Everybody loves to root for a nuisance, hit the Earth like an asteroid
    Did nothin' but shoot for the Moon since (pew)
    MCs get taken to school with this music 'cause I use it as a vehicle to, "Bus the rhyme"
    Now I lead a new school full of students
    Me? I'm a product of Rakim, Lakim Shabazz, 2Pac, N.W.A, Cube, hey Doc, Ren
    Yella, Eazy, thank you, they got Slim
    Inspired enough to one day grow up, blow up and be in a position
    To meet Run–D.M.C., and induct them into the mother-
    Rock and Roll Hall of Fame even though I'll walk in the church and burst in a ball of flames
    Only Hall of Fame I'll be inducted in is the alcohol of fame on the wall of (shame)
    You - think it's all a game 'til I walk a flock of flames
    Off a plank and, tell me what in the - are you thinkin'?
    Little g-lookin' boy, so g- I can barely say it with a straight face, lookin' boy (haha)
    You're witnessin' a mass-occur like you're watchin' a church gatherin' take place, lookin' boy
    "Oy vey, that boy's g-", that's all they say, lookin' boy
    You get a thumbs up, pat on the back and a, "Way to go" from your label every day, lookin' boy
    Hey, lookin' boy, what you say, lookin' boy? I get a, "Hell yeah" from Dre, lookin' boy
    I'ma work for everythin' I have, never asked nobody for s-, get outta my face, lookin' boy
    Basically, boy, you're never gonna be capable of keepin' up with the same pace, lookin' boy, 'cause
    I'm beginnin' to feel like a Rap God, Rap God
    All my people from the front to the back nod, back nod
    The way I'm racin' around the track, call me NASCAR, NASCAR
    Dale Earnhardt of the trailer park, the White Trash God
    Kneel before General Zod, this planet's Krypton, no, Asgard, Asgard
    So you'll be Thor, and I'll be Odin, you rodent, I'm omnipotent
    Let off, then I'm reloadin', immediately with these bombs I'm totin'
    And I should not be woken
    I'm the walkin' dead, but I'm just a talkin' head, a zombie floatin', but I got your mom deep-
    I'm out my Ramen Noodle, we have nothin' in common, poodle
    I'm a Doberman, pinch yourself in the arm and pay homage, pupil
    It's me, my honesty's brutal
    But it's honestly futile if I don't utilize what I do though
    For good, at least once in a while
    So I wanna make sure somewhere in this chicken scratch I scribble and doodle enough rhymes
    To maybe try to help get some people through tough times
    But I gotta keep a few punchlines just in case 'cause even you unsigned
    Rappers are hungry lookin' at me like it's lunchtime
    I know there was a time where once I was king of the underground
    But I still rap like I'm on my Pharoahe Monch grind
    So I crunch rhymes, but sometimes when you combine
    Appeal with the skin color of mine
    You get too big and here they come tryin' to censor you like that one line
    I said on, "I'm Back" from The Mathers LP 1 when I tried to say I'll take seven k- from Columbine
    Put 'em all in a line, add an AK-47, a revolver and a .9
    See if I get away with it now that I ain't as big as I was, but I'm
    Morphin' into an immortal, comin' through the portal
    You're stuck in a time warp from 2004 though
    And I don't know what the f- that you rhyme for
    You're pointless as Rapunzel with -ckin' cornrows
    You write normal? F- bein' normal
    And I just bought a new raygun from the future
    Just to come and shoot ya, like when Fabolous made Ray J mad
    'Cause Fab said he looked like a - at Mayweather's pad singin' to a man while he played piano
    Man, oh man, that was a 24-7 special on the cable channel
    So Ray J went straight to the radio station, the very next day, "Hey Fab, I'ma kill you"
    Lyrics comin' at you at supersonic speed (J.J. Fad)
    Uh, summa-lumma, dooma-lumma, you assumin' I'm a human
    What I gotta do to get it through to you? I'm superhuman
    Innovative and I'm made of rubber so that anythin' you say is ricochetin' off of me, and it'll glue to you and
    I'm devastatin', more than ever demonstratin', how to give a mother- audience a feelin' like it's levitatin'
    Never fadin' and I know the haters are forever waitin' for the day that they can say I fell off, they'll be celebratin'
    'Cause I know the way to get 'em motivated, I make elevatin' music, you make elevator music
    "Oh, he's too mainstream", well, that's what they do when they get jealous, they confuse it
    "It's not hip-hop, it's pop" 'cause I found a hella way to fuse it
    With rock, shock rap with Doc, throw on "Lose Yourself" and make 'em lose it
    "I don't know how to make songs like that, I don't know what words to use"
    Let me know when it occurs to you while I'm rippin' any one of these verses that versus you
    It's curtains, I'm inadvertently hurtin' you, how many verses I gotta murder to
    Prove that if you were half as nice, your songs, you could sacrifice virgins too?
    Ugh, school flunky, pill junkie, but look at the accolades these skills brung me
    Full of myself, but still hungry
    I bully myself 'cause I make me do what I put my mind to
    And I'm a million leagues above you, ill when I speak in tongues
    But it's still tongue-in-cheek, f- you
    I'm drunk, so, Satan, take the f- wheel, I'ma sleep in the front seat
    Bumpin' Heavy D and the Boyz, still "Chunky but Funky"
    But in my head there's somethin' I can feel tuggin' and strugglin'
    Angels fight with devils and here's what they want from me
    They're askin' me to eliminate some of the women hate
    But if you take into consideration the bitter hatred
    I have, then you may be a little patient, and more sympathetic to the situation
    And understand the discrimination
    But -uck it, life's handin' you lemons? Make lemonade then
    But if I can't batter the women
    How the fu- am I supposed to bake 'em a cake, then?
    Don't mistake him for Satan
    It's a fatal mistake if you think I need to be overseas and take a vacation
    To trip a broad, and make her fall on her face and
    Don't be a -ard, be a king? Think not, why be a king when you can be a God?
    """

    print("=== RhymeMapper - Eminem 'Rap God' ===")

    verse = process_verse(lyrics, artist="Eminem")
    assign_rhyme_labels(verse, min_occurrences=3, tail_window=5)

    visualizer = VisualEngine()
    visualizer.display(verse)

def run_dataset_analysis():
    csv_path = "dataset/artists_sample.csv"
    print("\n=== Analyse Détaillée par Verse ===")
    
    try:
        # On récupère la liste des stats par morceau
        all_verses = analyze_dataset(csv_path, min_occurrences=2, tail_window=None)
    except FileNotFoundError:
        print(f"Fichier {csv_path} introuvable.")
        return

    if not all_verses:
        print("Aucune donnée exploitable.")
        return

    # Header du tableau dynamique
    header = "{:<25} {:<15} {:>10} {:>10} {:>12} {:>10}".format(
        "Track Name", "Artist", "Density", "Multi", "Signatures", "Syll."
    )
    print(header)
    print("-" * len(header))

    for v in all_verses:
        print("{:<25} {:<15} {:>10.1%} {:>10.1%} {:>12} {:>10}".format(
            v['track'][:23], 
            v['artist'][:14],
            v['density'],
            v['multi_score'], # Nouvelle colonne
            v['unique_sigs'],
            v['total_syllables']
        ))


if __name__ == "__main__":
    # Au choix, lancez l'une des deux fonctions ou les deux
    run_rhyme_mapper()        # Pour visualiser le texte colorisé
    run_dataset_analysis()      # Pour l'analyse statistique du dataset
