# export_for_web.py
import sys
import os
import json
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))

from src.phonetics import process_verse
from src.engine import assign_rhyme_labels



def verse_to_data(verse, artist, track):
    """Convertit un objet Verse en structure JSON‑compatible."""
    lines_data = []
    for line in verse.lines:
        words_data = []
        for word in line.words:
            syllables_data = [
                {"text": syl.text, "label": syl.rhyme_label}
                for syl in word.syllables
            ]
            words_data.append({"full_text": word.text, "syllables": syllables_data})
        lines_data.append(words_data)
    return {
        "artist": artist,
        "track": track,
        "lines": lines_data
    }

def process_lyrics(lyrics_text, artist, track, **kwargs):
    verse = process_verse(lyrics_text, artist=artist)
    assign_rhyme_labels(verse, **kwargs)
    return verse_to_data(verse, artist, track)

def main():
    all_verses = []


    # Quelques morceaux du dataset
    csv_path = "dataset/artists_sample.csv"
    if os.path.exists(csv_path):
        df = pd.read_csv(csv_path)
        for _, row in df.head(5).iterrows():
            lyric = row.get("artist_verses") or row.get("raw_lyrics")
            if pd.isna(lyric):
                continue
            try:
                v = process_lyrics(str(lyric), row["artist"], row["track_name"],
                                   min_occurrences=2, tail_window=None)
                all_verses.append(v)
            except Exception as e:
                print(f"Erreur {row['track_name']} : {e}")

    # Sauvegarde dans un fichier JS
    os.makedirs("web", exist_ok=True)
    with open("web/data.js", "w", encoding="utf-8") as f:
        f.write("const rhymeData = ")
        json.dump(all_verses, f, ensure_ascii=False, indent=2)
        f.write(";")

    print(f"✅ {len(all_verses)} morceaux exportés dans web/data.js")

if __name__ == "__main__":
    main()