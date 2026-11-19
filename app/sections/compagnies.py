"""Page « Compagnies » : classement, Pareto et compagnies par aéroport
(tables Gold risque_retard, retards_par_compagnie, top_compagnie_retards_par_aeroport)."""

import plotly.graph_objects as go
import streamlit as st

from sections import donnees as d
from sections.theme import BLUE, GRAY, INK, MUTED, NOM_COURT, ORANGE, entete, graphique, mise_en_forme, pct, table_html, titre


def court(nom: str) -> str:
    return nom.replace(" Inc.", "").replace(" Co.", "")


def nc(codes):
    return codes.map(NOM_COURT)


def carte_classement(r, f, gold):
    g = d.par(d.filtrer(r, f, sauf=("cie",)), ["airline", "airline_name"]).query("n_arrives >= @d.MIN_VOLS")
    g = g.merge(gold[["airline", "retard_mediane_min", "iqr_retard_min", "p90_retard_min"]], on="airline", how="left")
    if g.empty:
        st.caption(d.TROP_PEU)
        return g
    g = g.sort_values("taux_retard")
    moy = d.totaux(d.filtrer(r, f, sauf=("cie",)))["retard"]
    fig = go.Figure(go.Bar(
        x=g["taux_retard"], y=nc(g["airline"]), orientation="h",
        marker_color=[ORANGE if (f.cie is None or a == f.cie) else GRAY for a in g["airline"]],
        customdata=g[["airline", "n_arrives", "retard_mediane_min", "iqr_retard_min", "p90_retard_min"]].astype(object).values.tolist(),
        hovertemplate="<b>%{y}</b> : %{x:.1f} % de retard<br>%{customdata[1]:,} vols<br>"
                      "Sur l'année : médiane %{customdata[2]} min, IQR %{customdata[3]} min, P90 %{customdata[4]} min<extra></extra>"))
    fig.add_vline(x=moy, line_color=MUTED, line_width=1)
    fig.add_annotation(x=moy, y=1.05, yref="paper", text=f"moyenne {pct(moy)}", showarrow=False, font={"size": 11, "color": MUTED})
    for row in (g[g["airline"] == f.cie] if f.cie else g.iloc[[0, -1]]).itertuples():
        fig.add_annotation(x=row.taux_retard, y=NOM_COURT[row.airline], text=f"<b>{pct(row.taux_retard)}</b>",
                           showarrow=False, xanchor="left", xshift=6, font={"color": INK, "size": 12})
    fig.update_xaxes(ticksuffix=" %", range=[0, g["taux_retard"].max() * 1.18])
    fig.update_yaxes(gridcolor="rgba(0,0,0,0)")
    cle = f"classement_{d.signature()}"
    graphique(mise_en_forme(fig, 400).update_layout(margin_t=24), key=cle, clic=d.clic("cie", cle, lambda c: NOM_COURT[c]))
    return g


def carte_pareto(r, f):
    g = d.par(d.filtrer(r, f, sauf=("cie",)), ["airline", "airline_name"]).sort_values("minutes_retard", ascending=False)
    g["cum_retard"] = 100 * g["minutes_retard"].cumsum() / g["minutes_retard"].sum()
    g["cum_vols"] = 100 * g["n_vols"].cumsum() / g["n_vols"].sum()
    x = list(range(1, len(g) + 1))
    noms = nc(g["airline"])
    fig = go.Figure()
    fig.add_scatter(x=x, y=g["cum_vols"], name="Part cumulée des vols", mode="lines", line={"color": BLUE, "width": 2},
                    customdata=noms, hovertemplate="%{customdata} : %{y:.0f} % des vols<extra></extra>")
    fig.add_scatter(x=x, y=g["cum_retard"], name="Part cumulée des minutes de retard", mode="lines+markers",
                    line={"color": ORANGE, "width": 2}, marker={"size": 8, "line": {"color": "white", "width": 2}},
                    customdata=noms, hovertemplate="%{customdata} : %{y:.0f} % des minutes de retard<extra></extra>")
    fig.add_hline(y=80, line_color=GRAY, line_width=1)
    fig.add_annotation(x=len(g), y=80, text="80 %", showarrow=False, xanchor="right", yshift=8, font={"size": 11, "color": MUTED})
    fig.update_xaxes(tickvals=x, ticktext=list(noms), tickangle=-40)
    fig.update_yaxes(ticksuffix=" %", range=[0, 103])
    graphique(mise_en_forme(fig, 400, legende=True), key="pareto")


