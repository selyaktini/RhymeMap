> **Note (v4.0).** Ces notes sont le plan d'origine, écrit avant la refonte.
> Elles sont gardées telles quelles comme trace du projet. La liste
> « pas fait encore » ci-dessous n'est plus à jour : voir les annotations.

# ameliorer le regroupement des syllabes en prenant en consideration:
- la position dans la ligne (moins restrictive)
- ecars ligne - ligne 
- rendre peu restrictive en terme de 
- etc

# trouver une dataset bien parsable pour pouvoir effectuer des operation et des comparaisons

# implementer un systeme de test de performances (scores/stats/...)
- savoir regrouver des chansons et trouver des resultats comme (deux verses du meme artist sont proches d'eux meme , mais ils sont plus loin de quelques verses d'autres artists)


## pas fait encore:   ← liste d'origine, maintenant traitée
# creer une metrique pour mesurer un score de myltisyllabisme
  ✅ FAIT — métrique « Multi » dans `rhymemap/metrics.py`, plus la détection de
  chaînes multisyllabiques dans `rhymemap/chains.py`.

# faire une interface
  ✅ FAIT — `make serve` ouvre l'interface complète (coloration, survol,
  isolation d'une chaîne, changement de moteur). `make site` produit la version
  statique publiée sur GitHub Pages.

# essayer d ajouter de l audio (synchronisation avec la coloration) 
- ajouter un attribut time dans chaque mot 
- chercher des outils preexistante pour faire cette tache (il y en a bcp mais choisi une qui peut attribuer pour chaque mot un temps t donné)
  ✅ FAIT — et sans dépendance lourde : les sous-titres YouTube donnent le texte
  *et* un temps par mot en une seule requête. Quand il n'y a pas de sous-titres,
  LRCLIB fournit des paroles synchronisées à la ligne. L'alignement forcé
  (WhisperX, aeneas) reste optionnel et non installé.


# essayer de creer une matrice de similarité ? a preciser:
  ⚠️  FAIT, mais le résultat est négatif : les métriques seules ne permettent pas
  d'identifier l'artiste (tous les classifieurs ≤ hasard, ANOVA p = 0.29–0.96
  sur 3 verses par artiste). Voir `eval/ARTIST_ID.md`. Les figures de
  similarité et le dendrogramme montrent donc une structure que ce corpus ne
  peut pas soutenir.

A B C D ......
B 1  
C   1 
D     1? (c'etait faute de frappe)
.
.


### support visuelle pour la soutenance: 
- montrer prq on a pas fait les lignes 2 par 2 
- montrer deux lignes : L1 divisé en syl , L2 divisé en syl et expliquer precisemment ce que notre app fait


## rapport 
- 2 pages resumant l eseentiel , ca doit etre clair et contient l essentiel de ce qu on a fait

## soutenance :
- support sonor obligatoire 
- decrire precisemment ce qu on a fait 
- il y a aura des questions
- support visuelle possible
