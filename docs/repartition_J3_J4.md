# Répartition J3 / J4 (travail à distance)

J2 est terminé (EDA + ACP des aéroports). On découpe J3 et J4 en **3 thèmes indépendants** : chacun produit ses tables Gold, ses tests (ou sa segmentation) et son onglet du dashboard, sans attendre les autres.

On suit la structure de **l'exemple du prof** (`notebooks/example/exo-planette/`, à parcourir : notebooks `03` pour J3, `04` pour J4, `05` pour les conclusions, et son `dashboard.py`).

| | A : Compagnies | B : Saisonnalité & risque | C : Aéroports |
|---|---|---|---|
| Notebook de travail | `notebooks/travail/A_compagnies.ipynb` | `notebooks/travail/B_temps_risque.ipynb` | `notebooks/travail/C_aeroports.ipynb` |
| J3 | §1 asymétrie (Spark SQL) + **corrélations Pearson vs Spearman** + `airline_ranking` (`DENSE_RANK`, Pareto) | `monthly_trend` (`LAG`, moyenne glissante) + `delay_risk` (table du simulateur) | `airport_profile` (`ROW_NUMBER ... PARTITION BY`) + `OPTIMIZE` |
| J4 | Tests de **Kruskal-Wallis** (retard entre compagnies) et **Mann-Whitney** (low-cost vs traditionnelles) | Test du **χ²** (créneau × retard) + **suivi du drift (PSI)** → `drift_audit` | Test de **Spearman** (roulage × retard par aéroport) + **K-Means audité** (silhouette + Davies-Bouldin) → `airport_segments` |
| Dashboard | `app/sections/compagnies.py` + `app/sections/conclusions.py` | `app/sections/temps_risque.py` (simulateur voyageur) | `app/sections/aeroports.py` |
| En plus | Assemblage final de `J3_...ipynb` et `J4_...ipynb` + synthèse finale | | |

Chaque test écrit aussi sa ligne dans la table Gold commune `stats_tests` (voir plus bas), affichée dans l'onglet « Ce qu'il faut retenir ».

**Déjà fait : la vitrine 3D.** `notebooks/travail/V_vitrine_3D.ipynb` crée `flight_replay` et `route_flows`. L'onglet « Le ciel en 3D » rejoue en 3D les vols de 4 journées réelles (pire journée, blizzard du 27/01, journée typique, journée la plus ponctuelle) et affiche le réseau de l'année sur une carte 3D. Pour la voir : exécuter ce notebook, puis ouvrir `http://localhost:8501`.

Notez vos prénoms à côté des lettres dans le groupe, puis chacun ouvre son notebook : le détail (consignes, contrat des colonnes, squelettes de requêtes) y est. Les ajouts en **gras** ci-dessus, qui viennent de l'exemple du prof, sont détaillés plus bas, dans « Ce que l'exemple du prof ajoute ».

## Avant de commencer

1. `git pull`, puis `task up`.
2. Exécuter **J1 puis J2** sur votre machine : chacun a son propre HDFS, il faut la table `/lakehouse/silver/flights_enriched` localement.
   Si la cellule `MERGE` (J2 §3.2) plante avec `DELTA_MERGE_UNRESOLVED_EXPRESSION`, c'est qu'une ancienne table Silver traîne : videz `/lakehouse` (`docker exec namenode hdfs dfs -rm -r -skipTrash "/lakehouse/bronze/*" "/lakehouse/silver/*" "/lakehouse/gold/*"`) et relancez J1 puis J2.
3. Ouvrir son notebook de travail avec le kernel du conteneur (Jupyter `http://localhost:8888/?token=bigdata` ou Dev Container).

## Règles pour ne pas se marcher dessus

- **Chacun ne modifie que ses 2 fichiers** (son notebook de travail et son fichier `app/sections/...`). Pas de modification de `J3_...ipynb`, `J4_...ipynb`, `app/dashboard.py` ni des fichiers des autres : comme personne ne touche aux mêmes fichiers, on peut tous travailler sur `main` sans conflit.
- Committer souvent : `git pull --rebase` puis `git push`. Messages comme d'habitude : `feat(J3): ...`.
- Committer les notebooks **exécutés** (sorties visibles), comme J1 et J2.
- Les **tables Gold suivent exactement le contrat** ci-dessous : le dashboard et l'assemblage en dépendent. La fonction `save_gold(...)` de chaque notebook refuse une table à laquelle il manque une colonne. Vous pouvez ajouter des colonnes, pas en renommer.
- Mêmes définitions partout (déjà codées dans la cellule de départ) :
  - taux de retard = % des vols **arrivés** (vue `v_arrives`) avec `arrival_delay >= 15` ;
  - taux d'annulation = % de **tous** les vols (vue `v_silver`) ;
  - par aéroport : filtrer `airport_code_valid` (codes non valides en octobre).
- Chaque résultat est suivi d'une interprétation en Markdown, dans le même style que l'EDA de J2.

## Contrat des tables Gold

| Table | Grain | Colonnes obligatoires | Qui |
|---|---|---|---|
| `airline_ranking` | 1 ligne / compagnie | `airline, airline_name, n_vols, n_retards, taux_retard, retard_median, retard_p25, retard_p75, retard_iqr, retard_p90, rang, part_cumulee_retards` | A |
| `monthly_trend` | 1 ligne / mois | `month, n_vols, taux_retard, retard_median, taux_annulation, taux_retard_mois_prec, evolution_pts, moyenne_glissante_3m` | B |
| `delay_risk` | 1 ligne / (compagnie, aéroport, mois, créneau) | `airline, airline_name, origin_airport, month, dep_slot, n_vols, n_retards, taux_retard` | B |
| `airport_profile` | 1 ligne / aéroport (≥ 300 vols) | `origin_airport, origin_city, origin_state, origin_lat, origin_lon, n_vols, taux_retard, taux_annulation, roulage_median, rang_etat, meilleure_compagnie, taux_retard_meilleure_compagnie` | C |
| `airport_segments` | 1 ligne / aéroport (≥ 300 vols) | `origin_airport, origin_city, origin_lat, origin_lon, n_vols`, les 9 variables de l'ACP, `cluster_id, segment` | C |

