"""Moroccan Darija: Arabizi spelling -> phonemes -> syllables.

Darija is written online in *Arabizi*: Latin letters plus digits chosen for
their shape, because the Arabic letters they stand for have no Latin
equivalent.

    3 = ع   7 = ح   9 = ق   2 = ء   5 = خ (also written kh)

That convention is what makes this module possible. Arabizi is very nearly
phonemic -- a letter maps to a sound, not to three centuries of spelling drift
-- so Darija needs no pronunciation dictionary and no neural model. A grapheme
table and a syllabifier are enough, and unlike CMUdict they never miss a word.

Two things genuinely differ from English and are handled here:

**Places of articulation English does not have.** English stops at the velum;
Arabic keeps going, to the uvula (ق خ غ) and the pharynx (ح ع). Run "3ndi"
through an English grapheme-to-phoneme model and you get nonsense, because
there is no symbol for the sound the "3" is standing for. ``rhymemap.phonology``
carries those phonemes; this module is what produces them.

**Words with no written vowel.** "ktbt" (I wrote), "chft" (I saw), "drt" (I
did). Darija allows consonant clusters English never would, and the schwa that
breaks them up is not written down. Left alone these words have no nucleus at
all, so they would vanish from a rhyme analysis -- yet "drt"/"chft" is a real
rhyme, and a common one. ``_insert_schwas`` puts the vowel back.

Vowels deliberately reuse the English inventory (/a/ -> AA, /i/ -> IY, /u/ ->
UW, schwa -> AH0) instead of getting symbols of their own. Moroccan rap
code-switches constantly between Darija, French and English, often inside one
bar; a single shared vowel space is what lets the engine notice that "bzaf"
and "staff" rhyme. The consonants are extended because they had to be -- the
sounds are genuinely absent -- and the vowels are not, because they are not.
"""

from __future__ import annotations

import re
from pathlib import Path

# ---------------------------------------------------------------------------
# Graphemes
#
# Matched longest-first, so "kh" wins over "k" and "ou" over "o". Order within
# each length does not matter; the tokeniser tries every 2-character key before
# any 1-character key.
# ---------------------------------------------------------------------------

CONSONANT_GRAPHEMES = {
    # The digits. These are the whole reason Arabizi works as a phonemic
    # spelling, and the reason an English G2P cannot read Darija at all.
    "2": "Q2",    # ء  glottal stop
    "3": "AIN",   # ع  voiced pharyngeal
    "5": "X",     # خ  voiceless uvular fricative
    "7": "HS",    # ح  voiceless pharyngeal
    "9": "Q",     # ق  voiceless uvular plosive

    # Digraphs.
    "kh": "X",    # خ
    "gh": "GH",   # غ
    "ch": "SH",   # ش  -- French-influenced spelling: "chnou", "chouf"
    "sh": "SH",   # ش
    "th": "TH",   # ث
    "dh": "DH",   # ذ

    # Single letters.
    "b": "B", "t": "T", "j": "ZH", "d": "D", "r": "R", "z": "Z",
    "s": "S", "f": "F", "q": "Q", "k": "K", "l": "L", "m": "M",
    "n": "N", "h": "HH", "w": "W", "y": "Y", "g": "G", "p": "P",
    "v": "V", "x": "X", "c": "K",

    # Emphatics, written with a capital in the careful Arabizi convention
    # ("Sbar", "Tri9"). Most people do not bother, so in practice these arrive
    # from the lexicon rather than from the spelling; see EMPHATIC_WORDS.
    "S": "SD",    # ص
    "D": "DD",    # ض
    "T": "TD",    # ط
    "Z": "ZD",    # ظ
}

VOWEL_GRAPHEMES = {
    # Long / digraph vowels.
    "aa": "AA1", "ii": "IY1", "uu": "UW1", "ee": "IY1", "oo": "UW1",
    "ou": "UW1",              # French spelling for /u/: "chouf", "bouhali"
    "ay": "AY1", "aw": "AW1", "ey": "EY1", "oy": "OY1",   # but see GLIDE_DIGRAPHS

    # Short vowels.
    "a": "AA1",
    "i": "IY1",
    "u": "UW1",
    "o": "OW1",               # usually [o~u]: "khoya", "7ob"
    "e": "AH0",               # the written schwa, when anyone writes it
    "é": "EY1", "è": "EH1", "ê": "EH1", "â": "AA1", "î": "IY1", "ô": "OW1",
}

