# 🪐 Projet Data Detective Exoplanètes 2026 (`notebooks/example/exo-planette/`)

Architecture complète **Data Lakehouse Médaillon (Bronze → Silver → Gold → Streamlit)** sur **Hadoop HDFS 3.5 (1 NameNode + 3 DataNodes, blocs 16 Mo, réplication=2)**, **PySpark 4.2** et **Delta Lake 4.4**, articulée autour des **7 étapes du cycle *Data Detective*** de [`modules.apti.space/datascience/intro-datascience`](https://modules.apti.space/datascience/intro-datascience) et modernisant les notebooks d'exemple historiques (`notebooks/example/Exo-planet/`).

---

## 📦 5 Datasets Complémentaires & Récents Ingérés (~72 Mo cumulés)

| # | Dataset Kaggle (`kagglehub`) | Mise à jour | Volumétrie | Rôle dans le Lakehouse |
|---|---|---|---|---|
| 1 | `soumyatiw/nasa-confirmed-exoplanets-and-host-stars-dataset` | Juillet 2026 | **48,18 Mo** (4 blocs HDFS de 16 Mo) | **39 954 solutions publiées** (`ps`), demi-amplitude Doppler `pl_rvamp`, identifiants `TIC` / Gaia DR3, métallicité stellaire `[Fe/H]`, spectres JWST/HST. |
| 2 | `darkmatternet/nasa-exoplanet-archive-2026` | Août 2026 | **4,71 Mo** | Table consolidée des **6 336 exoplanètes confirmées jusqu'en 2026** (`pscomppars`). |
| 3 | `danttis/koi-cumulative-table-nasa-exoplanet-dr25` | Septembre 2026 | **11,30 Mo** | **9 564 Kepler Objects of Interest** (`CONFIRMED`, `CANDIDATE`, `FALSE POSITIVE`, SNR). |
| 4 | `shaikizaaz/tess-candidates-with-light-curves` | Octobre 2026 | **7,94 Mo** | **3 871 candidats TESS (TOI)** avec **vraies courbes de lumière de transit** (`local_view` & `global_view`). |
| 5 | `diaaessam/exoplanets-planets-outside-our-galaxy` | Référence `exoplanets.ipynb` | **0,39 Mo** | Chaînes bruitées (`±`, `+err−err`) pour le Data Wrangling Regex PySpark + **noms propres UAI** (*Dimidium*, *Galileo*...). |

---

## 📓 Parcours des 5 Notebooks Pas-à-Pas

1. **`01_Acquisition_Ingestion_HDFS_Bronze.ipynb`** *(Étape 1 — Acquisition)*  
   Téléchargement idempotent dans `/workspace/data_raw/exo-planette/`, téléversement HDFS, cartographie physique des **blocs de 16 Mo** sur `datanode1..3`, vérification de la *Data Locality* Spark (`getNumPartitions()`) et ingestion vers 5 tables Delta Lake `/lakehouse/bronze/exo_*`.
2. **`02_Data_Wrangling_Silver_ACID.ipynb`** *(Étape 2 — Nettoyage / Décrassage anti-GIGO)*  
   Preuve statistique des mécanismes **MAR** (*Transit* sans vitesse radiale vs *Doppler* sans rayon), parsing vectorisé JVM `F.regexp_extract` des barres d'erreur (`±`), dédoublonnage multi-publications par fenêtre de complétude, jointures distribuées `BroadcastHashJoin` sans explosion N-M, calcul de la **3e Loi de Kepler**, de la **Zone Habitable de Kopparapu** et du score **ESI**, puis transactions **ACID Delta Lake** (`_delta_log`, *Schema Enforcement*, `MERGE INTO`, *Time Travel*).
3. **`03_EDA_Visualisation_Biais_Decouverte.ipynb`** *(Étapes 3 & 4 — Visualisation & EDA)*  
   Asymétrie `SKEWNESS` (Médiane/IQR vs Moyenne), **Vallée des Rayons de Fulton ($~1,8\,R_\oplus$)**, **analyse physique détaillée du biais de découverte** (*Transit* $\Delta F/F$ et $P_{\text{geom}} = R_\star/a$, *Doppler* $K$, *Imagerie Directe*, *Microlentille*) face au Système Solaire, corrélations Pearson vs Spearman, ACP 2D, Spark SQL Gold (`DENSE_RANK`, **Pareto**, `LAG()`, `ROW_NUMBER`) et `OPTIMIZE`.
4. **`04_Modelisation_KMeans_Audit_Gold.ipynb`** *(Étapes 5 & 6 — Modélisation & Évaluation/MLOps)*  
   4 tests `scipy.stats` (*Kruskal-Wallis*, *Mann-Whitney U* sur la métallicité `[Fe/H]`, *Spearman* Masse–Rayon, *$\chi^2$*), **taxonomie K-Means ($k=5$)** (*Jupiters Chaudes*, *Géantes Froides*, *Mini-Neptunes*, *Super-Terres Laviques*, *Telluriques Tempérées*), audit *Silhouette / Davies-Bouldin*, et **surveillance MLOps du Data Drift temporel (`PSI`)** entre Pré-Kepler, Kepler et TESS/JWST.
5. **`05_Conclusions_Orbites_Storytelling.ipynb`** *(Étape 7 — Communication & Restitution)*  
   Synthèse décisionnelle, classement des mondes habitables Top ESI, résolution numérique exacte de l'**équation de Kepler** ($M = E - e\sin E$) avec Zone Habitable, export JSON *Universe Sandbox* et contrôle final de la couche Gold.

---

## 🚀 Lancer le Dashboard Dynamique Streamlit (`dashboard.py`)

Afin d'éviter tout conflit Git avec le squelette étudiant `app/dashboard.py`, le dashboard de cet exemple est isolé dans `notebooks/example/exo-planette/dashboard.py`. Deux modes de lancement :

1. **Sans modifier `app/dashboard.py` (dans le Dev Container VS Code ou via `spark-jupyter`)** :
   ```bash
   # Depuis l'intérieur du Dev Container VS Code (port auto-forwardé) :
   streamlit run /workspace/notebooks/example/exo-planette/dashboard.py --server.address=0.0.0.0 --server.port=8502
   ```
2. **Sur le conteneur `streamlit` principal (`http://localhost:8501`)** :
   ```bash
   cp notebooks/example/exo-planette/dashboard.py app/dashboard.py
   ```

Il interroge exclusivement les **8 tables Delta Lake Gold** (`/lakehouse/gold/exo_*`) sur HDFS :
- **🪐 Planétarium Képlérien 2D animé & 3D interactif** (sillages orbitaux, étoile colorée par corps noir $T_{\text{eff}}$, anneau de Zone Habitable, comparateur Système Solaire, échelle des rayons et export JSON *Universe Sandbox*).
- **🔭 Simulateur interactif de télescope virtuel & vraies courbes de lumière TESS** (curseurs $\Delta F/F$, durée de mission et seuil Doppler $K$ recalculant la visibilité du Système Solaire + exploration des transits et binaires à éclipses).
- **🧠 Explorateur K-Means ($k=5$), diagramme Masse–Rayon, ACP 2D & monitoring MLOps du Drift (`PSI`)**.
- **🌌 Entonnoir du Data Detective, film annuel animé des découvertes (1995–2026) & carte galactique (Kepler vs TESS)**.
- **🌍 Chasseur de mondes habitables (diagramme de Kopparapu & classement ESI)**.
