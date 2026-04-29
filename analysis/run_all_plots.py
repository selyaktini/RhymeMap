from .data_loader import load_stats
from .plots import (scatter_all_morceaux, scatter_artist_averages,
                    boxplot_density, similarity_heatmap)

def main():
    df = load_stats()
    
    # Sauvegarde des figures
    scatter_all_morceaux(df, save_path='data/scatter_all.png')
    scatter_artist_averages(df, save_path='data/artist_averages.png')
    boxplot_density(df, save_path='data/boxplot_density.png')
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import MinMaxScaler
from scipy.cluster.hierarchy import dendrogram, linkage
from sklearn.preprocessing import StandardScaler

def artist_similarity_analysis(csv_path='data/stats.csv', save_dir='data/'):
    # Chargement des données
    df = pd.read_csv(csv_path)
    
    # 1. Moyennes par artiste sur les 4 métriques
    artist_means = df.groupby('Artist')[['Density', 'Multi', 'Signatures', 'Syll.']].mean()
    
    # 2. Normalisation MinMax pour la heatmap
    scaler = MinMaxScaler()
    means_norm = scaler.fit_transform(artist_means)
    
    # 3. Matrice de similarité cosinus
    sim = cosine_similarity(means_norm)
    
    # 4. Heatmap
    plt.figure(figsize=(10, 8))
    sns.heatmap(sim, annot=True, fmt='.2f', cmap='coolwarm',
                xticklabels=artist_means.index, yticklabels=artist_means.index)
    plt.title('Similarité entre artistes (cosinus sur les métriques moyennes)')
    plt.tight_layout()
    plt.savefig(f'{save_dir}artist_similarity.png', dpi=150)
    plt.show()
    
    # 5. Dendrogramme (classification hiérarchique)
    scaler_std = StandardScaler()
    X_scaled = scaler_std.fit_transform(artist_means)
    linked = linkage(X_scaled, method='ward')
    
    plt.figure(figsize=(12, 6))
    dendrogram(linked, labels=artist_means.index, orientation='top', distance_sort='descending')
    plt.title('Dendrogramme de similarité entre artistes')
    plt.xlabel('Artiste')
    plt.ylabel('Distance euclidienne (standardisée)')
    plt.tight_layout()
    plt.savefig(f'{save_dir}artist_dendrogram.png', dpi=150)
    plt.show()
    
    # Option : afficher les paires les plus similaires
    print("Matrice de similarité (cosinus) entre artistes :")
    print(pd.DataFrame(sim, index=artist_means.index, columns=artist_means.index))

if __name__ == '__main__':
    artist_similarity_analysis()
    selected_artists = ['Drake', 'Eminem', 'Kendrick Lamar', 'J. Cole']
    for artist in selected_artists:
        if artist in df['Artist'].values:
            similarity_heatmap(df, artist=artist, save_path=f'data/similarity_{artist.replace(" ", "_")}.png')

if __name__ == '__main__':
    main()
