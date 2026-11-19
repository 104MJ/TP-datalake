"""Chargement des tables Gold, barre de filtres « Votre vol » et calcul des taux."""

from dataclasses import dataclass

import pandas as pd
import streamlit as st
from py4j.protocol import Py4JNetworkError
from pyspark import SparkContext
from pyspark.errors import AnalysisException
from pyspark.sql import SparkSession

from sections.theme import MOIS

MIN_VOLS = 200  # en dessous, un taux de retard n'est pas affiché (trop instable)
CLES = {"f_apt": "Tous", "f_cie": "Toutes", "f_mois": (1, 12), "f_heures": (0, 23)}


@st.cache_resource
def _spark():
    return (SparkSession.builder.appName("StreamlitGoldReader")
            .config("spark.driver.memory", "1g").config("spark.ui.enabled", "false").getOrCreate())


def _oublier_spark():
    """JVM de Spark arrêtée (souvent faute de mémoire) : on jette la session en cache pour en lancer une neuve."""
    _spark.clear()
    SparkContext._gateway = SparkContext._jvm = SparkContext._active_spark_context = None
    SparkSession._instantiatedSession = SparkSession._activeSession = None


@st.cache_data(ttl=600, show_spinner="Lecture de la couche Gold…")
def _lire(nom: str) -> pd.DataFrame:
    try:
        return _spark().read.format("delta").load(f"/lakehouse/gold/{nom}").toPandas()
    except (ConnectionError, Py4JNetworkError):
        _oublier_spark()
        return _spark().read.format("delta").load(f"/lakehouse/gold/{nom}").toPandas()


def gold(nom: str):
    """Table /lakehouse/gold/<nom> en pandas, ou None si elle n'existe pas encore."""
    try:
        return _lire(nom)
    except AnalysisException:
        st.info(f"Table `{nom}` absente : exécutez le notebook qui la crée.")
    except Exception as exc:
        st.error(f"Lecture de `{nom}` impossible ({type(exc).__name__}) : vérifiez que HDFS tourne, "
                 "puis relancez le dashboard (`docker compose restart streamlit`).")
    return None


def risque():
    df = gold("risque_retard")
    return None if df is None else df


def conserver_filtres():
    """Les filtres vivent dans f_* (hors widgets) : Streamlit efface l'état d'un widget absent de la page."""
    for k, v in CLES.items():
        st.session_state.setdefault(k, v)


def _copier(k, wk):
    st.session_state[k] = st.session_state[wk]


def _nouvelle_version():
    """Change la clé des widgets : ils sont recréés avec la valeur des filtres, sans état périmé côté navigateur."""
    st.session_state["v_filtres"] = st.session_state.get("v_filtres", 0) + 1


def _reinitialiser():
    for k, v in CLES.items():
        st.session_state[k] = v
    _nouvelle_version()


def signature() -> str:
    """Identifiant de l'état des filtres, utilisé dans la clé des graphiques cliquables."""
    s = st.session_state
    return f"{s.f_apt}-{s.f_cie}-{s.f_mois[0]}{s.f_mois[1]}-{s.f_heures[0]}{s.f_heures[1]}-{s.get('v_filtres', 0)}"


@dataclass
class Filtres:
    apt: str | None
    cie: str | None
    mois: tuple
    heures: tuple

    @property
    def actif(self):
        return bool(self.apt or self.cie or self.mois != (1, 12) or self.heures != (0, 23))

    def libelle(self, noms_cie: dict) -> str:
        parts = [self.apt or "Tous les aéroports", noms_cie.get(self.cie, "toutes compagnies")]
        if self.mois != (1, 12):
            parts.append(MOIS[self.mois[0] - 1] if self.mois[0] == self.mois[1] else f"{MOIS[self.mois[0] - 1]} – {MOIS[self.mois[1] - 1]}")
        if self.heures != (0, 23):
            parts.append(f"{self.heures[0]} h" if self.heures[0] == self.heures[1] else f"{self.heures[0]} h – {self.heures[1]} h")
        return " · ".join(parts)


@st.cache_data
def _options(df: pd.DataFrame):
    apts = (df.dropna(subset=["origin_airport"]).groupby(["origin_airport", "origin_city"], as_index=False)["n_vols"].sum()
              .query("n_vols >= 1000").sort_values("n_vols", ascending=False))
    cies = df.groupby(["airline", "airline_name"], as_index=False)["n_vols"].sum().sort_values("airline_name")
    return dict(zip(apts["origin_airport"], apts["origin_city"])), dict(zip(cies["airline"], cies["airline_name"]))


