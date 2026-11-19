"""Page « Vue d'ensemble » : KPI de la sélection et quatre facteurs du retard (table Gold risque_retard)."""

import numpy as np
import plotly.graph_objects as go
import streamlit as st

from sections import donnees as d
from sections.cockpit import instruments, profil_vol
from sections.radar import radar
from sections.theme import (BLUE, GRAY, INK, MOIS, MUTED, NOM_COURT, ORANGE, RAMPE, compact, entete, fr, graphique,
                            mise_en_forme, pct, titre)

SQL = ("SELECT airline, origin_airport, month, dep_hour,\n"
       "       COUNT(*) AS n_vols, SUM(CAST(is_cancelled AS INT)) AS n_annules,\n"
       "       COUNT(arrival_delay) AS n_arrives, SUM(CAST(is_delayed_15 AS INT)) AS n_retards\n"
       "FROM v_silver GROUP BY airline, origin_airport, month, dep_hour   -- table Gold risque_retard (J3 §6)")


def methode(texte: str):
    with st.expander("Requête SQL & justification", icon=":material/code:"):
        st.code(SQL, language="sql")
        st.caption(texte)


def kpis(r, f, noms):
    sel, ref = d.filtrer(r, f), d.totaux(r)
    t = d.totaux(sel)
    mois = d.par(d.filtrer(r, f, sauf=("mois",)), "month").set_index("month").reindex(range(1, 13)).fillna(0)
    heures = d.par(d.filtrer(r, f, sauf=("heures",)), "dep_hour")
    heures = heures[(heures["n_arrives"] >= d.MIN_VOLS) & (heures["dep_hour"] >= 5)]
    best = heures.loc[heures["taux_retard"].idxmin()] if len(heures) else None
    ecart = (lambda v, w: round(v - w, 2)) if f.actif else (lambda v, w: None)
    instruments(
        risque={"valeur": round(t["retard"], 2), "ref": round(ref["retard"], 2), "max": 40, "delta": ecart(t["retard"], ref["retard"])},
        vols={"valeur": int(t["vols"]), "part": f"{pct(100 * t['vols'] / ref['vols'], 0 if t['vols'] / ref['vols'] >= 0.1 else 1)} des vols de 2015",
              "mois": mois["n_vols"].astype(int).tolist(), "noms": MOIS,
              "dans": [f.mois[0] <= m <= f.mois[1] for m in range(1, 13)]},
        annul={"valeur": round(t["annul"], 2), "ref": round(ref["annul"], 2), "max": 5, "delta": ecart(t["annul"], ref["annul"])},
        heure={"meilleure": int(best.dep_hour) if best is not None else 5, "taux": float(best.taux_retard) if best is not None else 0,
               "heures": [{"h": int(x.dep_hour), "t": round(float(x.taux_retard), 2)} for x in heures.itertuples()]})
    if t["arrives"] < 100:
        st.warning(f"Seulement {fr(t['arrives'], 0)} vols arrivés dans cette sélection : élargissez-la pour un taux fiable.",
                   icon=":material/warning:")


def _clic_heure():
    h = st.session_state["profil"]["heure"]
    if h is not None:
        d._appliquer_filtre("heures", (int(h), int(h)), f"Départ à {int(h)} h")


def carte_heures(r, f):
    sel = d.par(d.filtrer(r, f, sauf=("heures",)), "dep_hour").query("n_arrives >= @d.MIN_VOLS and dep_hour >= 5")
    if len(sel) < 2:
        return st.caption(d.TROP_PEU)
    ref = []
    if f.apt or f.cie or f.mois != (1, 12):
        ref = [{"h": int(x.dep_hour), "t": round(float(x.taux_retard), 2)} for x in d.par(r, "dep_hour").query("dep_hour >= 5").itertuples()]
    profil_vol([{"h": int(x.dep_hour), "t": round(float(x.taux_retard), 2), "n": int(x.n_arrives)} for x in sel.itertuples()],
               ref, list(f.heures) if f.heures != (0, 23) else None, _clic_heure)