def carte_aeroport(r, f, top):
    if f.apt:
        g = d.par(d.filtrer(r, f, sauf=("cie",)), ["airline", "airline_name"]).query("n_arrives >= @d.MIN_VOLS")
        g = g.sort_values("taux_retard", ascending=False)
        pire = g.iloc[0]["airline"] if len(g) else None
        fig = go.Figure(go.Bar(x=nc(g["airline"]), y=g["taux_retard"], width=0.55,
                               marker_color=[ORANGE if a in (pire, f.cie) else GRAY for a in g["airline"]],
                               customdata=g[["airline", "n_arrives"]].astype(object).values.tolist(),
                               hovertemplate="%{x} : <b>%{y:.1f} %</b> de retard<br>%{customdata[1]:,} vols<extra></extra>"))
        for row in g.head(1).itertuples():
            fig.add_annotation(x=NOM_COURT[row.airline], y=row.taux_retard, text=f"<b>{pct(row.taux_retard)}</b>",
                               showarrow=False, yshift=12, font={"color": INK, "size": 12})
        fig.update_yaxes(ticksuffix=" %")
        cle = f"cie_apt_{d.signature()}"
        graphique(mise_en_forme(fig, 300), key=cle, clic=d.clic("cie", cle, lambda c: NOM_COURT[c]))
        st.caption(f"Compagnies avec au moins {d.MIN_VOLS} vols au départ de {f.apt} dans la sélection.")
    else:
        t = top.sort_values("nb_vols_aeroport", ascending=False).head(12)
        table_html(t.assign(cie=t["airline"].map(NOM_COURT)),
                   [("origin_airport", "Aéroport", "texte"), ("origin_city", "Ville", "texte"),
                    ("taux_retard_aeroport_pct", "Retard de l'aéroport", ("barre", 45)), ("cie", "Compagnie la plus en retard", "texte"),
                    ("taux_retard_15_pct", "Son retard", ("barre", 45)), ("nb_vols", "Ses vols", "nombre")], hauteur=330)
        st.caption("Choisissez un aéroport dans « Votre vol » pour comparer toutes ses compagnies.")


def render():
    r = d.risque()
    gold, top = d.gold("retards_par_compagnie"), d.gold("top_compagnie_retards_par_aeroport")
    if r is None or gold is None or top is None:
        return
    entete("Étape 2 · La compagnie", "La compagnie peut doubler le risque de retard", etape=2)
    f = d.barre_filtres(r)
    if not d.assez(r, f):
        return

    c1, c2 = st.columns([1.25, 1], gap="medium")
    with c1.container(border=True):
        titre("Spirit et Frontier, les moins ponctuelles", "Part des vols arrivés en retard, par compagnie · cliquez pour choisir")
        g = carte_classement(r, f, gold)
        with st.expander("Requête SQL & justification", icon=":material/code:"):
            st.code("SELECT airline, 100.0 * AVG(CAST(is_delayed_15 AS INT)) AS taux_retard_15_pct,\n"
                    "       PERCENTILE_APPROX(arrival_delay, 0.5) AS retard_mediane_min,\n"
                    "       DENSE_RANK() OVER (ORDER BY AVG(CAST(is_delayed_15 AS INT)) DESC) AS rang_taux_retard\n"
                    "FROM v_silver GROUP BY airline   -- table Gold retards_par_compagnie (J3 §2)", language="sql")
            st.caption("Retard très asymétrique : on compare un taux, pas une moyenne. Kruskal-Wallis : ε² = 0,012.")
            table_html(g.sort_values("taux_retard"), [("airline_name", "Compagnie", "texte"), ("taux_retard", "Retard", "pct"),
                                                      ("n_arrives", "Vols", "nombre")])
    with c2.container(border=True):
        titre("Le retard total suit la taille", "Compagnies classées par minutes de retard cumulées (Pareto)")
        carte_pareto(r, f)
        with st.expander("Requête SQL & justification", icon=":material/code:"):
            st.code("SUM(metric_total) OVER (ORDER BY metric_total DESC\n"
                    "    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) / SUM(metric_total) OVER ()", language="sql")
            st.caption("Les deux courbes se suivent : pas d'effet 80/20, les grosses compagnies pèsent surtout par leur volume.")

    with st.container(border=True):
        titre(f"Au départ de {f.apt}" if f.apt else "Dans les grands aéroports, la compagnie la plus en retard",
              "Part des vols arrivés en retard, par compagnie" if f.apt else "Compagnie la plus en retard (au moins 300 vols) dans les 12 plus gros aéroports")
        carte_aeroport(r, f, top)
        with st.expander("Requête SQL & justification", icon=":material/code:"):
            st.code("ROW_NUMBER() OVER (PARTITION BY origin_airport ORDER BY taux_retard_15_pct DESC) = 1\n"
                    "-- table Gold top_compagnie_retards_par_aeroport (J3 §4)", language="sql")
            st.caption("Classement au taux et non au total de minutes, sinon la plus grosse compagnie gagnerait toujours.")
