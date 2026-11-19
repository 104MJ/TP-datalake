"""Onglet « Aéroports » : Personne C (tables Gold : airport_profile, airport_segments)."""

import plotly.express as px  # noqa: F401
import streamlit as st


def render(load_gold):
    st.header("Les aéroports ont-ils des profils différents ?")

    profile = load_gold("airport_profile")
    if profile is not None:
        # TODO (Personne C) : carte des aéroports (px.scatter_geo, scope="usa", taille = n_vols,
        # couleur = taux_retard) et tableau « meilleure compagnie au départ de chaque aéroport ».
        st.dataframe(profile, hide_index=True)

    segments = load_gold("airport_segments")
    if segments is not None:
        # TODO (Personne C) : filtre st.multiselect sur les segments, carte colorée par segment,
        # tableau des médianes par segment, et description en une phrase de chaque segment.
        # st.expander("Méthode") : variables, log1p + StandardScaler, choix de k (coude / silhouette).
        st.dataframe(segments, hide_index=True)
