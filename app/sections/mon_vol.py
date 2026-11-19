"""Page « Mon vol » : le simulateur. Le voyageur décrit son vol, on lui donne son risque et de meilleures options
(table Gold risque_retard)."""

import plotly.graph_objects as go
import streamlit as st

from sections import donnees as d
from sections.tableau import tableau_departs
from sections.theme import GRAY, INK, MOIS, NOM_COURT, ORANGE, entete, fr, graphique, mise_en_forme, pct, titre


def _periode(f):
    m = "Toute l'année" if f.mois == (1, 12) else (MOIS[f.mois[0] - 1] if f.mois[0] == f.mois[1]
                                                   else f"{MOIS[f.mois[0] - 1]} – {MOIS[f.mois[1] - 1]}")
    h = "Toute la journée" if f.heures == (0, 23) else (f"{f.heures[0]} h" if f.heures[0] == f.heures[1]
                                                        else f"{f.heures[0]} h – {f.heures[1]} h")
    return m, h


def carte_embarquement(r, f):
    noms = d.noms_compagnies(r)
    t, ref = d.totaux(d.filtrer(r, f)), d.totaux(r)
    ratio = t["retard"] / ref["retard"]
    niveau = ("faible", "▼ Risque faible") if ratio < 0.85 else (("eleve", "▲ Risque élevé") if ratio > 1.15 else ("moyen", "● Risque moyen"))
    villes = r.dropna(subset=["origin_airport"]).drop_duplicates("origin_airport").set_index("origin_airport")["origin_city"]
    mois, heures = _periode(f)
    echelle = 40
    st.markdown(f"""
<div class="ce"><div class="ce-main">
  <div class="ce-entete"><span>Carte d'embarquement</span><b>{noms.get(f.cie, "Toutes compagnies")}</b></div>
  <div class="ce-route">
    <div><small>Départ</small><b>{f.apt or "USA"}</b><span>{villes.get(f.apt, "Tous les aéroports")}</span></div>
    <div class="ce-vol"></div>
    <div class="ce-periode"><small>Quand</small><b>{mois}</b><span>{heures}</span></div>
  </div>
  <div class="ce-risque"><small>Risque d'arriver avec 15 min de retard ou plus</small><b>{pct(t["retard"])}</b>
    <div class="ce-jauge"><div style="width:{min(100 * t["retard"] / echelle, 100):.0f}%"></div>
      <i style="left:{100 * ref["retard"] / echelle:.0f}%" title="Moyenne"></i></div>
    <div class="ce-pied">Trait noir : moyenne de tous les vols ({pct(ref["retard"])}) · calculé sur {fr(t["arrives"], 0)} vols comparables</div>
  </div>
</div><div class="ce-talon">
  <div><small>Niveau</small><span class="niveau {niveau[0]}">{niveau[1]}</span></div>
  <div><small>Annulation</small><b>{pct(t["annul"])}</b></div>
  <div><small>Par rapport à la moyenne</small><b>×{fr(ratio, 2)}</b></div>
</div></div>""", unsafe_allow_html=True)
    if t["arrives"] < d.MIN_VOLS:
        st.warning(f"Moins de {d.MIN_VOLS} vols comparables : élargissez la période ou l'heure pour un risque fiable.",
                   icon=":material/warning:")
    return t


def meilleure(r, f, dim, cle, fmt):
    g = d.par(d.filtrer(r, f, sauf=(dim,)), cle).query("n_arrives >= @d.MIN_VOLS")
    if dim == "heures":
        g = g[g["dep_hour"] >= 5]
    return None if g.empty else g.loc[g["taux_retard"].idxmin()]