def barre_filtres(df: pd.DataFrame) -> Filtres:
    apts, cies = _options(df)
    s = st.session_state
    f = Filtres(None if s.f_apt == "Tous" else s.f_apt, None if s.f_cie == "Toutes" else s.f_cie,
                tuple(s.f_mois), tuple(s.f_heures))
    choix_apt, choix_cie = ["Tous"] + list(apts), ["Toutes"] + list(cies)
    v = s.get("v_filtres", 0)
    with st.container(key="barre"):
        st.markdown(f"<div class='barre-titre'>✈ Votre vol <span>{f.libelle(cies)}</span></div>", unsafe_allow_html=True)
        c = st.columns([1.3, 1.3, 1.5, 1.5, 0.32], vertical_alignment="bottom", gap="medium")
        c[0].selectbox("Aéroport de départ", choix_apt, index=choix_apt.index(s.f_apt) if s.f_apt in choix_apt else 0,
                       key=f"w_apt_{v}", on_change=_copier, args=("f_apt", f"w_apt_{v}"),
                       format_func=lambda a: "Tous les aéroports" if a == "Tous" else f"{a} · {apts[a]}")
        c[1].selectbox("Compagnie", choix_cie, index=choix_cie.index(s.f_cie) if s.f_cie in choix_cie else 0,
                       key=f"w_cie_{v}", on_change=_copier, args=("f_cie", f"w_cie_{v}"),
                       format_func=lambda a: "Toutes les compagnies" if a == "Toutes" else cies[a])
        c[2].select_slider("Mois", options=list(range(1, 13)), value=tuple(s.f_mois), key=f"w_mois_{v}",
                           on_change=_copier, args=("f_mois", f"w_mois_{v}"), format_func=lambda m: MOIS[m - 1])
        c[3].select_slider("Heure de départ", options=list(range(24)), value=tuple(s.f_heures), key=f"w_heures_{v}",
                           on_change=_copier, args=("f_heures", f"w_heures_{v}"), format_func=lambda h: f"{h} h")
        c[4].button("", icon=":material/restart_alt:", on_click=_reinitialiser, help="Effacer les filtres", width="stretch")
    return f


def _appliquer_filtre(champ: str, valeur, libelle: str):
    """Remplit (ou vide, si déjà choisi) un champ de « Votre vol » depuis un clic sur un graphique."""
    cle = "f_" + champ
    if st.session_state.get(cle) == valeur:
        valeur, libelle = CLES[cle], f"{libelle} retiré de votre vol"
    else:
        libelle = f"{libelle} ajouté à votre vol"
    st.session_state[cle] = valeur
    _nouvelle_version()
    st.toast(libelle, icon=":material/flight_takeoff:")


def clic(champ: str, cle: str, libelle=lambda v: str(v)):
    """Callback de clic Plotly : la 1re valeur de customdata du point cliqué devient le filtre `champ`."""
    def rappel():
        points = st.session_state[cle]["selection"]["points"]
        if not points:
            return
        cd = points[0].get("customdata")
        if isinstance(cd, dict):  # tableau numérique encodé par Plotly
            cd = [cd[k] for k in sorted(cd, key=lambda k: int(k) if str(k).isdigit() else 0)]
        if cd is None or cd == []:
            return
        v = cd[0] if isinstance(cd, list) else cd
        if champ in ("mois", "heures"):
            v = tuple(int(x) for x in str(v).split("-")) if "-" in str(v) else (int(v), int(v))
        _appliquer_filtre(champ, v, libelle(v))
    return rappel


TROP_PEU = f"Pas assez de vols dans cette sélection (moins de {MIN_VOLS} par groupe) : élargissez les filtres."


def assez(df, f) -> bool:
    """Arrête la page avec un message si la sélection ne contient aucun vol arrivé."""
    if totaux(filtrer(df, f))["arrives"] > 0:
        return True
    st.info("Aucun vol ne correspond à cette sélection (par exemple une compagnie qui ne dessert pas cet aéroport, "
            "ou octobre avec un aéroport choisi). Élargissez les filtres.", icon=":material/flight:")
    return False


def noms_compagnies(df) -> dict:
    return _options(df)[1]


def filtrer(df: pd.DataFrame, f: Filtres, sauf=()) -> pd.DataFrame:
    """Applique les filtres, sauf ceux de `sauf` (pour comparer une sélection à son contexte)."""
    m = pd.Series(True, index=df.index)
    if f.apt and "apt" not in sauf:
        m &= df["origin_airport"] == f.apt
    if f.cie and "cie" not in sauf:
        m &= df["airline"] == f.cie
    if "mois" not in sauf:
        m &= df["month"].between(*f.mois)
    if "heures" not in sauf:
        m &= df["dep_hour"].between(*f.heures)
    return df[m]


def totaux(df: pd.DataFrame) -> dict:
    s = df[["n_vols", "n_annules", "n_arrives", "n_retards", "minutes_retard"]].sum()
    return {"vols": s.n_vols, "arrives": s.n_arrives,
            "retard": 100 * s.n_retards / s.n_arrives if s.n_arrives else float("nan"),
            "annul": 100 * s.n_annules / s.n_vols if s.n_vols else float("nan")}


def par(df: pd.DataFrame, cles) -> pd.DataFrame:
    """Effectifs sommés par groupe, puis taux recalculés."""
    g = df.groupby(cles, as_index=False)[["n_vols", "n_annules", "n_arrives", "n_retards", "minutes_retard"]].sum()
    g["taux_retard"] = 100 * g["n_retards"] / g["n_arrives"].where(g["n_arrives"] > 0)
    g["taux_annul"] = 100 * g["n_annules"] / g["n_vols"]
    return g
