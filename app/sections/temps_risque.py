"""Page « Quand partir » : heure et mois de départ (tables Gold risque_retard et retards_mensuels)."""

import numpy as np
import plotly.graph_objects as go
import streamlit as st

from sections import donnees as d
from sections.theme import (BLUE, ECHELLE, GRAY, INK, MOIS, MUTED, ORANGE, entete, graphique, mise_en_forme, pct,
                            titre)

CRENEAUX = [("Nuit", 0, 5), ("Matin", 6, 11), ("Après-midi", 12, 16), ("Soir", 17, 23)]

SQL_MENSUEL = ("WITH mensuel AS (\n"
               "  SELECT DATE_TRUNC('MONTH', flight_date) AS periode,\n"
               "         100.0 * AVG(CAST(is_delayed_15 AS INT)) AS taux_retard_15_pct\n"
               "  FROM v_silver GROUP BY 1)\n"
               "SELECT *, taux_retard_15_pct - LAG(taux_retard_15_pct) OVER (ORDER BY periode) AS variation_pts,\n"
               "       AVG(taux_retard_15_pct) OVER (ORDER BY periode ROWS BETWEEN 2 PRECEDING AND CURRENT ROW)\n"
               "         AS moyenne_3_mois\nFROM mensuel   -- table Gold retards_mensuels (J3 §3)")


def mensuel(r, f):
    """Série mensuelle : la table Gold retards_mensuels sans filtre, recalculée sur la sélection sinon."""
    if not (f.apt or f.cie or f.heures != (0, 23)):
        g = d.gold("retards_mensuels")
        if g is not None:
            return g.rename(columns={"mois": "month", "taux_retard_15_pct": "taux_retard",
                                     "taux_retard_moyenne_3_mois_pct": "moy3",
                                     "variation_taux_retard_pts": "variation"}).sort_values("month")
    g = d.par(d.filtrer(r, f, sauf=("mois",)), "month").sort_values("month")
    g["moy3"] = g["taux_retard"].rolling(3, min_periods=1).mean()
    g["variation"] = g["taux_retard"].diff()
    return g


def carte_chaleur(r, f):
    g = d.par(d.filtrer(r, f, sauf=("mois", "heures")), ["dep_hour", "month"]).query("dep_hour >= 5")
    g.loc[g["n_arrives"] < 50, "taux_retard"] = np.nan
    z = g.pivot(index="dep_hour", columns="month", values="taux_retard").reindex(index=range(5, 24), columns=range(1, 13))
    n = g.pivot(index="dep_hour", columns="month", values="n_arrives").reindex(index=range(5, 24), columns=range(1, 13))
    if z.isna().all().all():
        return st.caption(d.TROP_PEU)
    fig = go.Figure(go.Heatmap(z=z.values, x=MOIS, y=[f"{h} h" for h in z.index], colorscale=ECHELLE, xgap=2, ygap=2,
                               customdata=n.fillna(0).values, zmin=np.nanpercentile(z.values, 3), zmax=np.nanpercentile(z.values, 97),
                               hovertemplate="%{x}, départ %{y} : <b>%{z:.1f} %</b> de retard<br>%{customdata:,.0f} vols<extra></extra>",
                               colorbar={"thickness": 8, "len": 0.6, "ticksuffix": " %", "outlinewidth": 0,
                                         "tickfont": {"size": 10, "color": MUTED}}))
    if f.mois != (1, 12) or f.heures != (0, 23):
        h0, h1 = max(f.heures[0], 5), f.heures[1]
        fig.add_shape(type="rect", x0=f.mois[0] - 1.5, x1=f.mois[1] - 0.5, y0=h0 - 5.5, y1=h1 - 4.5,
                      line={"color": INK, "width": 2})
    fig.update_yaxes(autorange="reversed", gridcolor="rgba(0,0,0,0)")
    fig.update_xaxes(gridcolor="rgba(0,0,0,0)", side="top")
    graphique(mise_en_forme(fig, 430), key="chaleur")


