"""Dashboard Streamlit : retards des vols aériens (couche Gold du lakehouse).

Ce fichier ne contient que la structure commune (style, chargement des tables, onglets).
Chaque onglet est codé dans son propre module de `app/sections/` (un fichier par personne, pas de conflit git).
Le dashboard ne lit que des tables de `/lakehouse/gold/`, jamais Silver ni les CSV.
"""

import streamlit as st
from pyspark.sql import SparkSession
from streamlit import config as st_config

# Thème clair et couleur principale du dashboard (le conteneur ne monte que app/, pas de .streamlit/config.toml)
for option, valeur in {"theme.base": "light", "theme.primaryColor": "#2A9D8F", "theme.backgroundColor": "#F7F4EF",
                       "theme.secondaryBackgroundColor": "#FFFFFF", "theme.textColor": "#264653"}.items():
    st_config.set_option(option, valeur)

from sections import aeroports, ciel_3d, compagnies, conclusions, temps_risque

st.set_page_config(page_title="Pourquoi mon vol est-il en retard ?", layout="wide")

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@500;600;700&family=DM+Sans:wght@400;500;700&display=swap');

    :root {
        --ink: #264653; --muted: #6b7785; --paper: #F7F4EF; --card: #FFFFFF; --line: #ECE5DA;
        --teal: #2A9D8F; --sand: #E9C46A; --orange: #F4A261; --coral: #E76F51;
    }
    .stApp { background: var(--paper); color: var(--ink); }
    /* Police du texte : on vise les éléments de texte, jamais les span (les icônes Streamlit sont des span
       en police Material Symbols : leur changer de police les fait apparaître en toutes lettres). */
    .stApp :is(p, li, label, input, textarea, button, td, th, [data-testid="stMetricValue"] div) {
        font-family: 'DM Sans', sans-serif; }
    .stApp :is(p, li, label) { color: var(--ink); }
    .stApp :is(h1, h2, h3) { font-family: 'Poppins', sans-serif !important; color: var(--ink); letter-spacing: -0.015em; }
    .stApp h3 { font-size: 1.45rem; margin-top: 0.6rem; }
    .block-container { padding-top: 2.4rem; max-width: 1280px; }
    header[data-testid="stHeader"] { background: transparent; }

    /* En-tête : texte à gauche, chiffres clés à droite */
    .hero { display: grid; grid-template-columns: 1.25fr 1fr; gap: 1.6rem; align-items: center;
            background: var(--card); border-radius: 24px; padding: 2rem 2.2rem; margin-bottom: 1.6rem;
            box-shadow: 0 4px 24px rgba(38, 70, 83, 0.07); }
    .hero .kicker { font: 700 0.78rem 'DM Sans', sans-serif; letter-spacing: 0.14em; text-transform: uppercase;
                    color: var(--coral); margin: 0 0 0.6rem 0; }
    .hero h1 { font-size: 2.6rem; font-weight: 700; margin: 0; padding: 0; line-height: 1.1; }
    .hero .lead { color: var(--muted); font-size: 1.05rem; line-height: 1.55; margin: 0.8rem 0 1rem 0; }
    .chip { display: inline-block; padding: 0.28rem 0.85rem; border-radius: 999px; font: 700 0.8rem 'DM Sans', sans-serif;
            margin: 0 0.35rem 0.3rem 0; }
    .chip.teal { background: #D9F0EC; color: #1E6F66; }
    .chip.sand { background: #FBF0D2; color: #8A6A12; }
    .chip.coral { background: #FBE1DA; color: #A6432B; }
    .chip.ink { background: #DDE6EA; color: var(--ink); }
    .stats { display: grid; gap: 0.75rem; }
    .stat { display: flex; align-items: center; gap: 1rem; border-radius: 18px; padding: 0.9rem 1.1rem; }
    .stat b { font: 700 1.9rem 'Poppins', sans-serif; min-width: 6.2rem; line-height: 1; }
    .stat span { font: 500 0.95rem 'DM Sans', sans-serif; line-height: 1.35; color: var(--ink); }
    .stat.teal { background: #E6F4F1; } .stat.teal b { color: #1E7A70; }
    .stat.sand { background: #FCF4DC; } .stat.sand b { color: #A57D10; }
    .stat.coral { background: #FCE8E2; } .stat.coral b { color: #C4532F; }
    @media (max-width: 900px) { .hero { grid-template-columns: 1fr; } .hero h1 { font-size: 2rem; } }

    /* Onglets en pastilles (Streamlit 1.67 : onglets react-aria) */
    [data-testid="stTabs"] [role="tablist"] { gap: 0.55rem; flex-wrap: wrap; padding-bottom: 0.4rem; }
    [data-testid="stTabs"] [data-orientation="horizontal"] { border-bottom: none !important; box-shadow: none !important; }
    [data-testid="stTab"] { background: var(--card); border: 1px solid var(--line); border-radius: 999px !important;
                            padding: 0.55rem 1.25rem !important; height: auto !important; transition: all 0.15s; }
    [data-testid="stTab"]:hover { border-color: var(--teal); }
    [data-testid="stTab"] p { font-weight: 600 !important; font-size: 0.95rem !important; margin: 0; }
    [data-testid="stTab"][aria-selected="true"] { background: var(--ink); border-color: var(--ink); }
    [data-testid="stTab"][aria-selected="true"] p { color: #FFFFFF !important; }
    [data-testid="stTabs"] .react-aria-SelectionIndicator { display: none !important; }

    /* Cartes */
    [data-testid="stMetric"] { background: var(--card); border-radius: 18px; padding: 1rem 1.25rem;
                               box-shadow: 0 2px 14px rgba(38, 70, 83, 0.06); border-top: 6px solid var(--teal); }
    [data-testid="stColumn"]:nth-child(2) [data-testid="stMetric"] { border-top-color: var(--sand); }
    [data-testid="stColumn"]:nth-child(3) [data-testid="stMetric"] { border-top-color: var(--coral); }
    [data-testid="stColumn"]:nth-child(4) [data-testid="stMetric"] { border-top-color: var(--orange); }
    [data-testid="stMetricLabel"] p { color: var(--muted) !important; font-weight: 500; }
    [data-testid="stMetricValue"] div { font-family: 'Poppins', sans-serif !important; font-weight: 600; color: var(--ink) !important; }
    [data-testid="stPlotlyChart"], [data-testid="stDeckGlJsonChart"], [data-testid="stIFrame"] {
        border-radius: 20px; overflow: hidden; box-shadow: 0 4px 22px rgba(38, 70, 83, 0.10); }
    [data-testid="stExpander"] details { background: var(--card); border-radius: 14px; border: 1px solid var(--line); }
    [data-testid="stCaptionContainer"] p { color: var(--muted) !important; }
    .stRadio [role="radiogroup"] { gap: 0.4rem 1.4rem; }
    </style>

    <div class="hero">
        <div>
            <p class="kicker">Projet Big Data, vols intérieurs américains de 2015</p>
            <h1>Pourquoi mon vol est-il en retard ?</h1>
            <p class="lead">L'heure de départ, la compagnie, l'aéroport et la saison pèsent tous sur le risque
            d'arriver en retard. On a suivi les données de bout en bout, des fichiers bruts sur HDFS
            jusqu'aux tables de la couche Gold, pour comprendre lesquels comptent vraiment.</p>
            <span class="chip teal">HDFS</span><span class="chip sand">PySpark</span><span class="chip coral">Delta Lake</span><span class="chip ink">Streamlit</span>
        </div>
        <div class="stats">
            <div class="stat coral"><b>18,7 %</b><span>des vols arrivent avec au moins 15 minutes de retard</span></div>
            <div class="stat sand"><b>×4</b><span>de risque entre un départ à 5 h (7 %) et un départ vers 20 h (27 %)</span></div>
            <div class="stat teal"><b>12 à 30 %</b><span>de vols en retard selon la compagnie, à heure de départ égale</span></div>
        </div>
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
    """Charge /lakehouse/gold/<name> en pandas, ou None (avec un message) si la table n'existe pas encore."""
    try:
        return _read_gold(name)
    except Exception as exc:  # table pas encore créée par le notebook J3/J4
        st.info(f"La table `{name}` n'est pas encore disponible : exécutez le notebook qui la crée. ({type(exc).__name__})")
        return None


tab_ciel, tab_risque, tab_compagnies, tab_aeroports, tab_conclusions = st.tabs(
    ["Le ciel en 3D", "Quand partir", "Les compagnies", "Les aéroports", "Ce qu'il faut retenir"]
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
