"""Onglet « Les aéroports » : segmentation K-Means (table Gold segments_aeroports, J4 §2)."""

import plotly.express as px
import streamlit as st

from sections.style import SEGMENT_COLORS, styled

DESCRIPTIONS = {
    "Grands hubs congestionnés": "Le plus de trafic, le roulage le plus long et le taux de retard le plus élevé (environ 20 %). Atlanta en fait partie.",
    "Retards en cascade": "La moitié des minutes de retard vient d'un avion arrivé en retard : bases de Southwest (Dallas Love, Houston Hobby, Midway) et Hawaï.",
    "Aéroports régionaux perturbés": "Peu de trafic, la plus forte part de retard due au système aérien, 2 % d'annulations.",
    "Aéroports exposés à la météo": "Little Rock, Fayetteville, Colorado Springs, Fresno : 17 % des minutes de retard dues à la météo et le plus d'annulations.",
}


def render(load_gold):
    df = load_gold("segments_aeroports")
    if df is None:
        return
    df = df.assign(taux_retard_pct=df["taux_retard"], taux_annulation_pct=df["taux_annulation"])

    st.subheader("Quatre profils d'aéroports")
    st.markdown("Un K-Means sur les neuf indicateurs de l'ACP de J2 (retard, annulations, roulage, trafic, distance, "
                "départs du soir, part du retard due au système aérien, à la météo et aux avions arrivés en retard) "
                "regroupe les 104 aéroports avec au moins 300 vols en quatre profils.")

    segments = [s for s in SEGMENT_COLORS if s in set(df["segment"])]
    choix = st.multiselect("Profils affichés", segments, default=segments, placeholder="Choisissez des profils")
    sel = df[df["segment"].isin(choix)]
    if sel.empty:
        st.info("Sélectionnez au moins un profil.")
        return

    cols = st.columns(len(segments))
    for col, seg in zip(cols, segments):
        g = df[df["segment"] == seg]
        col.markdown(
            f"<div style='background:white;border-radius:16px;padding:0.9rem 1rem;height:100%;"
            f"border-top:6px solid {SEGMENT_COLORS[seg]};box-shadow:0 2px 14px rgba(38,70,83,.06)'>"
            f"<div style='font:600 1rem Poppins,sans-serif'>{seg}</div>"
            f"<div style='font-size:0.85rem;color:#6b7785;margin:0.3rem 0'>{len(g)} aéroports, "
            f"{g['taux_retard_pct'].median():.1f} % de retard</div>"
            f"<div style='font-size:0.88rem'>{DESCRIPTIONS.get(seg, '')}</div></div>", unsafe_allow_html=True)
    st.write("")

    fig = px.scatter_geo(sel, lat="origin_lat", lon="origin_lon", color="segment", size="nb_vols", size_max=28,
                         color_discrete_map=SEGMENT_COLORS, scope="usa", hover_name="origin_airport",
                         custom_data=["origin_city", "nb_vols", "taux_retard_pct", "taux_annulation_pct"],
                         title="Carte des profils (taille = nombre de vols)")
    fig.update_traces(hovertemplate="<b>%{hovertext}</b> %{customdata[0]}<br>%{customdata[1]:,} vols"
                                    "<br>%{customdata[2]:.1f} % de retard, %{customdata[3]:.2f} % d'annulations<extra></extra>",
                      marker={"line": {"color": "white", "width": 0.8}, "opacity": 0.9})
    fig.update_geos(bgcolor="white", landcolor="#F3EFE8", lakecolor="white", subunitcolor="#E2DACD",
                    showsubunits=True, showcountries=False, showcoastlines=False)
    st.plotly_chart(styled(fig, 520), width="stretch")

    fig2 = px.scatter(sel, x="taux_annulation_pct", y="taux_retard_pct", color="segment", size="nb_vols", size_max=30,
                      color_discrete_map=SEGMENT_COLORS, hover_name="origin_airport", log_x=False,
                      custom_data=["origin_city", "nb_vols", "retard_p90_min"],
                      title="Retard et annulations : deux façons d'être perturbé")
    fig2.update_traces(hovertemplate="<b>%{hovertext}</b> %{customdata[0]}<br>%{y:.1f} % de retard, "
                                     "%{x:.2f} % d'annulations<br>P90 du retard : %{customdata[2]} min<extra></extra>",
                       marker={"line": {"color": "white", "width": 0.8}})
    fig2.update_layout(xaxis_title="Part des vols annulés (%)", yaxis_title="Part des vols en retard (%)")
    st.plotly_chart(styled(fig2, 460), width="stretch")

    profil = (sel.groupby("segment")[["nb_vols", "retard_p90_min", "taux_retard_pct", "taux_annulation_pct", "distance_mediane"]]
                 .median().round(1).rename(columns={"nb_vols": "Vols", "retard_p90_min": "P90 du retard (min)",
                                                    "taux_retard_pct": "Retard (%)", "taux_annulation_pct": "Annulations (%)",
                                                    "distance_mediane": "Distance (miles)"}))
    st.dataframe(profil, width="stretch")
    st.caption("Médianes de chaque profil.")

    with st.expander("Méthode et justification statistique"):
        st.code(
            "silver_df.where('airport_code_valid').groupBy('origin_airport').agg(\n"
            "    count('*').alias('nb_vols'),\n"
            "    (100 * avg(col('is_delayed_15').cast('int'))).alias('taux_retard'),\n"
            "    (100 * avg(col('is_cancelled').cast('int'))).alias('taux_annulation'),\n"
            "    percentile_approx('taxi_out', 0.5).alias('roulage_median'),\n"
            "    percentile_approx('distance', 0.5).alias('distance_mediane'),\n"
            "    (100 * avg((col('dep_hour') >= 17).cast('int'))).alias('part_depart_soir'),\n"
            "    (100 * sum('air_system_delay') / total_causes).alias('part_systeme'),\n"
            "    (100 * sum('weather_delay') / total_causes).alias('part_meteo'),\n"
            "    (100 * sum('late_aircraft_delay') / total_causes).alias('part_avion_retarde'),\n"
            ").where('nb_vols >= 300')   # puis log_trafic = log10(nb_vols)", language="python")
        st.markdown(
            "- Trafic en log (très asymétrique), puis `StandardScaler` : les variables n'ont pas les mêmes unités "
            "(%, minutes, miles) et aucune ne doit écraser les autres dans la distance euclidienne.\n"
            "- **k = 4** : l'indice de Davies-Bouldin baisse nettement de k = 3 (1,60) à k = 4 (1,47) ; au-delà, "
            "on n'ajoute que des groupes de 2 à 4 aéroports. La silhouette est faible (0,20) : les profils se recouvrent.\n"
            "- Octobre est exclu (codes aéroport non valides) et seuls les aéroports avec au moins 300 vols sont gardés, "
            "pour que les taux soient fiables.\n"
            "- Les profils retrouvent les trois premiers axes de l'ACP de J2 : congestion des hubs, retard propagé "
            "contre perturbations du système aérien, météo.")
