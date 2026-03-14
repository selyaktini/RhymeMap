from g2p_en import G2p 

def get_phonemes(text):
    g2p = G2p()

    ret = g2p(text)
    phonemes = [p for p in ret if p != ' ']
    return phonemes

def get_vowels(text):
    return [v for v in get_phonemes(text) if v[-1] in ['0', '1', '2']]

if __name__ == "__main__":
    ligne1 = "The moment, you own it, you better never let it go"
    ligne2 = "You only get one shot, do not miss your chance to blow"

    print("__first_ligne__")
    print(ligne1)
    print(get_phonemes(ligne1))
    print("__second_ligne__")
    print(ligne2)
    print(get_phonemes(ligne2))

    print("__first_ligne_vowels__")
    print(ligne1)
    print(get_vowels(ligne1))
    print("__second_ligne_vowels__")
    print(ligne2)
    print(get_vowels(ligne2))



