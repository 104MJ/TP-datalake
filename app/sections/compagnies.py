"""Onglet « Compagnies » — Personne A (tables Gold : airline_ranking)."""

import plotly.express as px  # noqa: F401
import streamlit as st


def render(load_gold):
    st.header("Les compagnies se valent-elles ?")
    df = load_gold("airline_ranking")
    if df is None:
        return

    # TODO (Personne A) :
    # 1. Barres horizontales du taux de retard par compagnie, triées par rang (px.bar, orientation="h").
    # 2. Courbe de Pareto : part cumulée des vols en retard (part_cumulee_retards) par compagnie.
    # 3. Rappel du test de Kruskal-Wallis (J4) : statistique, p-value et conclusion en une phrase.
    # 4. st.expander("Requête SQL & justification statistique") avec la requête J3 et le choix médiane/IQR.
    st.dataframe(df, hide_index=True)
