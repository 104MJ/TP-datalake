"""Page « À retenir » : les quatre facteurs du retard et les tests statistiques (tables Gold risque_retard, stats_tests)."""

import streamlit as st

from sections import donnees as d
from sections.theme import entete, fr, pct, titre

CONSEILS = [
    ("wb_twilight", "Partez tôt", "Avant 8 h, moins d'un vol sur dix arrive en retard ; après 17 h, un sur quatre."),
    ("airlines", "Choisissez la compagnie", "Hawaiian, Alaska et Delta sont deux fois plus ponctuelles que Spirit ou Frontier."),
    ("connecting_airports", "Évitez les correspondances du soir", "Dans les grands hubs, les retards s'enchaînent au fil de la journée."),
]


def puissance(p: float) -> str:
    m, e = f"{p:.0e}".split("e")
    return f"p ≈ {m}·10" + str(int(e)).translate(str.maketrans("-0123456789", "⁻⁰¹²³⁴⁵⁶⁷⁸⁹"))


def facteurs(r):
    h = d.par(r, "dep_hour").query("dep_hour >= 5").sort_values("dep_hour")
    c = d.par(r, "airline").sort_values("taux_retard")
    m = d.par(r, "month").sort_values("month")
    a = d.par(r.dropna(subset=["origin_airport"]), "origin_airport").query("n_vols >= 1000").sort_values("taux_retard")
    cols = st.columns(4)
    for col, (rang, nom, g, type_) in zip(cols, [(1, "L'heure de départ", h, "line"), (2, "La compagnie", c, "bar"),
                                                  (3, "Le mois", m, "line"), (4, "L'aéroport", a, "bar")]):
        lo, hi = g["taux_retard"].min(), g["taux_retard"].max()
        col.metric(f"{rang} · {nom}", f"×{fr(hi / lo, 1)}", f"de {pct(lo, 0)} à {pct(hi, 0)} de retard", delta_color="off",
                   delta_arrow="off", border=True, height=200, chart_type=type_, chart_data=g["taux_retard"].round(1).tolist(),
                   help="Écart entre le groupe le plus ponctuel et le plus en retard.")


def render():
    r, tests = d.risque(), d.gold("stats_tests")
    if r is None:
        return
    entete("Arrivée", "Ce qu'il faut retenir : quatre facteurs connus avant de réserver", etape=6)
    facteurs(r)

    c1, c2 = st.columns([1.5, 1], gap="medium")
    with c1.container(border=True):
        titre("Ce que disent les tests statistiques", "Sur 5,7 M de vols, tout écart est significatif : la taille d'effet dit s'il compte")
        if tests is not None:
            html = ""
            for t in tests.itertuples():
                p = "p < 10⁻³⁰⁰" if t.p_value == 0 else puissance(t.p_value)
                html += (f"<div class='test'><div><b>{t.test}</b><div class='q'>{t.question}</div></div>"
                         f"<div><small>{t.mesure_effet} = {fr(abs(t.taille_effet), 3)} · {p}</small>"
                         f"<div class='jauge'><div style='width:{min(100 * abs(t.taille_effet) / 0.15, 100):.0f}%'></div></div></div>"
                         f"<div class='c'>{t.conclusion}</div></div>")
            st.markdown(html, unsafe_allow_html=True)
        with st.expander("Requête SQL & justification", icon=":material/code:"):
            st.caption("Tests non paramétriques (retard très asymétrique, skewness 6,5) et χ² pour les catégories. "
                       "Table Gold stats_tests (J4).")
    with c2.container(border=True):
        titre("Nos conseils au voyageur")
        st.markdown("".join(f"<div class='conseil'><span class='material'>{i}</span><div><b>{t}</b><br>{x}</div></div>"
                            for i, t, x in CONSEILS), unsafe_allow_html=True)
        with st.expander("Limites", icon=":material/info:"):
            st.caption("Octobre exclu des analyses par aéroport (codes non IATA). Retard et annulation sont deux réponses "
                       "différentes : le 27 janvier, 19 % d'annulations mais 7 % de retards.")
