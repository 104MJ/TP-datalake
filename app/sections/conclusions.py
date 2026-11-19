"""Onglet « Conclusions & tests » : Personne A (tables Gold : stats_tests, + synthèse de toutes les autres)."""

import streamlit as st


def render(load_gold):
    st.header("Conclusions : ce qui rend un vol à risque")
    tests = load_gold("stats_tests")
    if tests is not None:
        # TODO (Personne A) :
        # 1. Tableau des tests (theme, test, H0, statistique, p-value, taille d'effet, conclusion), p-value en notation
        #    scientifique et colonne « H0 rejetée ? » (p < 0,05).
        # 2. Rappeler sous le tableau la différence entre significativité (p-value) et importance (taille d'effet).
        st.dataframe(tests, hide_index=True)

    # TODO (Personne A) : synthèse exécutive en 4-5 phrases (comme la conclusion de J2 et le notebook 05 de l'exemple
    # du prof) : facteurs du retard classés, profils d'aéroports, conseils au voyageur, limites (échantillon de 5 %,
    # octobre sans codes aéroport, retard ≠ annulation).
