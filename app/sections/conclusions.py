"""Onglet « Ce qu'il faut retenir » : tests statistiques (table Gold stats_tests, J4) et synthèse du projet."""

import pandas as pd
import streamlit as st

FACTEURS = [
    ("1", "L'heure de départ", "7 % de vols en retard à 5 h, 27 % vers 20 h : les retards se propagent d'un vol à l'autre au fil de la journée.", "#E76F51"),
    ("2", "La compagnie", "De 12,5 % (Hawaiian) à 30 % (Spirit). Les low-cost Spirit et Frontier sont les moins ponctuelles.", "#F4A261"),
    ("3", "La saison", "Pics en février et juin (environ 24 %), creux en septembre et octobre (environ 13 %).", "#E9C46A"),
    ("4", "L'aéroport", "Les grands hubs congestionnés (Chicago, Dallas, Denver...) sont les plus à risque ; Atlanta reste fiable.", "#2A9D8F"),
]


def render(load_gold):
    st.subheader("Ce qui rend un vol à risque")
    cols = st.columns(len(FACTEURS))
    for col, (num, titre, texte, couleur) in zip(cols, FACTEURS):
        col.markdown(
            f"<div style='background:white;border-radius:18px;padding:1.1rem 1.2rem;height:100%;"
            f"box-shadow:0 2px 14px rgba(38,70,83,.06)'>"
            f"<div style='display:inline-grid;place-items:center;width:34px;height:34px;border-radius:50%;"
            f"background:{couleur};color:white;font:700 1rem Poppins,sans-serif'>{num}</div>"
            f"<div style='font:600 1.05rem Poppins,sans-serif;margin:0.6rem 0 0.3rem'>{titre}</div>"
            f"<div style='font-size:0.9rem;line-height:1.45'>{texte}</div></div>", unsafe_allow_html=True)
    st.write("")
    st.markdown(
        "**Notre conseil au voyageur** : réserver un vol tôt le matin, éviter les correspondances dans les grands hubs "
        "en fin de journée, et préférer une compagnie ponctuelle (Delta, Alaska, Hawaiian). La distance du vol, elle, "
        "ne change rien au risque.")

    tests = load_gold("stats_tests")
    if tests is not None:
        st.subheader("Ce que disent les tests statistiques")
        vue = pd.DataFrame({
            "Test": tests["test"],
            "Question": tests["question"],
            "p-value": tests["p_value"].map(lambda p: "< 10⁻³⁰⁰" if p == 0 else f"{p:.2g}"),
            "Taille d'effet": [f"{m} = {v:.3f}" for m, v in zip(tests["mesure_effet"], tests["taille_effet"])],
            "H₀ rejetée": tests["h0_rejetee"].map({True: "Oui", False: "Non"}),
            "Conclusion": tests["conclusion"],
        })
        st.dataframe(vue, hide_index=True, width="stretch")
        with st.expander("Pourquoi une taille d'effet en plus de la p-value ?"):
            st.markdown(
                "Avec des dizaines de milliers de vols, la moindre différence devient « statistiquement significative ». "
                "La p-value dit seulement si un écart existe ; la **taille d'effet** dit s'il compte. Exemple : la distance "
                "a un lien significatif avec le retard (p ≈ 10⁻¹⁹), mais elle n'explique que 0,6 % de sa variance. "
                "Tous les tests sont **non paramétriques** (Mann-Whitney, Kruskal-Wallis, Spearman) car le retard est "
                "très asymétrique (skewness ≈ 6,5).")

    st.subheader("Limites")
    st.markdown(
        "- Les analyses portent sur un **échantillon de 5 %** des vols de 2015 (environ 290 000 vols).\n"
        "- En **octobre**, les codes aéroport du dataset ne sont pas des codes IATA : ce mois est exclu des analyses par aéroport.\n"
        "- **Retard et annulation** sont deux réponses différentes à une perturbation : le jour du blizzard du 27 janvier, "
        "19 % des vols ont été annulés mais seulement 6 % sont arrivés en retard.")
