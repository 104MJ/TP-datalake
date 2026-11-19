"""Onglet « Le ciel en 3D » : avions 3D d'une journée réelle et carte 3D du réseau de l'année.

Tables Gold lues : flight_replay (vols des journées remarquables, horaires en heure de l'Est)
et route_flows (routes de l'année). Toutes deux sont créées par le notebook J3 (§5).

La scène des avions est une page HTML autonome (ciel_3d_avions.html : deck.gl + MapLibre, chargés depuis
un CDN) dans laquelle on injecte les vols de la journée. Le navigateur doit donc avoir accès à Internet.
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pydeck as pdk
import streamlit as st
import streamlit.components.v1 as components

INK = "#264653"
FONT = "DM Sans, Arial, sans-serif"
MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre",
        "novembre", "décembre"]
CONTINENTAL = {"lon": (-125.5, -66.5), "lat": (24.0, 49.5)}
AVIONS_TEMPLATE = Path(__file__).with_name("ciel_3d_avions.html")


def _continental(df: pd.DataFrame) -> pd.DataFrame:
    def inside(lon, lat):
        return lon.between(*CONTINENTAL["lon"]) & lat.between(*CONTINENTAL["lat"])
    return df[inside(df["origin_lon"], df["origin_lat"]) & inside(df["dest_lon"], df["dest_lat"])]


def date_fr(d) -> str:
    d = pd.Timestamp(d)
    return f"{'1er' if d.day == 1 else d.day} {MOIS[d.month - 1]} {d.year}"


def build_flights_html(day: pd.DataFrame, t0_h: float = 16, autoplay: bool = True, start_h: int = 5, end_h: int = 26,
                       size_scale: float = 3200) -> str:
    """Page HTML autonome : les avions de la journée volent en 3D sur fond satellite (heure de l'Est)."""
    flown = _continental(day.dropna(subset=["takeoff_et", "landing_et"]))
    flown = flown[flown["landing_et"] > flown["takeoff_et"]]
    delay = flown["arrival_delay"].fillna(0)
    cls = np.select([delay < 15, delay < 60], [0, 1], 2)
    flights = [
        [round(r.origin_lon, 4), round(r.origin_lat, 4), round(r.dest_lon, 4), round(r.dest_lat, 4),
         float(r.takeoff_et), float(r.landing_et), int(c), int(r.distance), str(r.airline_name),
         int(r.flight_number), str(r.origin_airport), str(r.destination_airport), int(d)]
        for r, c, d in zip(flown.itertuples(), cls, delay)
    ]
    apt = (day.assign(late=day["arrival_delay"] >= 15)
              .groupby(["origin_airport", "origin_city", "origin_lon", "origin_lat"], as_index=False)
              .agg(n=("flight_number", "size"), taux=("late", "mean")))
    apt = apt[apt["origin_lon"].between(*CONTINENTAL["lon"]) & apt["origin_lat"].between(*CONTINENTAL["lat"])]
    airports = [[round(r.origin_lon, 4), round(r.origin_lat, 4), r.origin_airport, r.origin_city, int(r.n),
                 round(float(r.taux), 3)] for r in apt.itertuples()]
    html = AVIONS_TEMPLATE.read_text(encoding="utf-8")
    for key, value in {
        "__FLIGHTS__": json.dumps(flights, ensure_ascii=False), "__AIRPORTS__": json.dumps(airports, ensure_ascii=False),
        "__START__": str(start_h * 60), "__END__": str(end_h * 60), "__T0__": str(int(t0_h * 60)),
        "__AUTOPLAY__": "true" if autoplay else "false", "__SIZE__": str(size_scale),
    }.items():
        html = html.replace(key, value)
    return html


def _rate_rgb(rate: pd.Series, alpha: int) -> list:
    """Taux de retard (%) -> couleur RGBA : turquoise (ponctuel) -> sable -> corail (≥ 30 %)."""
    stops = np.array([[42, 157, 143], [233, 196, 106], [231, 111, 81]], dtype=float)
    x = np.clip((rate.to_numpy(dtype=float) - 10) / 20, 0, 1) * 2
    i = np.minimum(x.astype(int), 1)
    f = (x - i)[:, None]
    rgb = stops[i] * (1 - f) + stops[i + 1] * f
    return [[int(r), int(g), int(b), alpha] for r, g, b in rgb]


def build_network_deck(routes: pd.DataFrame) -> pdk.Deck:
    """Carte 3D de l'année : arcs des routes (couleur = % de retard) et colonnes des aéroports (hauteur = trafic)."""
    routes = routes.copy()
    routes["color"] = _rate_rgb(routes["taux_retard"], 190)
    routes["width"] = 0.5 + 4 * np.sqrt(routes["n_vols"] / routes["n_vols"].max())

    apt = (routes.assign(n_retards=routes["n_vols"] * routes["taux_retard"] / 100)
                 .groupby(["origin_airport", "origin_city", "origin_lon", "origin_lat"], as_index=False)
                 .agg(n_vols=("n_vols", "sum"), n_retards=("n_retards", "sum")))
    apt["taux_retard"] = (100 * apt["n_retards"] / apt["n_vols"]).round(1)
    apt["color"] = _rate_rgb(apt["taux_retard"], 235)

    arcs = pdk.Layer("ArcLayer", routes, get_source_position=["origin_lon", "origin_lat"],
                     get_target_position=["dest_lon", "dest_lat"], get_source_color="color", get_target_color="color",
                     get_width="width", get_height=0.6, great_circle=False, pickable=True, auto_highlight=True)
    columns = pdk.Layer("ColumnLayer", apt, get_position=["origin_lon", "origin_lat"], get_elevation="n_vols",
                        elevation_scale=60, radius=16000, get_fill_color="color", extruded=True, pickable=True,
                        auto_highlight=True)
    view = pdk.ViewState(latitude=37.5, longitude=-96, zoom=3.4, pitch=52, bearing=-12)
    tooltip = {"html": "<b>{origin_airport}</b> {origin_city}<br/>{n_vols} vols, dont {taux_retard} % en retard",
               "style": {"backgroundColor": "white", "color": INK, "fontFamily": FONT, "borderRadius": "10px",
                         "boxShadow": "0 4px 14px rgba(38,70,83,.15)"}}
    return pdk.Deck(layers=[arcs, columns], initial_view_state=view, map_provider="carto", map_style="light", tooltip=tooltip)


def render(load_gold):
    replay = load_gold("flight_replay")
    if replay is not None:
        st.subheader("Une journée dans le ciel américain")
        st.markdown(
            "Chaque avion est un vol réel de notre échantillon, à sa vraie position et à la vraie heure. "
            "Choisissez une journée, lancez la lecture et regardez les retards s'accumuler au fil des heures."
        )
        days = replay[["flight_date", "day_label", "day_order"]].drop_duplicates().sort_values("day_order")
        labels = [f"{r.day_label} ({date_fr(r.flight_date)})" for r in days.itertuples()]
        choice = st.radio("Journée", labels, horizontal=True, label_visibility="collapsed")
        date = days.iloc[labels.index(choice)]["flight_date"]
        day = replay[replay["flight_date"] == date]

        flown = day[~day["is_cancelled"].astype(bool)]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Vols ce jour-là", f"{len(day):,}".replace(",", " "))
        c2.metric("Arrivés en retard", f"{100 * (flown['arrival_delay'] >= 15).mean():.0f} %")
        c3.metric("Annulés", f"{100 * day['is_cancelled'].astype(bool).mean():.1f} %".replace(".", ","))
        c4.metric("Retard médian à l'arrivée", f"{flown['arrival_delay'].median():+.0f} min")

        components.html(build_flights_html(day), height=720)
        st.caption("Clic droit et glisser pour incliner ou faire pivoter la vue, molette pour zoomer. "
                   "Survolez un avion pour voir son vol. Données : 5 % des vols de 2015.")
        with st.expander("Comment c'est calculé"):
            st.markdown(
                "Les horaires du jeu de données sont en heure locale de chaque aéroport. Pour que tous les avions "
                "partagent la même horloge, on les convertit en heure de l'Est (fuseau de l'État de départ, heure d'été 2015). "
                "Un avion décolle à l'heure prévue, plus son retard au départ, plus le temps de roulage (`taxi_out`), "
                "et se pose `air_time` minutes plus tard. L'altitude est exagérée pour que les trajectoires se lisent.\n\n"
                "Les quatre journées sont choisies en Spark SQL en classant les jours avec `ROW_NUMBER()` :")
            st.code(
                "SELECT flight_date, COUNT(*) AS n_vols,\n"
                "       100 * AVG(CAST(is_delayed_15 AS INT)) AS taux_retard,\n"
                "       ROW_NUMBER() OVER (ORDER BY AVG(CAST(is_delayed_15 AS INT)) DESC) AS rang_pire,\n"
                "       ROW_NUMBER() OVER (ORDER BY AVG(CAST(is_delayed_15 AS INT)) ASC)  AS rang_meilleur\n"
                "FROM v_arrives WHERE airport_code_valid\nGROUP BY flight_date", language="sql")

    routes = load_gold("route_flows")
    if routes is not None:
        st.subheader("Le réseau sur toute l'année")
        st.markdown("Les arcs relient les aéroports, les colonnes montrent leur trafic. "
                    "Plus la couleur tire vers le corail, plus la route ou l'aéroport accumule les retards.")
        col_a, col_b = st.columns(2)
        min_vols = col_a.slider("Nombre minimum de vols par route", 10, 150, 30, step=10)
        min_rate = col_b.slider("Taux de retard minimum (%)", 0, 40, 0)
        sel = routes[(routes["n_vols"] >= min_vols) & (routes["taux_retard"] >= min_rate)]
        st.caption(f"{len(sel)} routes affichées. Clic droit et glisser pour incliner la carte.")
        if len(sel):
            st.pydeck_chart(build_network_deck(sel), height=620)
        with st.expander("Comment c'est calculé"):
            st.code(
                "SELECT origin_airport, destination_airport, COUNT(*) AS n_vols,\n"
                "       ROUND(100 * AVG(CAST(is_delayed_15 AS INT)), 1) AS taux_retard,\n"
                "       PERCENTILE_APPROX(arrival_delay, 0.5) AS retard_median\n"
                "FROM v_arrives WHERE airport_code_valid\n"
                "GROUP BY origin_airport, destination_airport HAVING COUNT(*) >= 10", language="sql")
            st.markdown("Un taux de retard calculé sur une poignée de vols n'est pas fiable : "
                        "le filtre sur le nombre minimum de vols évite de les afficher.")
