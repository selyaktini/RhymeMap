import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Charger les données
df = pd.read_csv('data/stats.csv')

# Configurer le style
sns.set_style('whitegrid')
plt.figure(figsize=(12, 8))

# Créer le scatter plot avec une couleur par artiste
sns.scatterplot(data=df, x='Density', y='Multi', hue='Artist', s=100, alpha=0.7)

# Ajouter des étiquettes et un titre
plt.xlabel('Densité (%)', fontsize=12)
plt.ylabel('Multi (%)', fontsize=12)
plt.title('Densité vs Multi par morceau', fontsize=14)

# Afficher la légende
plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')

# Sauvegarder l'image
plt.tight_layout()
plt.savefig('data/scatter_density_multi.png', dpi=150)
plt.show()
