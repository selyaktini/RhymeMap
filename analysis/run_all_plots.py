from .data_loader import load_stats
from .plots import (scatter_all_morceaux, scatter_artist_averages,
                    boxplot_density, similarity_heatmap)

def main():
    df = load_stats()
    
    # Sauvegarde des figures
    scatter_all_morceaux(df, save_path='data/scatter_all.png')
    scatter_artist_averages(df, save_path='data/artist_averages.png')
    boxplot_density(df, save_path='data/boxplot_density.png')

    selected_artists = ['Drake', 'Eminem', 'Kendrick Lamar', 'J. Cole']
    for artist in selected_artists:
        if artist in df['Artist'].values:
            similarity_heatmap(df, artist=artist, save_path=f'data/similarity_{artist.replace(" ", "_")}.png')

if __name__ == '__main__':
    main()
