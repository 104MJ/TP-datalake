"""Page « Aéroports » : les 4 profils du K-Means (table Gold segments_aeroports, J4 §2)."""

import numpy as np
import plotly.graph_objects as go
import streamlit as st

from sections import donnees as d
from sections.theme import GRAY, INK, SEGMENTS, entete, fr, graphique, mise_en_forme, pct, table_html, titre

PROFILS = {
    "Grands hubs congestionnés": "Beaucoup de trafic, roulage long, départs tardifs.",
    "Retards en cascade": "Le retard vient surtout d'un avion arrivé en retard.",
    "Aéroports régionaux perturbés": "Retards dus au système aérien, annulations fréquentes.",
    "Aéroports exposés à la météo": "Petits aéroports, deux fois plus de retard dû à la météo.",
}


def liste_profils(s, choix):
    g = s.groupby("segment").agg(n=("origin_airport", "size"), retard=("taux_retard", "median"),
                                 annul=("taux_annulation", "median"))
    vmax = g["retard"].max()
    html = ""
    for seg, desc in PROFILS.items():
        if seg not in g.index:
            continue
        row = g.loc[seg]
        actif = "actif" if seg == choix else ""
        html += (f"<div class='profil {actif}'><div class='profil-tete'><i style='background:{SEGMENTS[seg]}'></i>"
                 f"<b>{seg}</b><span>{int(row.n)} aéroports</span></div><div class='profil-desc'>{desc}</div>"
                 f"<div class='profil-barre'><div style='width:{100 * row.retard / vmax:.0f}%;background:{SEGMENTS[seg]}'></div></div>"
                 f"<div class='profil-chiffres'>{pct(row.retard)} de retard · {pct(row.annul, 1)} d'annulations (médianes)</div></div>")
    st.markdown(html, unsafe_allow_html=True)


def carte_carte(s, choix):
    autres, sel = s[s["segment"] != choix], s[s["segment"] == choix]
    taille = lambda g: 5 + 24 * np.sqrt(g["nb_vols"] / s["nb_vols"].max())
    fig = go.Figure()
    for g, couleur, opac in ((autres, GRAY, 0.6), (sel, SEGMENTS[choix], 0.95)):
        fig.add_scattergeo(lon=g["origin_lon"], lat=g["origin_lat"], mode="markers", name="",
                           marker={"size": taille(g), "color": couleur, "opacity": opac, "line": {"color": "white", "width": 1}},
                           customdata=np.stack([g["origin_airport"], g["origin_city"], g["segment"], g["taux_retard"], g["nb_vols"]], axis=1),
                           hovertemplate="<b>%{customdata[0]}</b> %{customdata[1]}<br>%{customdata[2]}<br>"
                                         "%{customdata[3]:.1f} % de retard · %{customdata[4]:,} vols<extra></extra>")
    for row in sel.nlargest(6, "nb_vols").itertuples():
        fig.add_scattergeo(lon=[row.origin_lon], lat=[row.origin_lat], mode="text", text=[row.origin_airport],
                           textposition="top center", textfont={"color": INK, "size": 12, "family": "DM Sans"}, hoverinfo="skip")
    fig.update_geos(scope="usa", bgcolor="rgba(0,0,0,0)", landcolor="#E8EDF3", subunitcolor="#FFFFFF",
                    showlakes=False, showcoastlines=False, showframe=False)
    cle = f"carte_profils_{d.signature()}"
    graphique(mise_en_forme(fig, 380), key=cle, clic=d.clic("apt", cle, lambda a: a))


def carte_nuage(s, choix):
    fig = go.Figure()
    for g, couleur in ((s[s["segment"] != choix], GRAY), (s[s["segment"] == choix], SEGMENTS[choix])):
        fig.add_scatter(x=g["taux_annulation"], y=g["taux_retard"], mode="markers",
                        marker={"size": 6 + 18 * np.sqrt(g["nb_vols"] / s["nb_vols"].max()), "color": couleur,
                                "line": {"color": "white", "width": 2}},
                        customdata=np.stack([g["origin_airport"], g["origin_city"]], axis=1),
                        hovertemplate="<b>%{customdata[0]}</b> %{customdata[1]}<br>%{y:.1f} % de retard · "
                                      "%{x:.2f} % d'annulations<extra></extra>")
    fig.update_xaxes(ticksuffix=" %", title={"text": "Vols annulés", "font": {"size": 12}})
    fig.update_yaxes(ticksuffix=" %", title={"text": "Vols en retard", "font": {"size": 12}})
    graphique(mise_en_forme(fig, 320), key="nuage")


def render():
    s = d.gold("segments_aeroports")
    if s is None:
        return
    entete("Étape 3 · L'aéroport", "Quatre façons d'être en retard", etape=3)
    with st.container(key="barre"):
        choix = st.pills("Profil d'aéroport (K-Means sur les 9 variables de l'ACP)", list(PROFILS), default=list(PROFILS)[0],
                         required=True)

    c1, c2 = st.columns([1.6, 1], gap="medium")
    with c1.container(border=True):
        titre(f"{choix} : {(s['segment'] == choix).sum()} aéroports",
              "Taille = nombre de vols ; en couleur, le profil choisi · cliquez un aéroport pour préparer votre vol")
        carte_carte(s, choix)
    with c2.container(border=True):
        titre("Les 4 profils", "Taux médians des aéroports de chaque profil")
        liste_profils(s, choix)

    c3, c4 = st.columns([1, 1.2], gap="medium")
    with c3.container(border=True):
        titre("Retard ou annulation ?", "Chaque point est un aéroport")
        carte_nuage(s, choix)
    with c4.container(border=True):
        titre("Les plus gros aéroports du profil", "Classés par nombre de vols")
        t = s[s["segment"] == choix].nlargest(15, "nb_vols")
        table_html(t, [("origin_airport", "Code", "texte"), ("origin_city", "Ville", "texte"), ("nb_vols", "Vols", "nombre"),
                       ("taux_retard", "Retard", ("barre", 35)), ("taux_annulation", "Annulés", "pct"),
                       ("part_meteo", "Météo", "pct"), ("part_avion_retarde", "Cascade", "pct")], hauteur=330)
        st.caption("Météo et Cascade : part des minutes de retard dues à la météo et à un avion arrivé en retard.")
    with st.expander("Méthode & justification", icon=":material/code:"):
        st.code("silver_df.where('airport_code_valid').groupBy('origin_airport').agg(... 9 variables de l'ACP ...)\n"
                "  .where('nb_vols >= 1000')  ->  StandardScaler  ->  KMeans(n_clusters=4)   # table Gold segments_aeroports",
                language="python")
        st.caption("k = 4 : pas de k net (silhouette 0,17), 4 groupes d'au moins 27 aéroports, lisibles. Aéroports d'au moins 1 000 vols.")
