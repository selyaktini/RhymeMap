import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv('data/stats.csv')
df.boxplot(column='Density', by='Artist')
plt.show()