SCHWA = "AH0"

# A diphthong only when nothing follows it. In "kayn" the "ay" is one vowel
# [aj]; in "khoya" the same two letters are a vowel plus a consonant, [xo.ja],
# because a vowel follows and claims the glide as its onset.
GLIDE_DIGRAPHS = frozenset({"ay", "aw", "ey", "oy"})

_GRAPHEMES = {**CONSONANT_GRAPHEMES, **VOWEL_GRAPHEMES}
_MAX_GRAPHEME = max(len(g) for g in _GRAPHEMES)

# The digits that identify a word as Darija on sight. 2 and 5 are Arabizi too,
# but they are also English texting shorthand ("2pac", "b4", "5th"), so they
# carry no weight on their own; see has_arabizi_digit.
STRONG_DIGITS = frozenset("379")


# ---------------------------------------------------------------------------
# Spelling -> phonemes
# ---------------------------------------------------------------------------


def _tokenise(word: str) -> list[tuple[str, str]]:
    """Split a spelling into ``("C"|"V", phoneme)`` pairs, longest match first.

    Unknown characters are dropped rather than guessed at: a stray letter is
    better left out of the rime than turned into a sound the rapper never said.
    """
    tokens: list[tuple[str, str]] = []
    i, n = 0, len(word)
    while i < n:
        for size in range(min(_MAX_GRAPHEME, n - i), 0, -1):
            chunk = word[i:i + size]
            # Exact first, so the capitalised emphatics ("Sbar") are seen before
            # the plain letters they would otherwise fold into.
            phoneme = _GRAPHEMES.get(chunk) or _GRAPHEMES.get(chunk.lower())
            if phoneme and chunk.lower() in GLIDE_DIGRAPHS:
                nxt = word[i + size: i + size + 2].lower()
                if nxt[:2] in VOWEL_GRAPHEMES or nxt[:1] in VOWEL_GRAPHEMES:
                    phoneme = None          # the glide belongs to the next syllable
            if phoneme:
                kind = "V" if chunk.lower() in VOWEL_GRAPHEMES or chunk in VOWEL_GRAPHEMES else "C"
                tokens.append((kind, phoneme))
                i += size
                break
        else:
            i += 1
    return tokens


def _break_run(run: list, after_vowel: bool, before_vowel: bool) -> list:
    """Insert schwas into one consonant run until every consonant has a home.

    A consonant needs a syllable to belong to. It can be the coda of the vowel
    before it (Darija takes up to two) or the onset of the vowel after it. When
    a run is longer than its neighbours can absorb, the leftover consonants get
    a schwa of their own -- which is exactly what a Moroccan speaker does with
    "ktbt": [ktebt], not [ktbt].
    """
    run = list(run)
    coda_cap = 2 if after_vowel else 0
    onset_cap = 0
    if before_vowel:
        # Word-initially Darija really does allow two-consonant onsets: "bghit"
        # is [bghit], "chnou" is [chnou]. Once a syllable precedes, the ordinary
        # Arabic split takes over and the onset is a single consonant --
        # "3ndi" is [3en.di], not [3e.ndi].
        onset_cap = 1 if (after_vowel or len(run) > 2) else 2

    if len(run) <= coda_cap + onset_cap:
        return run

    right = run[len(run) - onset_cap:] if onset_cap else []
    left = run[: len(run) - onset_cap] if onset_cap else run

    placed: list = []
    capacity = coda_cap
    while len(left) > capacity:
        take = min(2, len(left) - 1)
        if take <= 0:
            break
        placed = [("V", SCHWA)] + left[len(left) - take:] + placed
        left = left[: len(left) - take]
        # What is still to the left is now the new schwa's onset, not a coda.
        capacity = 2

    return left + placed + right


