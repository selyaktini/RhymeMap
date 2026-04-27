import pandas as pd
from .config import STATS_FILE

def load_stats():
    df = pd.read_csv(STATS_FILE)
    # nettoyage : suppression des lignes avec valeurs manquantes
    df = df.dropna(subset=['Density', 'Multi', 'Signatures', 'Syll.'])
    return df

def get_artist_means(df):
    return df.groupby('Artist').agg({
        'Density': 'mean',
        'Multi': 'mean',
        'Signatures': 'mean',
        'Syll.': 'mean'
    }).reset_index()
