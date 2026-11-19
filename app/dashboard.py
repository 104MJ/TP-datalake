"""Dashboard Streamlit : retards des vols intérieurs américains de 2015 (couche Gold du lakehouse).

Ne lit que des tables de /lakehouse/gold/. Une page par étape du voyage, une barre « Votre vol » commune.
Thème : app/.streamlit/config.toml.
"""

from pathlib import Path

import streamlit as st

from sections import accueil, aeroports, ciel_3d, compagnies, conclusions, donnees, mon_vol, temps_risque, theme

st.set_page_config(page_title="Retards aériens 2015", page_icon="✈", layout="wide")
st.logo(str(Path(__file__).with_name("assets") / "logo.svg"), size="large")
with st.container(key="mode"):
    st.toggle("Vol de nuit", key="nuit", help="Thème sombre")
theme.appliquer()
donnees.conserver_filtres()

pages = [
    st.Page(accueil.render, title="Vue d'ensemble", icon=":material/flight_takeoff:", url_path="accueil", default=True),
    st.Page(temps_risque.render, title="Quand partir", icon=":material/schedule:", url_path="quand"),
    st.Page(compagnies.render, title="Compagnies", icon=":material/airlines:", url_path="compagnies"),
    st.Page(aeroports.render, title="Aéroports", icon=":material/location_on:", url_path="aeroports"),
    st.Page(ciel_3d.render, title="Le ciel en 3D", icon=":material/public:", url_path="ciel"),
    st.Page(mon_vol.render, title="Mon vol", icon=":material/confirmation_number:", url_path="mon-vol"),
    st.Page(conclusions.render, title="À retenir", icon=":material/flight_land:", url_path="retenir"),
]
st.navigation(pages, position="top").run()