def _insert_schwas(tokens: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """Put back the vowels Arabizi does not write."""
    out: list[tuple[str, str]] = []
    i, n = 0, len(tokens)
    while i < n:
        if tokens[i][0] == "V":
            out.append(tokens[i])
            i += 1
            continue
        j = i
        while j < n and tokens[j][0] == "C":
            j += 1
        after_vowel = bool(out) and out[-1][0] == "V"
        out.extend(_break_run(tokens[i:j], after_vowel, before_vowel=j < n))
        i = j

    # A lone consonant has no room for the rule above to work with: there is
    # nothing to split. It still needs a vowel, because Darija's one-letter
    # words are real words -- "w" (and), "f" (in), "l" (the) -- and a syllable
    # with no nucleus is not a syllable, so the word would vanish.
    if out and not any(kind == "V" for kind, _ in out):
        out.append(("V", SCHWA))
    return out


def _syllabify(tokens: list[tuple[str, str]]) -> list[dict]:
    """Group a schwa-filled token list into ``{onset, nucleus, coda}`` parts."""
    nuclei = [i for i, (kind, _) in enumerate(tokens) if kind == "V"]
    if not nuclei:
        return []

    parts = [{"onset": [], "nucleus": tokens[i][1], "coda": []} for i in nuclei]

    # Everything before the first vowel opens the word.
    parts[0]["onset"] = [p for _, p in tokens[: nuclei[0]]]

    # Between two vowels, one consonant opens the second syllable and the rest
    # close the first: the ordinary Arabic CVC.CV split.
    for index in range(len(nuclei) - 1):
        run = [p for _, p in tokens[nuclei[index] + 1: nuclei[index + 1]]]
        if run:
            parts[index + 1]["onset"] = run[-1:]
            parts[index]["coda"] = run[:-1]

    # Everything after the last vowel closes the word.
    parts[-1]["coda"] = [p for _, p in tokens[nuclei[-1] + 1:]]
    return parts


def arabizi_phonemes(word: str) -> list[str]:
    """Phonemes for one Arabizi word: ``"3ndi"`` -> ``["AIN", "AH1", "N", "D", "IY1"]``."""
    phonemes: list[str] = []
    for part in arabizi_syllables(word):
        phonemes.extend(part["onset"])
        if part["nucleus"]:
            phonemes.append(part["nucleus"])
        phonemes.extend(part["coda"])
    return phonemes


def arabizi_syllables(word: str) -> list[dict]:
    """Syllabify one Arabizi word into ``[{onset, nucleus, coda}, ...]``.

    The shape ``rhymemap.phonetics`` expects from CMUdict, so a Darija word
    travels through the rest of the engine exactly like an English one.
    """
    if not word:
        return []

    parts = _syllabify(_insert_schwas(_tokenise(emphatic_spelling(word))))

    # Darija has no vowel reduction to mark, so every full vowel is written
    # stressed and the schwa is not -- with one exception. When the schwa is a
    # word's only vowel ("drt", "chft") it is that word's main vowel, and the
    # engine drops unstressed syllables away from a line end. Leaving it at 0
    # would delete the word from the analysis, and "drt"/"chft" is a real rhyme.
    #
    # The one-letter prepositions are the counter-exception. A clitic is
    # unstressed by definition -- "f tri9" is said [ftri9], leaning on the word
    # after it -- so promoting its schwa would let "w", "f", "l" and "b" anchor
    # a rhyme group with each other, which is noise standing where a rhyme
    # should be.
    if (len(parts) == 1 and parts[0]["nucleus"] == SCHWA
            and str(word).strip().lower() not in DARIJA_CLITICS):
        parts[0]["nucleus"] = "AH1"
    return parts


# ---------------------------------------------------------------------------
# Which language is this word?
#
# Three tiers, in order of how much they can be trusted:
#
#   1. An Arabizi digit. "3", "7" and "9" are used for nothing else, so a word
#      containing one is Darija and that is the end of it.
#   2. DARIJA_WORDS, curated below. These override CMUdict, which is why the
#      list is hand-filtered rather than scraped: every entry was checked
#      against the dictionary and anything English would want more was dropped.
#      That is what keeps "had", "men", "hit", "jay" and "lil" English, even
#      though all four are also everyday Darija.
#   3. The generated word list, 127,596 spellings derived from the master
#      lexicon. It went through the same filter mechanically: every spelling
#      CMUdict knows was removed when it was built.
# ---------------------------------------------------------------------------

DARIJA_WORDS = frozenset("""
ana nta nti huwa hiya hna ntuma homa dyal dyali dyalk dyalo dyalha dyalna
li hadi hada hadok hadchi dakchi dik dak fin kifach kifma chnou chno achno ach
wach wahed chi kol kola koulchi kulchi ghir gher walakin bach hita mnin
mn ila wla walla bla bnadem daba deba mazal baqi rah raha rani rak
kayn kayna kaynin makayn makaynch machi mashi walo chwiya bzaf bezzaf kter
ktar temma tma taht mora jnb hda dima ghadi ghadya ghadin jaya safi yallah
yalah zid aji chouf chuf gol gul golt dert drt ktbt chft bghit bghina bghaw
khdem khdam khasni khasek bghi nsit nsa jbt wslt mchit mcha mchaw msht
jit tbark hamdulah nchouf nchof kanbghi kanbghik kanmchi ghanmchi bghitk
khoya khti khouya sahbi drari derri bnat wlad wldi waldi mra rajel dar homti
houma zanka blad lblad mghrib maghrib flous flouss drahm khdma khedma hyat
mout rouh ras rasi yed yedi rjl dem nar lma chems njoum sma waqt fuq
lhal nhar sbah chhar jouj tlata rbaa khamsa sta tmnya zwin zwina
mzyan mzyana khayb shab sghir kbir jdid qdim baba mouhim swiya
wakha iyeh ayeh lla labas bikhir kifak bslama chokran smhli smh fhmt fhem
tsna wa3ra wa3r kdoub kdb s7i7 bnin nas nass 3ibad kla chrb glst
tl3 nzl dkhl khrj rj3 b9a b9it 9rit sm3t
""".split())

# Words whose commonest Arabizi spelling hides an emphatic. Written with
# capitals ("Sbar", "Tri9") by people who are careful about it and with plain
# letters by everyone else, so the spelling alone cannot tell you. A lexicon is
# the real source; this is enough for the emphatic contrast to be live without
# one.
EMPHATIC_WORDS = {
    "sbar": "Sbar", "sber": "Sber", "sghir": "Sghir", "sghira": "Sghira",
    "sa7b": "Sa7b", "sa7bi": "Sa7bi", "sahbi": "Sahbi", "sbah": "Sbah",
    "sda3": "Sda3", "sw7ab": "Sw7ab", "s7i7": "S7i7", "sot": "Sot",
    "tri9": "Tri9", "tri9a": "Tri9a", "tab": "Tab", "tayb": "Tayb",
    "tar": "Tar", "tayr": "Tayr", "tfl": "Tfl", "tbib": "Tbib",
    "tbla": "Tbla", "batl": "baTl", "khatar": "khaTar", "wast": "wasT",
    "dhar": "Dhar", "dlam": "Dlam", "dlma": "Dlma",
}

# The generated word list: 127,596 Latin-script Darija spellings derived from
# dataset/darija_lexicon_master_150k.csv, with everything CMUdict already knows
# filtered out. See scripts/build_darija_lexicon.py. Loaded on first use, not at
# import -- it is 1.4 MB, and an English-only run never needs it.
LEXICON_PATH = Path(__file__).resolve().parent / "data" / "darija_words.txt"

_LEXICON: frozenset[str] | None = None


def lexicon() -> frozenset[str]:
    """The generated word list, read once. Empty if it was never built."""
    global _LEXICON
    if _LEXICON is None:
        try:
            _LEXICON = frozenset(
                line.strip()
                for line in LEXICON_PATH.read_text(encoding="utf-8").splitlines()
                if line.strip() and not line.startswith("#")
            )
        except OSError:
            # The curated list is meant to stand on its own, and does. Losing
            # the generated one costs coverage, not correctness.
            _LEXICON = frozenset()
    return _LEXICON


def lexicon_size() -> int:
    """How many spellings the generated word list contributes."""
    return len(lexicon())


# Rap is full of digits that are not Arabizi: ordinals, calibres, counts, and
# the texting spellings the genre has used since the nineties. Every one of
# these would otherwise be read as Darija, because "3rd" and "9mm" do contain a
# 3 and a 9.
_ENGLISH_NUMERIC = re.compile(r"^\d+(st|nd|rd|th|s|k|m|mm|x|oz)?$", re.IGNORECASE)
_ENGLISH_DIGIT_SLANG = frozenset("""
2pac 2chainz b4 4ever 4eva 2nite 2night 2day 2morrow 4got 4give 4get gr8 l8
l8r m8 str8 w8 h8 sk8 cre8 4real 2real 1nce 2gether 24 247 365
""".split())


def has_arabizi_digit(word: str) -> bool:
    """True if the word carries a digit that means a Darija consonant.

    Only 3, 7 and 9 count. 2 and 5 are Arabizi too, but they are also English
    texting shorthand -- "2pac", "b4", "5th" -- and a false positive is worse
    than a miss here: a Darija word this does not catch still gets analysed,
    just through the English path, whereas an English word sent to the Darija
    path comes out as sounds nobody said. Words spelled with 2 or 5 are picked
    up by DARIJA_WORDS and the lexicon instead.
    """
    word = str(word).strip().lower()
    if not any(ch.isalpha() for ch in word):
        return False
    if _ENGLISH_NUMERIC.match(word) or word in _ENGLISH_DIGIT_SLANG:
        return False
    return any(ch in STRONG_DIGITS for ch in word)


def is_darija(word: str) -> bool:
    """Is this word unmistakably Darija? Strong enough to outrank CMUdict.

    All three tiers earn that by construction. The digits are Arabizi and
    nothing else. DARIJA_WORDS was checked against the dictionary by hand, and
    anything English wanted more was dropped. The generated list had every
    CMUdict spelling filtered out of it before it was written, so a word can be
    in one or the other but never both.

    Which is also what lets this drive ``detect_language``: a test that cannot
    fire on an English word is a test you can count occurrences of.
    """
    word = str(word).strip().lower()
    if not word:
        return False
    return has_arabizi_digit(word) or word in DARIJA_WORDS or word in lexicon()


def emphatic_spelling(word: str) -> str:
    """Re-spell a word with its emphatics marked, if we know of any."""
    return EMPHATIC_WORDS.get(str(word).strip().lower(), word)


# ---------------------------------------------------------------------------
# Which language is this *verse*?
#
# Per-word detection alone cannot work, and the reason is worth stating: Darija
# inflects heavily. "kteb" (he wrote) is also ktbt, ktbti, ktbna, ktbo, kaykteb,
# ghaykteb, makatbch, lktab, bktabi... A word list of any size will keep missing
# forms, and every miss lands in an English neural G2P that answers with sounds
# nobody said -- "kayshuf" came back as K EY1 Z HH AH0 F.
#
# But a song is not ambiguous even when its words are. A Moroccan track is
# Darija with French and English dropped into it, and the Darija is dense enough
# that the unmistakable words -- the ones carrying a 3, a 7 or a 9 -- give it
# away several times a verse. So the verse is classified once, from the evidence
# that cannot be argued with, and that verdict decides what happens to every
# word CMUdict could not name. English insertions still resolve as English:
# CMUdict knows "gangster" and "money", and it is asked first either way.
# ---------------------------------------------------------------------------

# Single-letter words. Darija writes its prepositions and conjunctions this way
# constantly -- "w" (and), "f" (in), "l" (the, to), "b" (with), "d" (of) -- and
# CMUdict answers for all five with the *name* of the letter, so "w" comes back
# as "double-u": five phonemes and three syllables of pure noise in the middle
# of a bar. They are only read this way in a verse already established as
# Darija, since a stray "b" in an English verse is likelier to be a letter.
DARIJA_CLITICS = frozenset({"w", "f", "l", "b", "d"})

# Enough evidence to call a verse Darija. Three unmistakable words guards
# against a single stray token, and 5% against a long English verse that quotes
# a line of Darija -- in which case the quoted line's own words still route
# correctly on their digits, which is the outcome we want either way.
MIN_DARIJA_WORDS = 3
MIN_DARIJA_SHARE = 0.05

_WORD = re.compile(r"[\w']+")


def count_darija(text: str) -> tuple[int, int]:
    """``(unmistakably Darija, total)`` word counts for a block of text."""
    words = _WORD.findall(str(text).lower())
    return sum(1 for w in words if is_darija(w)), len(words)


def detect_language(text: str) -> str:
    """``"dar"`` or ``"en"`` for a verse, from its unmistakable words alone."""
    strong, total = count_darija(text)
    if not total:
        return "en"
    if strong >= MIN_DARIJA_WORDS and strong / total >= MIN_DARIJA_SHARE:
        return "dar"
    return "en"
