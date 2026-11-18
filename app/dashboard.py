"""Dashboard Streamlit : retards des vols aériens (couche Gold du lakehouse).

Ce fichier ne contient que la structure commune. Chaque onglet est codé dans
son propre module de `app/sections/` (un fichier par personne, pas de conflit git).
Le dashboard ne lit que des tables de `/lakehouse/gold/`, jamais Silver ni les CSV.
"""

import streamlit as st
from pyspark.sql import SparkSession

from sections import aeroports, compagnies, temps_risque

st.set_page_config(page_title="Retards des vols 2015", layout="wide")
st.title("Retards des vols aériens aux États-Unis (2015)")


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

tab_risque, tab_compagnies, tab_aeroports = st.tabs(
    ["Saisonnalité & risque de retard", "Compagnies", "Aéroports"]
)
with tab_risque:
    temps_risque.render(load_gold)
with tab_compagnies:
    compagnies.render(load_gold)
with tab_aeroports:
    aeroports.render(load_gold)
