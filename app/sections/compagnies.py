"""Onglet « Les compagnies » : classement et Pareto (tables Gold retards_par_compagnie et top_compagnie_retards_par_aeroport, J3)."""

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from sections.style import CORAL, INK, LINE, SAND, TEAL, styled


def render(load_gold):
    df = load_gold("retards_par_compagnie")
    if df is None:
        return

    st.subheader("Toutes les compagnies ne se valent pas")
    st.markdown("Pour un voyageur, la compagnie change le risque d'arriver en retard du simple au double, "
                "même si elle n'explique qu'une petite partie du retard d'un vol donné.")

    lowcost = {"NK", "F9", "WN", "B6", "VX"}
    choix = st.multiselect("Compagnies affichées", sorted(df["airline_name"]),
                           default=sorted(df["airline_name"]), placeholder="Choisissez des compagnies")
    sel = df[df["airline_name"].isin(choix)].sort_values("taux_retard_15_pct")
    if sel.empty:
        st.info("Sélectionnez au moins une compagnie.")
        return
    moyenne = 100 * df["nb_retards_15"].sum() / df["nb_vols"].sum()

    fig = px.bar(sel, x="taux_retard_15_pct", y="airline_name", orientation="h",
                 color=sel["airline"].isin(lowcost).map({True: "Low-cost", False: "Compagnie traditionnelle ou régionale"}),
                 color_discrete_map={"Low-cost": CORAL, "Compagnie traditionnelle ou régionale": TEAL},
                 custom_data=["nb_vols", "retard_mediane_min", "iqr_retard_min", "p90_retard_min"],
                 category_orders={"airline_name": list(sel["airline_name"])[::-1]},
                 title="Part des vols arrivés avec 15 min de retard ou plus")
    fig.update_traces(hovertemplate="<b>%{y}</b><br>%{x:.1f} % de vols en retard<br>%{customdata[0]:,} vols"
                                    "<br>Médiane %{customdata[1]} min, IQR %{customdata[2]} min, P90 %{customdata[3]} min<extra></extra>")
    fig.add_vline(x=moyenne, line_dash="dash", line_color=INK,
                  annotation_text=f"Moyenne : {moyenne:.1f} %".replace(".", ","), annotation_position="top")
    fig.update_layout(xaxis_ticksuffix=" %", xaxis_title=None, yaxis_title=None)
    st.plotly_chart(styled(fig, 480), width="stretch")
    with st.expander("Requête SQL et justification statistique"):
        st.code(
            "SELECT airline, FIRST(airline_name) AS airline_name, COUNT(*) AS nb_vols,\n"
            "       ROUND(100.0 * AVG(CAST(is_delayed_15 AS INT)), 2) AS taux_retard_15_pct,\n"
            "       PERCENTILE_APPROX(arrival_delay, 0.50) AS retard_mediane_min,\n"
            "       PERCENTILE_APPROX(arrival_delay, 0.75) - PERCENTILE_APPROX(arrival_delay, 0.25) AS iqr_retard_min,\n"
            "       DENSE_RANK() OVER (ORDER BY AVG(CAST(is_delayed_15 AS INT)) DESC) AS rang_taux_retard\n"
            "FROM v_silver WHERE arrival_delay IS NOT NULL GROUP BY airline", language="sql")
        st.markdown(
            "Le retard est très asymétrique (skewness ≈ 6,5, J3 §1) : la moyenne est tirée par quelques vols très en "
            "retard. On compare donc les compagnies avec le **taux de vols en retard de 15 min ou plus**, complété par "
            "la **médiane, l'IQR et le P90** au survol. Le test de Kruskal-Wallis (J4) confirme que les compagnies "
            "diffèrent (p < 0,001), avec une taille d'effet faible (ε² = 0,012).")

    st.subheader("Qui pèse dans le retard total ? (Pareto)")
    pareto = df.sort_values("rang_retard_total")
    fig2 = go.Figure()
    fig2.add_bar(x=pareto["airline_name"], y=pareto["total_retard_positif_min"], name="Minutes de retard",
                 marker_color=SAND, hovertemplate="%{x}<br>%{y:,.0f} min<extra></extra>")
    fig2.add_scatter(x=pareto["airline_name"], y=pareto["pct_cumule_retards"], name="Part cumulée du retard",
                     yaxis="y2", mode="lines+markers", line={"color": CORAL, "width": 3},
                     hovertemplate="%{x}<br>%{y:.1f} % du retard cumulé<extra></extra>")
    fig2.add_scatter(x=pareto["airline_name"], y=pareto["part_des_vols_pct"].cumsum(), name="Part cumulée des vols",
                     yaxis="y2", mode="lines", line={"color": INK, "width": 2, "dash": "dot"},
                     hovertemplate="%{x}<br>%{y:.1f} % des vols cumulés<extra></extra>")
    fig2.update_layout(title="Minutes de retard par compagnie et courbe de Pareto",
                       yaxis2={"overlaying": "y", "side": "right", "range": [0, 105], "ticksuffix": " %",
                               "gridcolor": LINE, "showgrid": False},
                       xaxis_tickangle=-35)
    st.plotly_chart(styled(fig2, 460), width="stretch")
    st.caption("Les deux courbes se suivent : les compagnies qui cumulent le plus de minutes de retard sont "
               "surtout celles qui ont le plus de vols. Il n'y a pas d'effet 80/20 marqué.")
    with st.expander("Requête SQL et justification statistique"):
        st.code(
            "SELECT airline, SUM(GREATEST(arrival_delay, 0)) AS total_retard_positif_min,\n"
            "       DENSE_RANK() OVER (ORDER BY SUM(GREATEST(arrival_delay, 0)) DESC) AS rang_retard_total,\n"
            "       100.0 * SUM(SUM(GREATEST(arrival_delay, 0))) OVER (\n"
            "           ORDER BY SUM(GREATEST(arrival_delay, 0)) DESC\n"
            "           ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)\n"
            "         / SUM(SUM(GREATEST(arrival_delay, 0))) OVER () AS pct_cumule_retards\n"
            "FROM v_silver WHERE arrival_delay IS NOT NULL GROUP BY airline", language="sql")
        st.markdown("Le Pareto répond à une autre question que le taux : qui contribue le plus au retard total du "
                    "réseau. On le compare à la part cumulée des vols pour ne pas confondre « beaucoup de retard » "
                    "et « beaucoup de vols ».")

    top = load_gold("top_compagnie_retards_par_aeroport")
    if top is not None:
        st.subheader("Au départ de votre aéroport, quelle compagnie éviter ?")
        top = top.sort_values("nb_vols_aeroport", ascending=False)
        labels = [f"{r.origin_airport} ({r.origin_city})" for r in top.itertuples()]
        choix_apt = st.selectbox("Aéroport de départ", labels, index=0)
        r = top.iloc[labels.index(choix_apt)]
        c1, c2, c3 = st.columns(3)
        c1.metric("Taux de retard de l'aéroport", f"{r.taux_retard_aeroport_pct:.1f} %".replace(".", ","))
        c2.metric("Compagnie la plus en retard", r.airline_name)
        c3.metric("Son taux de retard ici", f"{r.taux_retard_15_pct:.1f} %".replace(".", ","),
                  f"{r.taux_retard_15_pct - r.taux_retard_aeroport_pct:+.1f} points".replace(".", ","), delta_color="inverse")
        st.caption(f"Classement parmi {r.nb_compagnies_classees} compagnies ayant au moins 30 vols au départ de "
                   f"{r.origin_airport} ({r.nb_vols} vols pour {r.airline_name}).")
        with st.expander("Requête SQL et justification statistique"):
            st.code(
                "SELECT origin_airport, airline, COUNT(*) AS nb_vols,\n"
                "       ROUND(100.0 * AVG(CAST(is_delayed_15 AS INT)), 2) AS taux_retard_15_pct,\n"
                "       ROW_NUMBER() OVER (PARTITION BY origin_airport\n"
                "                          ORDER BY AVG(CAST(is_delayed_15 AS INT)) DESC) AS rang\n"
                "FROM v_silver WHERE airport_code_valid AND arrival_delay IS NOT NULL\n"
                "GROUP BY origin_airport, airline HAVING COUNT(*) >= 30   -- puis rang = 1", language="sql")
            st.markdown("On ne classe que les compagnies avec au moins 30 vols au départ de l'aéroport, sinon un taux "
                        "calculé sur 3 ou 4 vols pourrait placer n'importe quelle compagnie en tête. Octobre est exclu "
                        "car ses codes aéroport ne sont pas des codes IATA.")
