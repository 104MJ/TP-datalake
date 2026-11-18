# Répartition J3 / J4 (travail à distance)

J2 est terminé (EDA + ACP des aéroports). On découpe J3 et J4 en **3 thèmes indépendants** : chacun produit ses tables Gold, son test (ou sa segmentation) et son onglet du dashboard, sans attendre les autres.

| | A — Compagnies | B — Saisonnalité & risque | C — Aéroports |
|---|---|---|---|
| Notebook de travail | `notebooks/travail/A_compagnies.ipynb` | `notebooks/travail/B_temps_risque.ipynb` | `notebooks/travail/C_aeroports.ipynb` |
| J3 | §1 asymétrie (Spark SQL) + §2 `airline_ranking` (`DENSE_RANK`, Pareto) | §3 `monthly_trend` (`LAG`, moyenne glissante) + `delay_risk` (table du simulateur) | §4 `airport_profile` (`ROW_NUMBER ... PARTITION BY`) + `OPTIMIZE` |
| J4 | Test de Kruskal-Wallis : retard entre compagnies | Test du χ² : créneau horaire × retard | K-Means des aéroports → `airport_segments` |
| Dashboard | `app/sections/compagnies.py` | `app/sections/temps_risque.py` (simulateur voyageur) | `app/sections/aeroports.py` |
| En plus | Assemblage final de `J3_...ipynb` et `J4_...ipynb` | | |

Notez vos prénoms à côté des lettres dans le groupe, puis chacun ouvre son notebook : tout le détail (consignes, contrat des colonnes, squelettes de requêtes) y est.

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

Les taux sont en **%** (0–100). `dep_slot` vaut `1_nuit (0-5h)`, `2_matin (6-11h)`, `3_apres-midi (12-16h)` ou `4_soir (17-23h)`.

## Dashboard

`app/dashboard.py` est déjà prêt : 3 onglets, chacun appelle `render(load_gold)` dans son fichier de `app/sections/`. `load_gold("nom_table")` renvoie un DataFrame pandas (ou `None` avec un avertissement si la table n'existe pas encore). Le conteneur Streamlit recharge à chaque sauvegarde : `http://localhost:8501`.

Attendu par onglet : au moins un filtre, 1 ou 2 graphiques Plotly, et un `st.expander("Requête SQL & justification statistique")` sous chaque graphique (exigence du TP). Le dashboard ne lit **que** `/lakehouse/gold/`.

## Assemblage final (A, une fois les 3 notebooks poussés)

1. `git pull`, puis copier les cellules dans `J3_Analytics_SQL_Gold.ipynb` (§1–2 de A, §3 + `delay_risk` de B, §4 de C) et `J4_Stats_Segmentation_Dashboard.ipynb` (tests de A et B, K-Means de C), en remplaçant les cellules `TODO` du modèle.
2. Vérifier que tout tourne d'un bout à l'autre : `task test:j3` puis `task test:j4`.
3. Les notebooks de `notebooks/travail/` restent dans le dépôt comme trace du travail de chacun.
