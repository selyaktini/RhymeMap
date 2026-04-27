# Plan de Soutenance — RhymeMapper
**Durée : 15 minutes | Format : Présentation interactive + démo live**

---

## 🛠️ Outil recommandé : Canva

**Pourquoi Canva et pas PowerPoint / LaTeX ?**

| Critère | Canva | PowerPoint | LaTeX/Beamer |
|---|---|---|---|
| Embed vidéo YouTube | ✅ natif | ⚠️ lien externe | ❌ |
| Embed audio | ✅ natif | ✅ | ❌ |
| Design attractif sans effort | ✅ | ⚠️ templates basiques | ❌ |
| Collaboration en ligne | ✅ | ⚠️ OneDrive | ❌ |
| Export PDF/PPT | ✅ | ✅ | ✅ |
| Animations fluides | ✅ | ✅ | ❌ |

→ **Canva** est le meilleur choix ici. Il permet d'intégrer la vidéo YouTube directement dans le slide, d'ajouter un extrait audio de rap, et de faire un design moderne sans perdre du temps.
→ Template recommandé : chercher "Dark Presentation" ou "Music Pitch Deck" sur Canva.

---

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
> [Vos prénoms] — [Date] — [Établissement]

**Audio en fond :** Mettre un beat instrumental de rap en fond très bas (5-10s) pendant qu'on s'installe — ça donne le ton immédiatement. Chercher un beat royalty-free sur Pixabay ou YouTube Audio Library.

---

### SLIDE 2 — Accroche / Question à l'audience (0:30 – 1:30)
**Visuel :** Slide épuré, une seule grande question en blanc sur fond noir.