def carte_creneaux(r, f):
    sel = d.filtrer(r, f, sauf=("heures",))
    lignes = []
    for nom, a, b in CRENEAUX:
        t = d.totaux(sel[sel["dep_hour"].between(a, b)])
        lignes.append((f"{nom} ({a} h – {b} h)", t["retard"], t["vols"], not (b < f.heures[0] or a > f.heures[1]), f"{a}-{b}"))
    fig = go.Figure(go.Bar(y=[l[0] for l in lignes][::-1], x=[l[1] for l in lignes][::-1], orientation="h",
                           marker_color=[ORANGE if l[3] else GRAY for l in lignes][::-1],
                           customdata=[[l[4], l[2]] for l in lignes][::-1], width=0.5,
                           hovertemplate="%{y} : <b>%{x:.1f} %</b> de retard<br>%{customdata[1]:,.0f} vols<extra></extra>"))
    for l in lignes:
        fig.add_annotation(x=l[1], y=l[0], text=f"<b>{pct(l[1], 0)}</b>", showarrow=False, xanchor="left", xshift=6,
                           font={"color": INK, "size": 13})
    fig.update_xaxes(ticksuffix=" %", range=[0, max(l[1] for l in lignes) * 1.25])
    fig.update_yaxes(gridcolor="rgba(0,0,0,0)")
    cle = f"creneaux_{d.signature()}"
    graphique(mise_en_forme(fig, 250), key=cle, clic=d.clic("heures", cle, lambda v: f"{v[0]} h" if v[0] == v[1] else f"{v[0]} h – {v[1]} h"))
    soir, matin = lignes[3][1], lignes[1][1]
    st.markdown(f"<div class='chiffre-cle'><b>×{(soir / matin):.1f}</b>".replace(".", ",")
                + " de risque entre un départ le soir et un départ le matin</div>", unsafe_allow_html=True)


def carte_tendance(g, f):
    dans = g["month"].between(*f.mois)
    fig = go.Figure()
    fig.add_bar(x=[MOIS[m - 1] for m in g["month"]], y=g["taux_retard"], name="Taux du mois",
                marker_color=np.where(dans, ORANGE, GRAY), customdata=[[int(m)] for m in g["month"]],
                hovertemplate="%{x} : <b>%{y:.1f} %</b><extra>Taux du mois</extra>")
    fig.add_scatter(x=[MOIS[m - 1] for m in g["month"]], y=g["moy3"], name="Moyenne glissante sur 3 mois", mode="lines",
                    line={"color": INK, "width": 2}, hovertemplate="%{x} : %{y:.1f} %<extra>Moyenne sur 3 mois</extra>")
    fig.update_yaxes(ticksuffix=" %", rangemode="tozero")
    cle = f"tendance_{d.signature()}"
    graphique(mise_en_forme(fig, 280, legende=True), key=cle, clic=d.clic("mois", cle, lambda m: MOIS[m[0] - 1]))


def carte_variation(g):
    v = g.dropna(subset=["variation"])
    fig = go.Figure(go.Bar(x=[MOIS[m - 1] for m in v["month"]], y=v["variation"],
                           marker_color=np.where(v["variation"] > 0, ORANGE, BLUE),
                           hovertemplate="%{x} : <b>%{y:+.1f} points</b> par rapport au mois précédent<extra></extra>"))
    fig.add_hline(y=0, line_color=MUTED, line_width=1)
    fig.update_yaxes(ticksuffix=" pts")
    graphique(mise_en_forme(fig, 280), key="variation")


def render():
    r = d.risque()
    if r is None:
        return
    entete("Étape 1 · Le départ", "Partir tôt le matin réduit fortement le risque", etape=1)
    f = d.barre_filtres(r)
    if not d.assez(r, f):
        return

    c1, c2 = st.columns([1.55, 1], gap="medium")
    with c1.container(border=True):
        titre("Le soir et l'été cumulent les retards", "Part des vols arrivés en retard, par heure de départ et par mois")
        carte_chaleur(r, f)
        with st.expander("Requête SQL & justification", icon=":material/code:"):
            st.code("SELECT dep_hour, month, SUM(n_retards) / SUM(n_arrives) AS taux_retard\n"
                    "FROM risque_retard GROUP BY dep_hour, month", language="sql")
            st.caption("Cases de moins de 50 vols laissées vides. Couleur bornée aux centiles 3 et 97.")
    with c2.container(border=True):
        titre("Le créneau compte plus que le mois", "Part des vols arrivés en retard selon le moment de la journée · cliquez pour choisir")
        carte_creneaux(r, f)
        with st.expander("Requête SQL & justification", icon=":material/code:"):
            st.caption("Test du χ² créneau × retard (J4) : lien significatif, V de Cramér = 0,13, le plus fort effet des tests.")

    g = mensuel(r, f)
    c3, c4 = st.columns(2, gap="medium")
    with c3.container(border=True):
        titre("Deux pics : février et juin", "Taux de retard du mois et moyenne glissante sur 3 mois · cliquez un mois")
        carte_tendance(g, f)
        with st.expander("Requête SQL & justification", icon=":material/code:"):
            st.code(SQL_MENSUEL, language="sql")
            st.caption("Un taux, pas un total de minutes, qui grossit avec le nombre de vols du mois.")
    with c4.container(border=True):
        titre("La rentrée fait chuter le retard", "Variation du taux de retard par rapport au mois précédent (LAG)")
        carte_variation(g)
        with st.expander("Requête SQL & justification", icon=":material/code:"):
            st.code(SQL_MENSUEL, language="sql")
            st.caption("En orange, les mois où le retard augmente ; en bleu, ceux où il baisse.")
