import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Charger les données
df = pd.read_csv('data/stats.csv')

# Calculer la moyenne par artiste
artist_means = df.groupby('Artist').agg({
    'Density': 'mean',
    'Multi': 'mean'
}).reset_index()

# Afficher le tableau des moyennes (optionnel)
print("Moyennes par artiste :")
print(artist_means)

# Créer le scatter plot
plt.figure(figsize=(10, 6))
sns.scatterplot(data=artist_means, x='Density', y='Multi', hue='Artist', s=200, alpha=0.8)

# Ajouter des labels directement sur les points
for i, row in artist_means.iterrows():
    plt.annotate(row['Artist'], (row['Density'], row['Multi']),
                 xytext=(5, 5), textcoords='offset points', fontsize=9)

plt.xlabel('Densité moyenne (%)', fontsize=12)
plt.ylabel('Multi moyen (%)', fontsize=12)
plt.title('Position moyenne des artistes : Densité vs Multi')
plt.grid(True, linestyle='--', alpha=0.5)
plt.tight_layout()
plt.savefig('data/artist_averages.png', dpi=150)
plt.show()