| `stats_tests` | 1 ligne / test | `theme, test, h0, statistique, p_value, taille_effet, conclusion` | A, B, C (chacun ses lignes) |
| `drift_audit` | 1 ligne / mois | `month, psi, niveau` (`stable` < 0,1 ≤ `modéré` < 0,25 ≤ `fort`) | B |
| `flight_replay`, `route_flows` | vols de 4 journées / routes | voir `V_vitrine_3D.ipynb` | fait |

Les taux sont en **%** (0–100). `dep_slot` vaut `1_nuit (0-5h)`, `2_matin (6-11h)`, `3_apres-midi (12-16h)` ou `4_soir (17-23h)`.

## Ce que l'exemple du prof ajoute

**Tous : enregistrer chaque test dans `stats_tests`.** Copiez cette fonction dans votre notebook. Le `replaceWhere` de Delta remplace uniquement la ligne de votre test : vous pouvez ré-exécuter sans écraser les tests des autres, et la table est créée au premier appel.

```python
def save_test(theme, test, h0, statistique, p_value, taille_effet, conclusion):
    schema = "theme STRING, test STRING, h0 STRING, statistique DOUBLE, p_value DOUBLE, taille_effet DOUBLE, conclusion STRING"
    row = spark.createDataFrame([(theme, test, h0, float(statistique), float(p_value), float(taille_effet), conclusion)], schema)
    (row.write.format("delta").mode("overwrite")
        .option("replaceWhere", f"theme = '{theme}' AND test = '{test}'")
        .save("/lakehouse/gold/stats_tests"))

# ex. : save_test("compagnies", "Kruskal-Wallis", "Même distribution du retard pour toutes les compagnies", H, p_value, eps2, "H0 rejetée : ...")
```

Avec ~280 000 vols, toutes les p-values seront minuscules. Comme le prof, donnez toujours une **taille d'effet** (ε² pour Kruskal, r = Z/√n pour Mann-Whitney, V de Cramér pour le χ², ρ pour Spearman) et dites si l'écart compte en pratique.

**A : Compagnies**
- J3 : matrice de corrélation **Pearson vs Spearman** sur `arrival_delay, departure_delay, taxi_out, distance, air_time` (échantillon via `.sample(..., seed=42)` puis `.toPandas()`) : deux heatmaps côte à côte, et une phrase sur les écarts (Pearson est sensible aux retards extrêmes, Spearman ne l'est pas).
- J4 : **Mann-Whitney U** sur `arrival_delay` entre compagnies low-cost (`NK`, `F9`, `WN`, `B6`, `VX`) et traditionnelles (les autres).
- Fin de J4 : **synthèse finale** façon notebook `05` du prof (5 à 6 phrases + tableau des facteurs), reprise dans `app/sections/conclusions.py`.

**B : Saisonnalité & risque**
- J4 : **drift (PSI)** de la distribution de `arrival_delay` de chaque mois par rapport à l'année entière. Prenez 10 classes définies par les déciles de l'année ; PSI = Σ (p_mois − p_annee) × ln(p_mois / p_annee). Interprétation : les mois de forte dérive sont-ils ceux des tempêtes (janvier, février) ? → table `drift_audit`.

**C : Aéroports**
- J4 : **Spearman** entre `roulage_median` et `taux_retard` sur les aéroports (ρ = 0,38 dans l'EDA J2 : à confirmer avec la p-value).
- K-Means : comme le prof, choisir k avec **silhouette et Davies-Bouldin** (k = 2 à 8, un graphique avec les deux courbes), puis montrer les clusters sur le **plan de l'ACP** (CP1 × CP2).

## Dashboard

`app/dashboard.py` est déjà prêt : 3 onglets, chacun appelle `render(load_gold)` dans son fichier de `app/sections/`. `load_gold("nom_table")` renvoie un DataFrame pandas (ou `None` avec un avertissement si la table n'existe pas encore). Le conteneur Streamlit recharge à chaque sauvegarde : `http://localhost:8501`.

Attendu par onglet : au moins un filtre, 1 ou 2 graphiques Plotly, et un `st.expander("Requête SQL & justification statistique")` sous chaque graphique (exigence du TP). Le dashboard ne lit **que** `/lakehouse/gold/`.

## Assemblage final (A, une fois les 3 notebooks poussés)

1. `git pull`, puis copier les cellules en suivant l'ordre des notebooks du prof :
   - `J3_Analytics_SQL_Gold.ipynb` (≈ son `03`) : asymétrie → corrélations Pearson/Spearman (A) → tables Gold `airline_ranking` (A), `monthly_trend` + `delay_risk` (B), `airport_profile` (C), `flight_replay` + `route_flows` (vitrine) → `OPTIMIZE` (C) ;
   - `J4_Stats_Segmentation_Dashboard.ipynb` (≈ son `04` + `05`) : les 5 tests (A, B, C) → K-Means audité (C) → drift PSI (B) → synthèse finale (A).
2. Vérifier que tout tourne d'un bout à l'autre : `task test:j3` puis `task test:j4`.
3. Les notebooks de `notebooks/travail/` restent dans le dépôt comme trace du travail de chacun.
