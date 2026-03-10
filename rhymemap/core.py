import pronouncing

def get_pronunciation(word):
    """Retourne la chaîne phonétique d'un mot (None si inconnu)."""
    phones = pronouncing.phones_for_word(word.lower())
    return phones[0] if phones else None

print(get_pronunciation("communication"))