**Ce qu'on dit :**
> "Avant de commencer, on a une question : *qui écoute du rap ici ?*"
> *(lever la main, regarder l'audience)*
> "Est-ce que quelqu'un peut me dire ce qu'est un **rhyme scheme** ?"
> *(laisser 2-3 réponses, ne pas juger)*
> "Parfait. On va vous montrer que c'est bien plus complexe que ce qu'on pense."

**Note :** Cette interaction brise la glace et engage immédiatement le jury/l'audience.

---

### SLIDE 3 — Activité : Trouve l'intrus (1:30 – 2:30)
**Visuel :** 4 cases côte à côte avec ces expressions (police grande, couleurs vives) :

```
┌──────────────┐  ┌───────────────┐  ┌──────────────┐  ┌──────────────────┐
│   move out   │  │ quite nervous │  │  new route   │  │ up in my house   │
└──────────────┘  └───────────────┘  └──────────────┘  └──────────────────┘
```

**Ce qu'on dit :**
> "Une petite activité. Ces 4 expressions — laquelle ne rime pas avec les autres ?"
> *(laisser l'audience répondre — beaucoup vont hésiter)*
> "La réponse : **'quite nervous'**. Pourtant on entend 'ous' dedans..."
> "C'est exactement le piège. Une rime ne dépend pas des lettres, mais des **sons** — et c'est ça que notre outil analyse."

**Ce slide illustre parfaitement le problème phonétique au cœur du projet.**

---

### SLIDE 4 — C'est quoi un Rhyme Scheme ? (2:30 – 3:30)
**Visuel :** Schéma simple AABB / ABAB / ABCABC avec code couleur (comme notre output terminal)

**Ce qu'on dit :**
> "Un rhyme scheme, c'est le schéma des rimes dans un texte. A, B, C... représentent des sons qui se répètent."
> "Dans le rap, c'est beaucoup plus dense qu'en poésie classique. Les rimes sont **à l'intérieur des lignes**, pas seulement en fin de vers — on appelle ça des rimes **internes** ou **multisyllabiques**."
> "Et ça ne dépend pas seulement du texte écrit : la **delivery**, l'**accent**, le **tempo**, la **prononciation** changent tout."

**Bullet points animés (apparaissent un par un) :**
- Rimes de fin de ligne (`AABB`, `ABAB`...)
- Rimes internes (au milieu d'une ligne)
- Rimes multisyllabiques (plusieurs syllabes qui riment d'un coup)
- Slant rhymes (rimes approximatives par famille de consonnes)

---

### SLIDE 5 — Démonstration vidéo : Mockingbird (3:30 – 5:30)
**Visuel :** Embed de la vidéo YouTube directement dans Canva :
`https://youtu.be/UjOFHNlULJ8?si=dehEzhYSCj-xlpqY`

**Ce qu'on dit (avant de lancer) :**
> "On va regarder 1 minute de cette vidéo — elle illustre parfaitement ce qu'est un rhyme scheme dans le rap."

*(Lancer la vidéo, la laisser tourner ~60-90 secondes)*

**Ce qu'on dit (après) :**
> "Vous voyez la densité des rimes ? Les couleurs qui s'accumulent ? C'est exactement ce que notre programme produit — mais automatiquement, à partir des phonèmes."

---

### SLIDE 6 — Notre projet : Vue d'ensemble (5:30 – 6:30)
**Visuel :** Schéma pipeline horizontal (flèches de gauche à droite, style moderne)

```
Texte brut → Phonèmes (g2p_en) → Syllabes (syllabify) → Signatures → Labels → Couleurs
```

**Ce qu'on dit :**
> "RhymeMapper prend du texte brut — les paroles d'un morceau — et en ressort une visualisation colorée des rimes, syllabe par syllabe."
> "Voilà les grandes étapes :"

*(Pointer chaque étape du pipeline)*

---

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

**Ce qu'on dit :**
> "On a fait des choix techniques précis. Par exemple, pour les rimes approximatives — les *slant rhymes* — on regroupe les consonnes en familles : les nasales, les occlusives, les sibilantes... Ce qui permet de détecter que 'back' et 'black' riment, même si ce n'est pas exactement le même son."

**Montrer rapid un exemple de signature :**
> "`rack` → noyau `AE1` + coda `K` → famille `PLO` → signature `AE_1_K` → label A"

---

### SLIDE 8 — Pourquoi pas ligne par ligne ? (8:00 – 8:45)
**Visuel :** 2 lignes de paroles découpées en syllabes, avec flèches montrant les correspondances

**Ce qu'on dit :**
> "Une question qu'on s'est posée : pourquoi ne pas comparer les lignes deux par deux ?"
> "Le problème : une rime dans le rap peut s'étaler sur 4, 6, 8 lignes. Si on compare seulement L1/L2, L3/L4..., on rate les schémas longs."
> "Notre approche : on compte les signatures sur **l'ensemble du vers**, et on ne retient que celles qui apparaissent au moins N fois — ce qui capture les vraies répétitions."

*(Ce point répond à une note dans vos notes.md — "montrer prq on a pas fait les lignes 2 par 2")*

---

### SLIDE 9 — Démo live : Terminal coloré (9:00 – 11:00)
**Pas de slide — on bascule sur le terminal**

**Ce qu'on fait :**
1. Ouvrir le terminal
2. Lancer `python -m src.main`
3. L'output coloré s'affiche (Rap God d'Eminem)
4. Pointer les couleurs en direct : "Ici, toutes les syllabes rouges partagent la même signature phonétique..."

**Ce qu'on dit :**
> "Voilà l'output de notre programme sur un extrait de *Rap God* d'Eminem — l'un des flows les plus denses du rap."
> "Chaque couleur = un groupe de rimes. Vous pouvez voir que la densité est très élevée — Eminem enchaîne les rimes à l'intérieur même de ses lignes."

**Conseil :** Préparer un screenshot haute qualité en backup au cas où le terminal bugue.

---

### SLIDE 10 — Résultats statistiques (11:00 – 12:30)
**Visuel :** Afficher les graphiques générés par `plots.py`

**3 sous-slides ou 1 slide avec 3 visuels :**

1. **Scatter Density vs Multi** → "Chaque point = un morceau. On voit que certains artistes sont systématiquement plus denses."
2. **Boxplot densité par artiste** → "Distribution. Eminem a une densité élevée ET stable. D'autres artistes sont très variables."
3. **Heatmap de similarité** → "Deux morceaux du même artiste sont plus proches entre eux qu'avec un autre artiste — notre métrique capture un 'style' phonétique."

**Ce qu'on dit :**
> "On a aussi construit un pipeline d'analyse sur dataset. On charge des CSV de paroles, on calcule des métriques par morceau, et on peut comparer des artistes entre eux."

---

### SLIDE 11 — Limites & Perspectives (12:30 – 13:30)
**Visuel :** 2 colonnes "Ce qu'on a fait" vs "Ce qu'on n'a pas eu le temps de faire", fond sobre

**Ce qu'on a fait :**
- ✅ Pipeline phonétique complet
- ✅ Détection rimes terminales + internes
- ✅ Slant rhymes par familles de consonnes
- ✅ Analyse statistique sur dataset
- ✅ Visualisation colorée

**Ce qu'on aurait voulu faire :**
- 🔲 Synchronisation avec l'audio (timestamp mot par mot)
- 🔲 Interface graphique (web ou desktop)
- 🔲 Métrique de multisyllabisme formalisée
- 🔲 Matrice de similarité inter-artistes complète

**Ce qu'on dit :**
> "Notre outil reste en ligne de commande. La prochaine étape naturelle serait de synchroniser la coloration avec l'audio — afficher les syllabes colorées en temps réel pendant que la chanson joue."

---

### SLIDE 12 — Conclusion (13:30 – 14:30)
**Visuel :** Citation d'Eminem ou d'un MC connu sur les rimes, fond sombre, grande typo

**Suggestion de citation (à vérifier) :**
> *"Rapping is poetry with rhythm."*

**Ce qu'on dit :**
> "Le rap est souvent sous-estimé comme forme d'art. Notre projet montre qu'il y a une structure phonétique précise, mesurable, quantifiable — derrière ce qui semble être de l'improvisation."
> "RhymeMapper est une preuve de concept : le NLP et la phonétique peuvent éclairer l'analyse musicale d'une manière qu'on ne fait pas encore assez."

**Slide de fin :** Laisser afficher le nom du projet + repo GitHub + prénoms.

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

---

## ⏱️ Timing résumé

| Segment | Durée | Responsable suggéré |
|---|---|---|
| Slide titre + accroche | 1 min | Présentateur A |
| Activité intruse + définition | 2 min | Présentateur A |
| Vidéo Mockingbird | 2 min | Présentateur B (lance la vidéo) |
| Pipeline & technique | 2 min 30 | Présentateur B |
| Pourquoi pas 2 par 2 | 45 sec | Présentateur A |
| Démo live terminal | 2 min | Présentateur B |
| Stats & graphiques | 1 min 30 | Présentateur A |
| Limites & conclusion | 2 min | Les deux |
| Q&A | 1 min | Les deux |
| **TOTAL** | **~15 min** | |

---

## 💡 Conseils de présentation

- **Parler lentement** — on a tendance à accélérer quand on stresse. 15 min c'est plus long qu'il n'y paraît.
- **Pointer l'écran** quand on montre le code ou les graphiques — ne pas juste lire les slides.
- **L'activité "intruse" est votre meilleur atout** — elle engage immédiatement et illustre le problème mieux que n'importe quelle explication.
- **La démo terminal** doit être préparée : fond sombre, grande police (16pt minimum), commande prête à lancer.
- **Ne pas s'excuser des limites** — les présenter comme des "perspectives" montre qu'on sait où on va.