def carte_compagnies(r, f):
    g = d.par(d.filtrer(r, f, sauf=("cie",)), ["airline", "airline_name"]).query("n_arrives >= @d.MIN_VOLS")
    if g.empty:
        return st.caption(d.TROP_PEU)
    g = g.sort_values("taux_retard")
    moy = d.totaux(d.filtrer(r, f, sauf=("cie",)))["retard"]
    couleurs = [ORANGE if (f.cie is None or a == f.cie) else GRAY for a in g["airline"]]
    fig = go.Figure(go.Bar(x=g["taux_retard"], y=g["airline"].map(NOM_COURT),
                           orientation="h", marker_color=couleurs, customdata=np.stack([g["airline"], g["n_arrives"]], axis=1),
                           hovertemplate="<b>%{y}</b><br>%{x:.1f} % de retard<br>%{customdata[1]:,} vols<extra></extra>"))
    fig.add_vline(x=moy, line_color=MUTED, line_width=1)
    fig.add_annotation(x=moy, y=1.04, yref="paper", text=f"moyenne {pct(moy)}", showarrow=False,
                       font={"size": 11, "color": MUTED})
    a_etiqueter = g[g["airline"] == f.cie] if f.cie else g.iloc[[0, -1]]
    for row in a_etiqueter.itertuples():
        fig.add_annotation(x=row.taux_retard, y=NOM_COURT[row.airline],
                           text=f"<b>{pct(row.taux_retard)}</b>", showarrow=False, xanchor="left", xshift=6,
                           font={"color": INK, "size": 12})
    fig.update_xaxes(ticksuffix=" %", range=[0, g["taux_retard"].max() * 1.18])
    fig.update_yaxes(gridcolor="rgba(0,0,0,0)")
    cle = f"compagnies_{d.signature()}"
    graphique(mise_en_forme(fig, 330).update_layout(margin_t=24), key=cle, clic=d.clic("cie", cle, lambda c: NOM_COURT[c]))


def carte_mois(r, f):
    g = d.par(d.filtrer(r, f, sauf=("mois",)), "month").query("n_arrives >= @d.MIN_VOLS")
    if g.empty:
        return st.caption(d.TROP_PEU)
    dans = g["month"].between(*f.mois)
    fig = go.Figure(go.Bar(x=[MOIS[m - 1] for m in g["month"]], y=g["taux_retard"],
                           marker_color=np.where(dans, ORANGE, GRAY), customdata=np.stack([g["month"], g["n_arrives"]], axis=1).tolist(),
                           hovertemplate="%{x} : <b>%{y:.1f} %</b> de retard<br>%{customdata[1]:,} vols<extra></extra>"))
    for p in (g.loc[g["taux_retard"].idxmax()], g.loc[g["taux_retard"].idxmin()]):
        fig.add_annotation(x=MOIS[int(p.month) - 1], y=p.taux_retard, text=f"<b>{pct(p.taux_retard, 0)}</b>",
                           showarrow=False, yshift=12, font={"color": INK, "size": 12})
    fig.update_yaxes(ticksuffix=" %", rangemode="tozero")
    cle = f"mois_{d.signature()}"
    graphique(mise_en_forme(fig, 290), key=cle, clic=d.clic("mois", cle, lambda m: MOIS[m[0] - 1]))


