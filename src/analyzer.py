import csv
from collections import defaultdict
from .phonetics import process_verse
from .engine import assign_rhyme_labels, get_syllable_signature

def analyze_dataset(csv_path, min_occurrences=3, tail_window=2, max_rows=None):
    verse_stats = []

    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if max_rows is not None and i >= max_rows:
                break

            artist = row['artist']
            track = row['track_name']
            text = row['artist_verses']
            
            if not text.strip():
                continue

            # Gestion des sauts de ligne dans le CSV
            text = text.replace('\\n', '\n')

            try:
                verse = process_verse(text, artist=artist)
                assign_rhyme_labels(verse, min_occurrences=min_occurrences, tail_window=tail_window)

                # 1. On aplatit toutes les syllabes du vers dans une liste
                all_syllables = []
                for line in verse.lines:
                    for word in line.words:
                        all_syllables.extend(word.syllables)

                # 2. Calcul des statistiques locales
                local_total_syl = len(all_syllables)
                local_labeled_syl = 0
                local_sigs = set()

                for syl in all_syllables:
                    if syl.rhyme_label:
                        local_labeled_syl += 1
                        sig = get_syllable_signature(syl)
                        local_sigs.add(sig)

                # 3. Calcul de la densité
                density = local_labeled_syl / local_total_syl if local_total_syl > 0 else 0

                # 4. Calcul du score multisyllabique (rimes consécutives)
                multi_rhyme_count = 0
                for j in range(len(all_syllables) - 1):
                    if all_syllables[j].rhyme_label and all_syllables[j+1].rhyme_label:
                        # On vérifie qu'elles appartiennent au même schéma ou simplement qu'elles riment
                        multi_rhyme_count += 1

                multi_score = multi_rhyme_count / local_total_syl if local_total_syl > 0 else 0
                
                verse_stats.append({
                    'track': track,
                    'artist': artist,
                    'density': density,
                    'multi_score': multi_score,
                    'unique_sigs': len(local_sigs),
                    'total_syllables': local_total_syl
                })

            except Exception as e:
                print(f"Erreur sur {artist} - {track}: {e}")

    return sorted(verse_stats, key=lambda x: x['density'], reverse=True)
