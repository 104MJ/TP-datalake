"""Onglet « Quand partir » : saisonnalité du retard (table Gold retards_mensuels, J3 §3)."""

import plotly.graph_objects as go
import streamlit as st

from sections.style import CORAL, MUTED, SAND, TEAL, styled

MOIS = ["Janv.", "Févr.", "Mars", "Avr.", "Mai", "Juin", "Juil.", "Août", "Sept.", "Oct.", "Nov.", "Déc."]


def render(load_gold):
    df = load_gold("retards_mensuels")
    if df is None:
        return
    df = df.sort_values("mois").assign(mois_nom=lambda d: d["mois"].map(lambda m: MOIS[m - 1]))

    st.subheader("Les saisons du retard")
    st.markdown("Le risque de retard n'est pas le même toute l'année : deux pics, en hiver et au début de l'été, "
                "et un creux à l'automne.")

    pire, meilleur = df.loc[df["taux_retard_15_pct"].idxmax()], df.loc[df["taux_retard_15_pct"].idxmin()]
    c1, c2, c3 = st.columns(3)
    c1.metric("Mois le plus à risque", pire["mois_nom"], f"{pire['taux_retard_15_pct']:.1f} % de vols en retard".replace(".", ","),
              delta_color="off")
    c2.metric("Mois le plus sûr", meilleur["mois_nom"], f"{meilleur['taux_retard_15_pct']:.1f} % de vols en retard".replace(".", ","),
              delta_color="off")
    c3.metric("Record d'annulations", df.loc[df["taux_annulation_pct"].idxmax(), "mois_nom"],
              f"{df['taux_annulation_pct'].max():.1f} % de vols annulés".replace(".", ","), delta_color="off")

    vue = st.radio("Indicateur", ["Taux de retard", "Annulations", "Minutes de retard cumulées"], horizontal=True)
    fig = go.Figure()
    if vue == "Taux de retard":
        fig.add_bar(x=df["mois_nom"], y=df["taux_retard_15_pct"], name="Taux de retard du mois", marker_color=SAND,
                    hovertemplate="%{x} : %{y:.1f} %<extra></extra>")
        fig.add_scatter(x=df["mois_nom"], y=df["taux_retard_moyenne_3_mois_pct"], name="Moyenne glissante sur 3 mois",
                        mode="lines+markers", line={"color": CORAL, "width": 3},
                        hovertemplate="%{x} : %{y:.1f} %<extra></extra>")
        fig.update_layout(title="Part des vols arrivés avec 15 min de retard ou plus", yaxis_ticksuffix=" %")
    elif vue == "Annulations":
        fig.add_bar(x=df["mois_nom"], y=df["taux_annulation_pct"], marker_color=CORAL, name="Annulations",
                    hovertemplate="%{x} : %{y:.2f} %<extra></extra>")
        fig.update_layout(title="Part des vols annulés", yaxis_ticksuffix=" %", showlegend=False)
    else:
        fig.add_bar(x=df["mois_nom"], y=df["total_retard_positif_min"], marker_color=TEAL, name="Minutes",
                    hovertemplate="%{x} : %{y:,.0f} min<extra></extra>")
        fig.update_layout(title="Minutes de retard cumulées (échantillon de 5 %)", showlegend=False)
    st.plotly_chart(styled(fig), width="stretch")

    evo = df.dropna(subset=["variation_taux_retard_pts"])
    fig2 = go.Figure(go.Bar(
        x=evo["mois_nom"], y=evo["variation_taux_retard_pts"],
        marker_color=[CORAL if v > 0 else TEAL for v in evo["variation_taux_retard_pts"]],
        hovertemplate="%{x} : %{y:+.1f} points<extra></extra>"))
    fig2.update_layout(title="Évolution d'un mois sur l'autre (points de pourcentage)", showlegend=False,
                       xaxis={"categoryorder": "array", "categoryarray": list(evo["mois_nom"])})
    st.plotly_chart(styled(fig2, 340), width="stretch")
    st.caption("En corail, les mois où le retard augmente par rapport au mois précédent ; en turquoise, ceux où il baisse.")

    with st.expander("Requête SQL et justification statistique"):
        st.code(
            "WITH mensuel AS (\n"
            "  SELECT DATE_TRUNC('MONTH', flight_date) AS periode, COUNT(*) AS nb_vols,\n"
            "         ROUND(100.0 * AVG(CASE WHEN arrival_delay IS NOT NULL\n"
            "                                THEN CAST(is_delayed_15 AS INT) END), 2) AS taux_retard_15_pct,\n"
            "         ROUND(100.0 * AVG(CAST(is_cancelled AS INT)), 2) AS taux_annulation_pct\n"
            "  FROM v_silver GROUP BY DATE_TRUNC('MONTH', flight_date)\n"
            ")\n"
            "SELECT *,\n"
            "       taux_retard_15_pct - LAG(taux_retard_15_pct, 1) OVER (ORDER BY periode) AS variation_taux_retard_pts,\n"
            "       AVG(taux_retard_15_pct) OVER (ORDER BY periode\n"
            "           ROWS BETWEEN 2 PRECEDING AND CURRENT ROW) AS taux_retard_moyenne_3_mois_pct\n"
            "FROM mensuel ORDER BY periode", language="sql")
        st.markdown(
            "On compare les mois avec un **taux** de vols en retard plutôt qu'avec le total de minutes, qui grossit "
            "mécaniquement avec le nombre de vols du mois. `LAG()` donne la variation d'un mois sur l'autre et la "
            "**moyenne glissante sur 3 mois** lisse les à-coups pour faire apparaître la tendance. Les pics de février "
            "et de juin correspondent aux tempêtes d'hiver et aux orages d'été (EDA de J2, étape 2 bis).")
    st.markdown(f"<span style='color:{MUTED};font-size:0.85rem'>Source : table Gold `retards_mensuels` (J3 §3).</span>",
                unsafe_allow_html=True)
