"""Onglet « Saisonnalité & risque de retard » : Personne B (tables Gold : monthly_trend, delay_risk)."""

import plotly.express as px  # noqa: F401
import streamlit as st


def render(load_gold):
    st.header("Quand les vols sont-ils en retard, et quel est mon risque ?")

    trend = load_gold("monthly_trend")
    if trend is not None:
        # TODO (Personne B) : courbe mensuelle du taux de retard (px.line) avec la moyenne glissante
        # sur 3 mois, et barres de l'évolution d'un mois sur l'autre (evolution_pts, issue de LAG).
        st.dataframe(trend, hide_index=True)

    risk = load_gold("delay_risk")
    if risk is not None:
        # TODO (Personne B) : simulateur voyageur.
        # - Filtres : st.selectbox compagnie, aéroport de départ, mois, créneau (dep_slot), chacun avec « Tous ».
        # - Taux de retard du filtre = sum(n_retards) / sum(n_vols) sur les lignes filtrées (pas la moyenne des taux !).
        # - Afficher le taux, le nombre de vols servant au calcul, et un avertissement si n_vols < 100.
        # - Comparer au taux global (st.metric avec delta).
        # - st.expander("Requête SQL & justification statistique") + rappel du test du χ² créneau × retard (J4).
        st.dataframe(risk.head(50), hide_index=True)
