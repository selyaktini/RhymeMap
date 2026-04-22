import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
from collections import defaultdict
from src.phonetics import process_verse
from src.engine import assign_rhyme_labels, get_syllable_signature

def compute_metrics(verse):
    total_syllables = 0
    rhyming_syllables = 0
    signature_counts = defaultdict(int)
    
    for line in verse.lines:
        for word in line.words:
            for syl in word.syllables:
                total_syllables += 1
                if syl.rhyme_label:
                    rhyming_syllables += 1
                sig = get_syllable_signature(syl)
                if sig:
                    signature_counts[sig] += 1
    
    density = (rhyming_syllables / total_syllables * 100) if total_syllables else 0
    # Diversité des signatures (nombre de signatures uniques / total syllabes) * 100
    diversity = (len(signature_counts) / total_syllables * 100) if total_syllables else 0
    
    return {
        'density': round(density, 1),
        'multi': round(diversity, 1),   # on garde le nom 'multi' pour compatibilité
        'signatures': len(signature_counts),
        'syllables': total_syllables
    }

def main():
    df = pd.read_csv('dataset/lyrics_raw.csv')
    
    # Utiliser la colonne 'artist_verses' si elle existe, sinon 'raw_lyrics'
    if 'artist_verses' in df.columns:
        lyrics_col = 'artist_verses'
    else:
        lyrics_col = 'raw_lyrics'
    
    results = []
    for idx, row in df.iterrows():
        track = row['track_name']
        artist = row['artist']
        lyrics = row[lyrics_col]
        if pd.isna(lyrics) or not isinstance(lyrics, str):
            continue
        try:
            verse = process_verse(lyrics, artist=artist)
            assign_rhyme_labels(verse, min_occurrences=3, only_terminal=True)
            metrics = compute_metrics(verse)
            results.append({
                'Track Name': track,
                'Artist': artist,
                'Density': metrics['density'],
                'Multi': metrics['multi'],
                'Signatures': metrics['signatures'],
                'Syll.': metrics['syllables']
            })
            print(f"✅ {track} - Density: {metrics['density']}% - Multi: {metrics['multi']}%")
        except Exception as e:
            print(f"❌ Erreur sur {track}: {e}")
    
    os.makedirs('data', exist_ok=True)
    out_df = pd.DataFrame(results)
    out_df.to_csv('data/stats.csv', index=False)
    print(f"\n📁 Fichier sauvegardé : data/stats.csv ({len(results)} morceaux)")

if __name__ == '__main__':
    main()
