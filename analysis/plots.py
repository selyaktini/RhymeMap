import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from .config import COLORS
from .data_loader import load_stats, get_artist_means

def scatter_all_morceaux(df, save_path=None):
    """Scatter plot Density vs Multi, un point par morceau, couleur par artiste."""
    plt.figure(figsize=(10, 6))
    artists = df['Artist'].unique()
    for i, artist in enumerate(artists):
        subset = df[df['Artist'] == artist]
        plt.scatter(subset['Density'], subset['Multi'], 
                    label=artist, alpha=0.7, s=80, color=COLORS[i % len(COLORS)])
    plt.xlabel('Densité (%)', fontsize=12)
    plt.ylabel('Multi (%)', fontsize=12)
    plt.title('Densité vs Multi (tous les morceaux)')
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.grid(True, linestyle='--', alpha=0.5)
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.show()

def scatter_artist_averages(df, save_path=None):
    """Scatter plot des moyennes par artiste."""
    means = get_artist_means(df)
    plt.figure(figsize=(10, 6))
    for i, row in means.iterrows():
        plt.scatter(row['Density'], row['Multi'], s=200, color=COLORS[i % len(COLORS)])
        plt.annotate(row['Artist'], (row['Density'], row['Multi']),
                     xytext=(5, 5), textcoords='offset points', fontsize=9)
    plt.xlabel('Densité moyenne (%)', fontsize=12)
    plt.ylabel('Multi moyen (%)', fontsize=12)
    plt.title('Position moyenne des artistes : Densité vs Multi')
    plt.grid(True, linestyle='--', alpha=0.5)
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.show()

def boxplot_density(df, save_path=None):
    """Boxplot de la densité par artiste."""
    plt.figure(figsize=(12, 6))
    sns.boxplot(data=df, x='Artist', y='Density', palette='Set2')
    plt.xticks(rotation=45, ha='right')
    plt.ylabel('Densité (%)')
    plt.title('Distribution de la densité par artiste')
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.show()

def similarity_heatmap(df, artist=None, save_path=None, max_name_len=25, max_items=20):
    """
    Heatmap de similarité cosinus pour les morceaux d’un artiste.
    - Nombre de morceaux limité à max_items (par défaut 20).
    - Noms tronqués.
    - Annotations désactivées si trop de morceaux.
    """
    if artist:
        df = df[df['Artist'] == artist]
    if len(df) < 2:
        print(f"Pas assez de morceaux pour {artist} (n={len(df)})")
        return
    if len(df) > max_items:
        print(f"Trop de morceaux pour {artist} ({len(df)}), prise des {max_items} premiers.")
        df = df.head(max_items)
    
    features = ['Density', 'Multi', 'Signatures', 'Syll.']
    X = df[features].values
    scaler = MinMaxScaler()
    X_norm = scaler.fit_transform(X)
    sim = cosine_similarity(X_norm)
    
    # Noms tronqués
    short_names = []
    for name in df['Track Name']:
        if len(name) > max_name_len:
            short_names.append(name[:max_name_len-3] + '...')
        else:
            short_names.append(name)
    
    # Taille dynamique
    figsize = (max(8, len(df)*0.6), max(6, len(df)*0.6))
    plt.figure(figsize=figsize)
    
    annot = len(df) <= 15   # annotations seulement si <= 15
    fmt = '.2f' if annot else ''
    ax = sns.heatmap(sim, annot=annot, fmt=fmt, cmap='coolwarm',
                     xticklabels=short_names, yticklabels=short_names,
                     cbar_kws={'label': 'Similarité cosinus'})
    ax.set_title(f'Similarité entre morceaux – {artist}')
    plt.xticks(rotation=45, ha='right', fontsize=8)
    plt.yticks(fontsize=8)
    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.show()
