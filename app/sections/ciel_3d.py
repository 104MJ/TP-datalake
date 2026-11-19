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

from sections.donnees import gold as gold_
from sections.theme import nuit, pal

INK = "#13253D"
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
                       size_scale: float = 2400, step: int = 1, focus: str | None = None) -> str:
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
    if nuit():
        html = (html.replace("background: #F2F5F9", f"background: {pal()['page']}")
                    .replace("linear-gradient(180deg, #A9C7D3 0%, #DCE8EC 35%, #EEF3F4 100%)",
                             "linear-gradient(180deg, #0B2545 0%, #13315C 45%, #1E4272 100%)"))
    for key, value in {
        "__FLIGHTS__": json.dumps(flights, ensure_ascii=False), "__AIRPORTS__": json.dumps(airports, ensure_ascii=False),
        "__START__": str(start_h * 60), "__END__": str(end_h * 60), "__T0__": str(int(t0_h * 60)),
        "__AUTOPLAY__": "true" if autoplay else "false", "__SIZE__": str(size_scale),
        "__STEP__": str(max(int(step), 1)), "__FOCUS__": json.dumps(focus),
    }.items():
        html = html.replace(key, value)
    return html


def _rate_rgb(rate: pd.Series, alpha: int) -> list:
    """Taux de retard (%) -> couleur RGBA sur la rampe orange (clair = ponctuel, foncé = en retard)."""
    stops = np.array([[249, 196, 163], [235, 104, 52], [140, 53, 18]], dtype=float)
    x = np.clip((rate.to_numpy(dtype=float) - 12) / 16, 0, 1) * 2
    i = np.minimum(x.astype(int), 1)
    f = (x - i)[:, None]
    rgb = stops[i] * (1 - f) + stops[i + 1] * f
    return [[int(r), int(g), int(b), alpha] for r, g, b in rgb]


TERRES = "https://d2ad6b4ur7yvpq.cloudfront.net/naturalearth-3.3.0/ne_50m_admin_0_scale_rank.geojson"


def build_network_deck(routes: pd.DataFrame, globe: bool = False) -> pdk.Deck:
    """Réseau en 3D : arcs des routes (couleur = % de retard), colonnes des aéroports (hauteur = trafic).
    `globe` : vue sur le globe terrestre plutôt que carte inclinée."""
    routes = routes.copy()
    routes["color"] = _rate_rgb(routes["taux_retard"], 200)
    routes["width"] = 0.6 + 3 * np.sqrt(routes["n_vols"] / routes["n_vols"].max())
    apt = (routes.assign(n_retards=routes["n_vols"] * routes["taux_retard"] / 100)
                 .groupby(["origin_airport", "origin_city", "origin_lon", "origin_lat"], as_index=False)
                 .agg(n_vols=("n_vols", "sum"), n_retards=("n_retards", "sum")))
    apt["taux_retard"] = (100 * apt["n_retards"] / apt["n_vols"]).round(1)
    apt["color"] = _rate_rgb(apt["taux_retard"], 235)
    apt["hauteur"] = 350_000 * np.sqrt(apt["n_vols"] / apt["n_vols"].max())
    arcs = pdk.Layer("ArcLayer", routes, get_source_position=["origin_lon", "origin_lat"],
                     get_target_position=["dest_lon", "dest_lat"], get_source_color="color", get_target_color="color",
                     get_width="width", get_height=0.5, pickable=True, auto_highlight=True, great_circle=globe)
    columns = pdk.Layer("ColumnLayer", apt, get_position=["origin_lon", "origin_lat"], get_elevation="hauteur",
                        elevation_scale=1, radius=14000, get_fill_color="color", extruded=True, pickable=True,
                        auto_highlight=True)
    tooltip = {"html": "<b>{origin_airport}</b> {origin_city}<br/>{n_vols} vols, dont {taux_retard} % en retard",
               "style": {"backgroundColor": "white", "color": INK, "fontFamily": FONT, "borderRadius": "10px",
                         "boxShadow": "0 4px 14px rgba(19,37,61,.15)"}}
    if globe:
        fond = {"depthTest": False}
        ocean = pdk.Layer("SolidPolygonLayer", [{"p": [[-180, -90], [180, -90], [180, 90], [-180, 90]]}],
                          get_polygon="p", get_fill_color=[11, 37, 69], parameters=fond)
        terres = pdk.Layer("GeoJsonLayer", TERRES, stroked=False, filled=True, get_fill_color=[36, 72, 110], parameters=fond)
        p = np.linspace(0, 1, 17)
        routes["path"] = [[[lo1 + t * (lo2 - lo1), la1 + t * (la2 - la1), (40_000 + 90 * d) * np.sin(np.pi * t)] for t in p]
                          for lo1, la1, lo2, la2, d in routes[["origin_lon", "origin_lat", "dest_lon", "dest_lat", "distance"]].values]
        arcs = pdk.Layer("PathLayer", routes, get_path="path", get_color="color", get_width="width",
                         width_units="pixels", width_min_pixels=1.2, pickable=True, auto_highlight=True)
        columns = pdk.Layer("ColumnLayer", apt, get_position=["origin_lon", "origin_lat"], get_elevation="hauteur",
                            elevation_scale=2.5, radius=30000, get_fill_color="color", extruded=True, pickable=True)
        return pdk.Deck(layers=[ocean, terres, arcs, columns], views=[pdk.View(type="_GlobeView", controller=True)],
                        initial_view_state=pdk.ViewState(latitude=36, longitude=-96, zoom=2.6), map_provider=None,
                        tooltip=tooltip)
    view = pdk.ViewState(latitude=37.5, longitude=-96, zoom=3.5, pitch=45, bearing=-10)
    return pdk.Deck(layers=[arcs, columns], initial_view_state=view, map_provider="carto",
                    map_style="dark" if nuit() else "light", tooltip=tooltip)


