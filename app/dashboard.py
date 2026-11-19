"""Dashboard Streamlit : retards des vols aériens (couche Gold du lakehouse).

Ce fichier ne contient que la structure commune. Chaque onglet est codé dans
son propre module de `app/sections/` (un fichier par personne, pas de conflit git).
Le dashboard ne lit que des tables de `/lakehouse/gold/`, jamais Silver ni les CSV.
"""

import streamlit as st
from pyspark.sql import SparkSession

from sections import aeroports, ciel_3d, compagnies, conclusions, temps_risque

st.set_page_config(page_title="Retards des vols 2015", page_icon="✈️", layout="wide")
st.markdown(
    """
    <style>
    .hero-banner {
        background: linear-gradient(135deg, #070b19 0%, #0c2340 55%, #0f172a 100%);
        border: 1px solid rgba(56, 189, 248, 0.35); border-radius: 16px;
        padding: 1.3rem 1.8rem; margin-bottom: 1rem; color: #f8fafc;
        box-shadow: 0 10px 28px rgba(15, 23, 42, 0.28);
    }
    .hero-banner h1 {
        margin: 0 0 0.35rem 0; font-size: 1.9rem;
        background: linear-gradient(90deg, #e0f2fe, #38bdf8, #f59e0b);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    }
    .hero-sub { color: #cbd5e1; font-size: 0.95rem; margin: 0; }
    </style>
    <div class="hero-banner">
        <h1>✈️ Retards aériens aux États-Unis — 2015</h1>
        <p class="hero-sub">
            Lakehouse <b>HDFS 3.5 (3 DataNodes)</b> • <b>PySpark 4.2</b> • <b>Delta Lake 4.4 (Bronze → Silver → Gold)</b> •
            Qu'est-ce qui fait qu'un vol arrive en retard, et peut-on repérer à l'avance les vols à risque ?
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource
def get_spark():
    return (
        SparkSession.builder
        .appName("StreamlitGoldReader")
        .config("spark.driver.memory", "512m")
        .config("spark.ui.enabled", "false")
        .getOrCreate()
    )


@st.cache_data(ttl=60)
def _read_gold(name: str):
    return get_spark().read.format("delta").load(f"/lakehouse/gold/{name}").toPandas()


def load_gold(name: str):
    """Charge /lakehouse/gold/<name> en pandas, ou None (avec un avertissement) si la table n'existe pas encore."""
    try:
        return _read_gold(name)
    except Exception as exc:  # table pas encore créée par le notebook J3/J4
        st.warning(f"Table `/lakehouse/gold/{name}` indisponible : exécutez d'abord le notebook qui la crée. ({type(exc).__name__})")
        return None


st.caption(
    "Problématique : qu'est-ce qui fait qu'un vol arrive en retard, et peut-on repérer à l'avance les vols à risque ? "
    "Indicateur : taux de vols arrivés avec 15 min de retard ou plus (médiane et IQR en complément)."
)

tab_ciel, tab_risque, tab_compagnies, tab_aeroports, tab_conclusions = st.tabs(
    ["✈️ Ciel 3D", "🕒 Saisonnalité & risque de retard", "🏢 Compagnies", "🗺️ Aéroports", "📜 Conclusions & tests"]
)
with tab_ciel:
    ciel_3d.render(load_gold)
with tab_risque:
    temps_risque.render(load_gold)
with tab_compagnies:
    compagnies.render(load_gold)
with tab_aeroports:
    aeroports.render(load_gold)
with tab_conclusions:
    conclusions.render(load_gold)
