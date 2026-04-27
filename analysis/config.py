from pathlib import Path
import matplotlib.pyplot as plt

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
STATS_FILE = DATA_DIR / "stats.csv"
FIGURES_DIR = DATA_DIR  

# Palette de couleurs pour les artistes
COLORS = plt.cm.tab10.colors   # ou une liste personnalisée