def options(r, f, t):
    for dim, cle, libelle, fmt in [
            ("heures", "dep_hour", "Partir à une autre heure", lambda b: f"Départ à {int(b.dep_hour)} h"),
            ("cie", "airline", "Choisir une autre compagnie", lambda b: NOM_COURT[b.airline]),
            ("mois", "month", "Voyager un autre mois", lambda b: MOIS[int(b.month) - 1])]:
        b = meilleure(r, f, dim, cle, fmt)
        if b is not None:
            st.metric(libelle, fmt(b), f"{b.taux_retard - t['retard']:+.1f} pts : {pct(b.taux_retard)} de retard".replace(".", ",", 1),
                      delta_color="inverse", border=True)


def barres(g, x, couleurs, cle, hauteur=260, champ=None, valeurs=None, libelle=str):
    fig = go.Figure(go.Bar(x=x, y=g["taux_retard"], marker_color=couleurs,
                           customdata=[[v, int(n)] for v, n in zip(valeurs if valeurs is not None else x, g["n_arrives"])],
                           hovertemplate="%{x} : <b>%{y:.1f} %</b> de retard<br>%{customdata[1]:,} vols<extra></extra>"))
    fig.update_yaxes(ticksuffix=" %", rangemode="tozero")
    cle = f"{cle}_{d.signature()}"
    graphique(mise_en_forme(fig, hauteur), key=cle, clic=d.clic(champ, cle, libelle) if champ else None)


def render():
    r = d.risque()
    if r is None:
        return
    entete("Étape 5 · Votre vol", "Quel risque pour votre vol ?", etape=5)
    f = d.barre_filtres(r)
    if not d.assez(r, f):
        return
    c1, c2 = st.columns([1.25, 1], gap="medium")
    with c1:
        t = carte_embarquement(r, f)
        with st.container(border=True):
            titre("Et à une autre heure ?", "Même aéroport, compagnie et période ; en orange, votre créneau · cliquez pour changer")
            g = d.par(d.filtrer(r, f, sauf=("heures",)), "dep_hour").query("n_arrives >= @d.MIN_VOLS and dep_hour >= 5")
            barres(g, [f"{h} h" for h in g["dep_hour"]],
                   [ORANGE if f.heures[0] <= h <= f.heures[1] else GRAY for h in g["dep_hour"]], "mv_heures", 230,
                   champ="heures", valeurs=[int(h) for h in g["dep_hour"]], libelle=lambda v: f"{v[0]} h" if v[0] == v[1] else f"{v[0]} h – {v[1]} h")
    with c2:
        with st.container(border=True):
            titre("Pour réduire le risque", "Meilleure option en ne changeant qu'un seul critère")
            options(r, f, t)
        with st.container(border=True):
            titre("Et avec une autre compagnie ?", "Même aéroport, période et heure ; en orange, votre compagnie · cliquez pour changer")
            g = d.par(d.filtrer(r, f, sauf=("cie",)), ["airline", "airline_name"]).query("n_arrives >= @d.MIN_VOLS").sort_values("taux_retard")
            barres(g, g["airline"].map(NOM_COURT),
                   [ORANGE if (f.cie is None or a == f.cie) else GRAY for a in g["airline"]], "mv_cies", 230,
                   champ="cie", valeurs=list(g["airline"]), libelle=lambda c: NOM_COURT[c])
    routes = d.gold("route_flows")
    if routes is not None:
        villes = r.dropna(subset=["origin_airport"]).drop_duplicates("origin_airport").set_index("origin_airport")["origin_city"]
        tableau_departs(routes, d.totaux(r)["retard"], f.apt, villes.get(f.apt))
        st.caption("Statut : écart du taux de retard de la ligne à la moyenne nationale (± 3 points). Toutes compagnies, année 2015.")
    with st.expander("Requête SQL & justification", icon=":material/code:"):
        st.code("SELECT SUM(n_retards) / SUM(n_arrives) AS risque FROM risque_retard\n"
                "WHERE origin_airport = :aeroport AND airline = :compagnie\n"
                "  AND month BETWEEN :m1 AND :m2 AND dep_hour BETWEEN :h1 AND :h2", language="sql")
        st.caption(f"Le risque est la part de vols comparables arrivés en retard. En dessous de {d.MIN_VOLS} vols, il n'est pas fiable.")