def carte_carte(r, f):
    g = d.par(d.filtrer(r, f, sauf=("apt",)), ["origin_airport", "origin_city", "origin_lat", "origin_lon"])
    g = g[g["n_arrives"] >= d.MIN_VOLS].sort_values("n_vols")
    if g.empty:
        return st.caption(d.TROP_PEU)
    lo, hi = np.nanpercentile(g["taux_retard"], [5, 95]) if len(g) > 5 else (10, 30)
    fig = go.Figure(go.Scattergeo(
        lon=g["origin_lon"], lat=g["origin_lat"], mode="markers",
        marker={"size": 4 + 22 * np.sqrt(g["n_vols"] / g["n_vols"].max()), "color": g["taux_retard"],
                "colorscale": [[i / 5, c] for i, c in enumerate(RAMPE)], "cmin": lo, "cmax": hi,
                "line": {"color": "white", "width": 1}, "opacity": 0.92,
                "colorbar": {"title": {"text": "% retard", "side": "top", "font": {"size": 11}}, "thickness": 8,
                             "len": 0.5, "x": 1.0, "ticksuffix": " %", "tickfont": {"size": 10, "color": MUTED},
                             "outlinewidth": 0}},
        customdata=np.stack([g["origin_airport"], g["origin_city"], g["taux_retard"], g["n_vols"]], axis=1),
        hovertemplate="<b>%{customdata[0]}</b> %{customdata[1]}<br>%{customdata[2]:.1f} % de retard<br>"
                      "%{customdata[3]:,} vols<extra></extra>"))
    if f.apt and f.apt in set(g["origin_airport"]):
        p = g[g["origin_airport"] == f.apt].iloc[0]
        fig.add_scattergeo(lon=[p.origin_lon], lat=[p.origin_lat], mode="markers+text", text=[f.apt],
                           textposition="top center", textfont={"color": INK, "size": 13, "family": "DM Sans"},
                           marker={"size": 20, "color": "rgba(0,0,0,0)", "line": {"color": INK, "width": 2.5}},
                           hoverinfo="skip")
    fig.update_geos(scope="usa", bgcolor="rgba(0,0,0,0)", landcolor="#E8EDF3", subunitcolor="#FFFFFF",
                    showlakes=False, showcoastlines=False, showframe=False)
    fig.update_layout(geo={"domain": {"x": [0, 0.94]}})
    cle = f"carte_{d.signature()}"
    graphique(mise_en_forme(fig, 300), key=cle, clic=d.clic("apt", cle, lambda a: a))


def render():
    r = d.risque()
    if r is None:
        return
    routes = d.gold("route_flows")
    ref = d.totaux(r)
    if routes is None:
        entete("Vols intérieurs américains · 2015", "Votre vol arrivera-t-il à l'heure ?")
    else:
        radar(routes, ref["retard"], [(compact(ref["vols"]), "vols en 2015"), (pct(ref["retard"]), "arrivent en retard"),
                                      (fr(len(routes), 0), "routes suivies")],
              "Vols intérieurs américains · 2015", "Votre vol arrivera-t-il à l'heure ?",
              "Chaque trait lumineux est un avion sur l'une des 320 routes les plus fréquentées. "
              "Décrivez votre vol ci-dessous : tout le tableau de bord s'adapte.")
    f = d.barre_filtres(r)
    if not d.assez(r, f):
        return
    kpis(r, f, d.noms_compagnies(r))

    g1, g2 = st.columns([1.45, 1], gap="medium")
    with g1.container(border=True):
        titre("Le risque prend de l'altitude au fil de la journée",
              "Part des vols arrivés en retard selon l'heure de départ prévue · cliquez une heure pour la choisir")
        carte_heures(r, f)
        methode("Les retards se propagent d'un vol à l'autre : l'avion du soir hérite des retards du matin.")
    with g2.container(border=True):
        titre("Toutes les compagnies ne se valent pas", "Part des vols arrivés en retard, par compagnie · cliquez pour choisir")
        carte_compagnies(r, f)
        methode(f"Compagnies avec au moins {d.MIN_VOLS} vols dans la sélection. Taux recalculé à partir des effectifs.")

    g3, g4 = st.columns([1, 1.45], gap="medium")
    with g3.container(border=True):
        titre("L'été et l'hiver sont à risque", "Part des vols arrivés en retard, par mois · cliquez pour choisir"
              + (" · octobre absent (codes aéroport non IATA)" if f.apt else ""))
        carte_mois(r, f)
        methode("Février : tempêtes d'hiver ; juin : orages d'été. Septembre-octobre est le creux de l'année.")
    with g4.container(border=True):
        titre("D'où partez-vous ?", "Taille = trafic, couleur = part de vols en retard · cliquez un aéroport pour le choisir")
        carte_carte(r, f)
        methode(f"Aéroports avec au moins {d.MIN_VOLS} vols dans la sélection ; octobre exclu (codes non IATA).")
