# Plan de Soutenance — RhymeMapper
**Durée : 10-15 minutes | Format : Présentation interactive + démo live**

## 🎯 Structure générale (15 min)

```
[0:00 – 1:30]  ACCROCHE — Hook rap + question à l'audience
[1:30 – 3:30]  ACTIVITÉ — Intruse + définition Rhyme Scheme
[3:30 – 5:30]  DÉMONSTRATION — Extrait YouTube Mockingbird
[5:30 – 9:00]  PRÉSENTATION DU PROJET — Ce qu'on a fait
[9:00 – 12:00] DÉMO LIVE — Terminal coloré + résultats
[12:00–13:30]  RÉSULTATS & STATS — Graphiques, similarité
[13:30–15:00]  CONCLUSION + Q&A
```

---

## 📋 Détail slide par slide

---

### SLIDE 1 — Titre (0:00 – 0:30)
**Visuel :** Fond sombre, typographie hip-hop (Canva a des polices type "Bebas Neue")
**Texte :**
> **RhymeMapper**
> *Décoder les rimes du rap avec du code*
> [EL YAKTINI Sohayb & BEL HAJJAM Yahya] — [Date] — [ENSEIRB MATMECA]

**Audio en fond :** Mettre un beat instrumental de rap en fond très bas (5-10s) pendant qu'on s'installe — ça donne le ton immédiatement. Chercher un beat royalty-free sur Pixabay ou YouTube Audio Library.

---

### SLIDE 2 — Accroche / Question à l'audience (0:30 – 1:30)
**Visuel :** Slide épuré, une seule grande question en blanc sur fond noir.

### SLIDE 3 — Activité : Trouve l'intrus (1:30 – 2:30)
**Visuel :** 4 cases côte à côte avec ces expressions (police grande, couleurs vives) :

```
┌──────────────┐  ┌───────────────┐  ┌──────────────┐  ┌──────────────────┐
│   move out   │  │ quite nervous │  │  new route   │  │ up in my house   │
└──────────────┘  └───────────────┘  └──────────────┘  └──────────────────┘
```



### SLIDE 4 — C'est quoi un Rhyme Scheme ? (2:30 – 3:30)
**Visuel :** Schéma simple AABB / ABAB / ABCABC avec code couleur (comme notre output terminal)

**Bullet points animés (apparaissent un par un) :**
- Rimes de fin de ligne (`AABB`, `ABAB`...)
- Rimes internes (au milieu d'une ligne)
- Rimes multisyllabiques (plusieurs syllabes qui riment d'un coup)
- Slant rhymes (rimes approximatives par famille de consonnes)

---

### SLIDE 5 — Démonstration vidéo : Mockingbird (3:30 – 5:30)
**Visuel :** Embed de la vidéo YouTube directement dans Canva :
`https://youtu.be/UjOFHNlULJ8?si=dehEzhYSCj-xlpqY`
---

### SLIDE 6 — Notre projet : Vue d'ensemble (5:30 – 6:30)
**Visuel :** Schéma pipeline horizontal (flèches de gauche à droite, style moderne)

```
Texte brut → Phonèmes (g2p_en) → Syllabes (syllabify) → Signatures → Labels → Couleurs
```


### SLIDE 7 — Ce qu'on a construit : Détail technique (6:30 – 8:00)
**Visuel :** Tableau 2 colonnes (Module | Rôle), fond sombre, icônes simples

| Module | Ce qu'il fait |
|---|---|
| `phonetics.py` | Convertit les mots en phonèmes, extrait les syllabes |
| `engine.py` | Calcule les signatures de rime, regroupe par famille de consonnes |
| `models.py` | Structures de données (Syllabe, Mot, Ligne, Vers) |
| `visual.py` | Affichage terminal coloré en ANSI |
| `analyzer.py` | Calcule densité, score multi, signatures uniques |
| `plots.py` | Visualisations statistiques (scatter, boxplot, heatmap) |

**Montrer rapid un exemple de signature :**
> "`rack` → noyau `AE1` + coda `K` → famille `PLO` → signature `AE_1_K` → label A"

---

### SLIDE 8 — Pourquoi pas ligne par ligne ? (8:00 – 8:45)
**Visuel :** 2 lignes de paroles découpées en syllabes, avec flèches montrant les correspondances
---

### SLIDE 9 — Démo live : Terminal coloré (9:00 – 11:00)
**Pas de slide — on bascule sur le terminal**


---

### SLIDE 10 — Résultats statistiques (11:00 – 12:30)
**Visuel :** Afficher les graphiques générés par `plots.py`

**3 sous-slides ou 1 slide avec 3 visuels :**

1. **Scatter Density vs Multi** → "Chaque point = un morceau. On voit que certains artistes sont systématiquement plus denses."
2. **Boxplot densité par artiste** → "Distribution. Eminem a une densité élevée ET stable. D'autres artistes sont très variables."
3. **Heatmap de similarité** → "Deux morceaux du même artiste sont plus proches entre eux qu'avec un autre artiste — notre métrique capture un 'style' phonétique."

---

### SLIDE 11 — Limites & Perspectives (12:30 – 13:30)
**Visuel :** 2 colonnes "Ce qu'on a fait" vs "Ce qu'on n'a pas eu le temps de faire", fond sobre

---

### SLIDE 12 — Conclusion (13:30 – 14:30)
**Visuel :** Citation d'Eminem ou d'un MC connu sur les rimes, fond sombre, grande typo

---

### SLIDE 13 — Q&A (14:30 – 15:00)
**Visuel :** Fond sombre, texte centré :
> **"Des questions ?"**
> *(et en petit : GitHub : github.com/yourusername/RhymeMapper)*

---

## 📌 Checklist avant la soutenance

- [ ] Vidéo YouTube intégrée dans Canva (tester le son)
- [ ] Beat instrumental en fond pour le slide titre (5-10s)
- [ ] Terminal prêt avec `python -m src.main` (testé, pas d'erreur)
- [ ] Screenshot de backup du terminal coloré
- [ ] Graphiques matplotlib exportés en PNG et insérés dans Canva
- [ ] Répétition complète en 15 min (chronométrer)
- [ ] Activité "intruse" préparée (slide bien lisible de loin)