DENSITES = {"Aérée": 10, "Moyenne": 4, "Tous les vols": 1}
SQL_JOURS = ("SELECT flight_date, 100 * AVG(CAST(is_delayed_15 AS INT)) AS taux_retard,\n"
             "       ROW_NUMBER() OVER (ORDER BY AVG(CAST(is_delayed_15 AS INT)) DESC) AS rang_pire\n"
             "FROM v_silver WHERE airport_code_valid GROUP BY flight_date   -- tables Gold flight_replay, route_flows (J3 §5)")


COURT = {1: "Pire journée", 2: "Blizzard", 3: "Jour ordinaire", 4: "Plus ponctuelle"}


def _journee(replay):
    days = replay[["flight_date", "day_label", "day_order"]].drop_duplicates().sort_values("day_order")
    labels = {COURT.get(r.day_order, r.day_label): r.flight_date for r in days.itertuples()}
    with st.container(key="barre_jour"):
        c = st.columns([2.6, 1.1, 0.9], vertical_alignment="bottom", gap="medium")
        choix = c[0].segmented_control("Journée", list(labels), default=list(labels)[0], required=True, key="c_jour")
        densite = c[1].segmented_control("Avions affichés", list(DENSITES), default="Aérée", required=True, key="c_densite")
        day = replay[replay["flight_date"] == labels[choix]]
        apts = day["origin_airport"].value_counts()
        focus = c[2].selectbox("Aéroport", ["Tous"] + list(apts.index[:40]), key="c_focus",
                               format_func=lambda a: "Tous les aéroports" if a == "Tous" else a)
    return choix, labels[choix], day, DENSITES[densite], None if focus == "Tous" else focus


def onglet_journee(replay):
    choix, date, day, step, focus = _journee(replay)
    flown = day[~day["is_cancelled"].astype(bool)]
    c = st.columns(4)
    c[0].metric("Vols ce jour-là", f"{len(day):,}".replace(",", " "), date_fr(date), delta_color="off", delta_arrow="off", border=True, height=130)
    c[1].metric("Arrivés en retard", f"{100 * (flown['arrival_delay'] >= 15).mean():.0f} %", border=True, height=130)
    c[2].metric("Annulés", f"{100 * day['is_cancelled'].astype(bool).mean():.1f} %".replace(".", ","), border=True, height=130)
    c[3].metric("Retard médian à l'arrivée", f"{flown['arrival_delay'].median():+.0f} min", border=True, height=130)
    st.iframe(build_flights_html(day, step=step, focus=focus, size_scale=2400 if step > 1 or focus else 1600), height=640)
    with st.expander("Méthode & justification", icon=":material/code:"):
        st.code(SQL_JOURS, language="sql")
        st.caption("Horaires convertis en heure de l'Est. Décollage = départ prévu + retard + roulage ; atterrissage = décollage + air_time.")


def onglet_reseau(routes):
    with st.container(key="barre_reseau"):
        c = st.columns([0.9, 1.4, 1], vertical_alignment="bottom", gap="medium")
        vue = c[0].segmented_control("Vue", ["Carte 3D", "Globe"], default="Carte 3D", required=True, key="c_vue")
        n = c[1].select_slider("Routes affichées (les plus fréquentées)", options=[50, 100, 200, 400, 800], value=200, key="c_routes")
        apts = routes.groupby("origin_airport")["n_vols"].sum().sort_values(ascending=False)
        focus = c[2].selectbox("Aéroport", ["Tous"] + list(apts.index[:60]), key="c_reseau",
                               format_func=lambda a: "Tous les aéroports" if a == "Tous" else a)
    sel = routes if focus == "Tous" else routes[(routes["origin_airport"] == focus) | (routes["destination_airport"] == focus)]
    sel = _continental(sel).nlargest(n, "n_vols")
    st.pydeck_chart(build_network_deck(sel, globe=vue == "Globe"), height=620)
    geste = "glisser pour faire tourner le globe" if vue == "Globe" else "clic droit pour incliner"
    st.caption(f"{len(sel)} routes · couleur = part de vols en retard (clair : ponctuel, foncé : en retard) · {geste}.")
    with st.expander("Méthode & justification", icon=":material/code:"):
        st.code("SELECT origin_airport, destination_airport, COUNT(*) AS n_vols,\n"
                "       ROUND(100 * AVG(CAST(is_delayed_15 AS INT)), 1) AS taux_retard\n"
                "FROM v_silver WHERE airport_code_valid GROUP BY 1, 2 HAVING COUNT(*) >= 100", language="sql")
        st.caption("Seules les routes les plus fréquentées sont tracées : leur taux de retard est fiable et la carte reste lisible.")


def render():
    from sections.theme import entete
    entete("Étape 4 · En vol", "Une journée dans le ciel américain", etape=4)
    replay, routes = gold_("flight_replay"), gold_("route_flows")
    t1, t2 = st.tabs(["Une journée en direct", "Le réseau sur l'année"])
    with t1:
        if replay is not None:
            onglet_journee(replay)
    with t2:
        if routes is not None:
            onglet_reseau(routes)
