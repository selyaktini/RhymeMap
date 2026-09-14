┌─────────────────────────────────────────────────────────────────────────────┐
│                             PIPELINE RHYMEMAPPER                            │
└─────────────────────────────────────────────────────────────────────────────┘

1. ENTREE (Texte brut)
   │
   ▼
2. PRÉTRAITEMENT
   - Nettoyage (suppression ponctuation, minuscules)
   - Découpage en lignes et mots
   │
   ▼
3. ANALYSE PHONÉTIQUE
   - Conversion mot → phonèmes (g2p_en)
   - Découpage des phonèmes en syllabes (syllabify ou heuristique)
   - Pour chaque syllabe : extraire noyau (voyelle) et coda (consonnes)
   │
   ▼
4. SIGNATURE DE RIME
   - Noyau + stress (ex: "AA1" → "AA", stress 1)
   - Signature = "noyau_stress_coda" (ex: "AA_1_RMZ")
   - Option use_consonant_families : coder les consonnes du coda par familles
     (NAS, PLO, SIB, FRI, LIQ, GLI, ASP) → "AA_1_PLO" ; permet les rimes
     approximatives (loud / out). Désactivée par défaut.
   │
   ▼
5. DÉTECTION DES RIMES
   - Compter les occurrences de chaque signature
   - Garder uniquement les signatures apparaissant ≥ min_occurrences (ex: 3)
   - Attribuer un label (A, B, ... Z, AA, AB, ...) à chaque signature retenue
   - Marquer les syllabes correspondantes avec ce label
   │
   ▼
6. CALCUL DES MÉTRIQUES
   - Density   = % de syllabes rimantes
   - Multi     = % de syllabes dans une suite de >= 2 syllabes consécutives
                 portant le MÊME label (rime multisyllabique)
   - Diversity = nb de groupes distincts / total syllabes
   - Signatures = nombre de groupes de rimes distincts
   - Syll.     = nombre total de syllabes
   │
   ▼
7. VISUALISATION
   - Affichage terminal : syllabes rimantes colorées (ANSI)
   - Export CSV des métriques
   - Graphiques : boxplots, scatter plots, heatmaps de similarité
   │
   ▼
8. SORTIE
   - Texte coloré lisible
   - Fichier stats.csv pour comparaison entre artistes/morceaux
