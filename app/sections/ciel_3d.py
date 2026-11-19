"""Onglet « Ciel 3D » : replay animé d'une journée de vols et carte 3D du réseau.

Tables Gold lues : flight_replay (vols des journées remarquables, horaires en heure de l'Est)
et route_flows (routes de l'année). Toutes deux sont créées par notebooks/travail/V_vitrine_3D.ipynb.
Les fonctions build_* sont pures (pandas -> figure) et réutilisées dans le notebook.
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import pydeck as pdk
import streamlit as st

BG = "#070b19"

# Catégories de retard à l'arrivée : (libellé, borne basse incluse, borne haute exclue, couleur)
DELAY_CLASSES = [
    ("À l'heure (< 15 min)", -10_000, 15, "#22d3ee"),
    ("Retard 15 à 60 min", 15, 60, "#f59e0b"),
    ("Retard > 60 min", 60, 100_000, "#ef4444"),
]

# Contour simplifié des États-Unis continentaux (lon, lat), tracé au sol de la scène 3D
US_OUTLINE = [
    (-124.7, 48.4), (-122.8, 49.0), (-95.2, 49.0), (-89.6, 48.0), (-84.8, 46.5), (-82.5, 45.3),
    (-82.4, 43.0), (-83.1, 42.3), (-82.6, 41.7), (-79.0, 42.8), (-79.1, 43.3), (-76.3, 44.2),
    (-74.7, 45.0), (-71.5, 45.0), (-70.0, 46.7), (-69.2, 47.45), (-67.8, 47.1), (-67.8, 45.7),
    (-67.0, 44.8), (-68.8, 44.3), (-70.2, 43.6), (-70.7, 42.9), (-71.0, 42.3), (-70.0, 41.8),
    (-71.4, 41.4), (-72.9, 41.2), (-74.0, 40.6), (-74.0, 39.8), (-74.9, 38.9), (-75.1, 38.3),
    (-75.9, 37.1), (-76.0, 36.9), (-75.5, 35.2), (-76.5, 34.7), (-77.9, 33.9), (-79.2, 33.2),
    (-80.9, 32.0), (-81.4, 30.7), (-80.6, 28.4), (-80.0, 26.7), (-80.2, 25.4), (-81.1, 25.1),
    (-81.8, 26.1), (-82.7, 27.7), (-82.7, 29.0), (-84.0, 30.1), (-85.4, 29.7), (-87.3, 30.4),
    (-88.1, 30.4), (-89.4, 30.2), (-89.2, 29.0), (-90.3, 29.1), (-91.8, 29.5), (-93.8, 29.7),
    (-94.8, 29.3), (-96.6, 28.3), (-97.4, 27.4), (-97.2, 25.95), (-99.5, 27.5), (-101.4, 29.8),
    (-103.3, 29.0), (-104.7, 30.0), (-106.5, 31.8), (-108.2, 31.8), (-108.2, 31.33), (-111.1, 31.33),
    (-114.8, 32.5), (-117.1, 32.5), (-118.4, 33.7), (-120.6, 34.6), (-121.9, 36.6), (-122.5, 37.8),
    (-123.8, 39.4), (-124.4, 40.4), (-124.2, 42.0), (-124.0, 44.6), (-124.0, 46.3), (-124.7, 48.4),
]

CONTINENTAL = {"lon": (-125.5, -66.5), "lat": (24.0, 49.5)}


def _continental(df: pd.DataFrame) -> pd.DataFrame:
    def inside(lon, lat):
        return lon.between(*CONTINENTAL["lon"]) & lat.between(*CONTINENTAL["lat"])
    return df[inside(df["origin_lon"], df["origin_lat"]) & inside(df["dest_lon"], df["dest_lat"])]


def _hhmm(minutes: float) -> str:
    m = int(round(minutes)) % (24 * 60)
    return f"{m // 60:02d}:{m % 60:02d}"


def _arc(df: pd.DataFrame, p: np.ndarray):
    """Position (lon, lat, altitude) de chaque vol à la progression p ∈ [0, 1] (arc parabolique).

    p a la forme (n,) ou (n, k) : k points le long de l'arc de chacun des n vols.
    """
    p = np.asarray(p, dtype=float)
    col = (lambda c: df[c].to_numpy(dtype=float)[:, None]) if p.ndim == 2 else (lambda c: df[c].to_numpy(dtype=float))
    lon = col("origin_lon") + p * (col("dest_lon") - col("origin_lon"))
    lat = col("origin_lat") + p * (col("dest_lat") - col("origin_lat"))
    peak = 0.6 + 2.4 * np.clip(col("distance") / 2500.0, 0, 1.2)  # les longs vols montent plus haut
    return lon, lat, peak * np.sin(np.pi * p)


def _with_breaks(a: np.ndarray) -> np.ndarray:
    """(n, k) -> vecteur où chaque ligne est suivie d'un NaN : n segments dans un seul tracé Plotly."""
    return np.hstack([a, np.full((a.shape[0], 1), np.nan)]).ravel()


def build_replay_figure(day: pd.DataFrame, step_min: int = 10, trail_min: int = 14, start_h: int = 5, end_h: int = 26) -> go.Figure:
    """Replay 3D animé d'une journée : un avion par vol, sur un arc entre décollage et atterrissage (heure de l'Est)."""
    flown = _continental(day.dropna(subset=["takeoff_et", "landing_et"]))
    flown = flown[flown["landing_et"] > flown["takeoff_et"]].reset_index(drop=True)
    delay = flown["arrival_delay"].fillna(0).to_numpy()
    cls_idx = np.select([delay < 15, delay < 60], [0, 1], 2)

    fig = go.Figure()

    # --- Décor statique : contour au sol, toile des trajectoires du jour, aéroports ---
    ox, oy = zip(*US_OUTLINE)
    fig.add_trace(go.Scatter3d(x=ox, y=oy, z=[0] * len(ox), mode="lines", hoverinfo="skip",
                               line={"color": "rgba(56,189,248,0.55)", "width": 3}, name="États-Unis", showlegend=False))

    p_line = np.tile(np.linspace(0, 1, 24), (len(flown), 1))
    web_x, web_y, web_z = _arc(flown, p_line)
    fig.add_trace(go.Scatter3d(x=_with_breaks(web_x), y=_with_breaks(web_y), z=_with_breaks(web_z), mode="lines",
                               hoverinfo="skip", line={"color": "rgba(148,163,184,0.10)", "width": 1},
                               name="Trajectoires du jour", showlegend=False))

    apt = (day.assign(late=day["arrival_delay"] >= 15)
              .groupby(["origin_airport", "origin_city", "origin_lon", "origin_lat"], as_index=False)
              .agg(n=("flight_number", "size"), taux=("late", "mean")))
    apt = apt[apt["origin_lon"].between(*CONTINENTAL["lon"]) & apt["origin_lat"].between(*CONTINENTAL["lat"])]
    top = apt.nlargest(10, "n")
    fig.add_trace(go.Scatter3d(
        x=apt["origin_lon"], y=apt["origin_lat"], z=np.zeros(len(apt)), mode="markers",
        marker={"size": 2.5 + 1.2 * np.sqrt(apt["n"]), "color": 100 * apt["taux"], "colorscale": "YlOrRd",
                "cmin": 0, "cmax": 50, "opacity": 0.85, "line": {"width": 0}},
        customdata=np.c_[apt["origin_airport"], apt["origin_city"], apt["n"], (100 * apt["taux"]).round(1)],
        hovertemplate="<b>%{customdata[0]}</b> %{customdata[1]}<br>%{customdata[2]} départs, %{customdata[3]} % en retard<extra></extra>",
        name="Aéroports (couleur = % de retard)", showlegend=False))
    fig.add_trace(go.Scatter3d(x=top["origin_lon"], y=top["origin_lat"], z=np.full(len(top), 0.25), mode="text",
                               text=top["origin_airport"], textfont={"color": "#e2e8f0", "size": 10},
                               hoverinfo="skip", showlegend=False))
    n_static = len(fig.data)

    # --- Traces dynamiques : pour chaque classe de retard, la traînée puis l'avion ---
    def dynamic_traces(t):
        p_now = (t - flown["takeoff_et"].to_numpy()) / (flown["landing_et"] - flown["takeoff_et"]).to_numpy()
        airborne = (p_now >= 0) & (p_now <= 1)
        traces = []
        for k, (label, _, _, color) in enumerate(DELAY_CLASSES):
            sel = np.where(airborne & (cls_idx == k))[0]
            sub = flown.iloc[sel]
            p = p_now[sel]
            lon, lat, alt = _arc(sub, p)
            # Traînée : de la position il y a trail_min minutes jusqu'à maintenant
            dur = (sub["landing_et"] - sub["takeoff_et"]).to_numpy(dtype=float)
            p_start = np.maximum(p - trail_min / dur, 0)
            pp = p_start[:, None] + (p - p_start)[:, None] * np.linspace(0, 1, 6)[None, :]
            tx, ty, tz = _arc(sub, pp)
            traces.append(go.Scatter3d(x=_with_breaks(tx), y=_with_breaks(ty), z=_with_breaks(tz), mode="lines",
                                       line={"color": color, "width": 3}, opacity=0.55, hoverinfo="skip",
                                       showlegend=False, name=f"traînée {label}"))
            traces.append(go.Scatter3d(
                x=lon, y=lat, z=alt, mode="markers", name=label,
                marker={"size": 4.2, "color": color, "symbol": "diamond", "line": {"color": "white", "width": 0.5}},
                customdata=np.c_[sub["airline_name"], sub["flight_number"], sub["origin_airport"], sub["destination_airport"],
                                 sub["departure_delay"].fillna(0).astype(int), sub["arrival_delay"].fillna(0).astype(int)],
                hovertemplate="<b>%{customdata[0]} %{customdata[1]}</b><br>%{customdata[2]} → %{customdata[3]}"
                              "<br>départ : %{customdata[4]:+d} min | arrivée : %{customdata[5]:+d} min<extra></extra>"))
        n_air = int(airborne.sum())
        late_air = int((airborne & (cls_idx > 0)).sum())
        landed = flown["landing_et"].to_numpy() <= t
        late_landed = 100 * (landed & (cls_idx > 0)).sum() / max(landed.sum(), 1)
        verbe = "arrivera" if late_air <= 1 else "arriveront"
        title = (f"<b>{_hhmm(t)}</b> (heure de l'Est)  ·  {n_air} avions en vol, dont {late_air} {verbe} en retard"
                 f"  ·  {late_landed:.0f} % des vols déjà posés étaient en retard")
        return traces, title

    times = np.arange(start_h * 60, end_h * 60 + 1, step_min)
    first_traces, first_title = dynamic_traces(times[0])
    for tr in first_traces:
        fig.add_trace(tr)
    dyn_idx = list(range(n_static, n_static + len(first_traces)))

    frames = []
    for t in times:
        trs, title = dynamic_traces(t)
        frames.append(go.Frame(data=trs, traces=dyn_idx, name=str(t), layout={"title": {"text": title}}))
    fig.frames = frames

    play = {"label": "▶ Lecture", "method": "animate",
            "args": [None, {"frame": {"duration": 140, "redraw": True}, "transition": {"duration": 0}, "fromcurrent": True}]}
    pause = {"label": "⏸ Pause", "method": "animate",
             "args": [[None], {"frame": {"duration": 0, "redraw": False}, "mode": "immediate"}]}
    axis = {"showbackground": True, "backgroundcolor": BG, "gridcolor": "rgba(148,163,184,0.12)",
            "zerolinecolor": "rgba(148,163,184,0.2)", "color": "#94a3b8"}
    fig.update_layout(
        template="plotly_dark", paper_bgcolor=BG, height=720, margin={"l": 0, "r": 0, "t": 60, "b": 0},
        title={"text": first_title, "x": 0.01, "font": {"size": 15}},
        legend={"orientation": "h", "y": 1.0, "x": 0.01, "bgcolor": "rgba(0,0,0,0)", "itemsizing": "constant"},
        scene={"xaxis": {**axis, "title": "Longitude", "range": list(CONTINENTAL["lon"])},
               "yaxis": {**axis, "title": "Latitude", "range": list(CONTINENTAL["lat"])},
               "zaxis": {**axis, "title": "", "range": [0, 4.2], "showticklabels": False},
               "aspectmode": "manual", "aspectratio": {"x": 2.2, "y": 1.0, "z": 0.45},
               "camera": {"eye": {"x": 0.35, "y": -1.55, "z": 0.95}, "center": {"x": 0, "y": 0, "z": -0.15}}},
        uirevision="replay",
        updatemenus=[{"type": "buttons", "direction": "left", "x": 0.01, "y": 0.02, "xanchor": "left", "yanchor": "bottom",
                      "pad": {"r": 8, "t": 0}, "showactive": False, "buttons": [play, pause],
                      "bgcolor": "#1e293b", "font": {"color": "#e2e8f0"}}],
        sliders=[{"active": 0, "x": 0.16, "y": 0.02, "len": 0.82, "yanchor": "bottom",
                  "currentvalue": {"visible": False}, "pad": {"t": 0}, "font": {"color": "#94a3b8", "size": 9},
                  "steps": [{"label": _hhmm(t) if (t % 60 == 0) else "", "method": "animate",
                             "args": [[str(t)], {"frame": {"duration": 0, "redraw": True}, "mode": "immediate"}]}
                            for t in times]}],
    )
    return fig


def _rate_rgb(rate: pd.Series, alpha: int) -> list:
    """Taux de retard (%) -> couleur RGBA : cyan (ponctuel) -> jaune -> rouge (≥ 30 %)."""
    x = np.clip((rate.to_numpy() - 10) / 20, 0, 1)
    r = np.where(x < 0.5, 34 + x * 2 * (250 - 34), 250 - (x - 0.5) * 2 * (250 - 239))
    g = np.where(x < 0.5, 211 + x * 2 * (204 - 211), 204 - (x - 0.5) * 2 * (204 - 68))
    b = np.where(x < 0.5, 238 - x * 2 * 238, 0 + (x - 0.5) * 2 * 68)
    return [[int(a), int(c), int(d), alpha] for a, c, d in zip(r, g, b)]


def build_network_deck(routes: pd.DataFrame) -> pdk.Deck:
    """Carte 3D de l'année : arcs des routes (couleur = % de retard) et colonnes des aéroports (hauteur = trafic)."""
    routes = routes.copy()
    routes["color"] = _rate_rgb(routes["taux_retard"], 170)
    routes["width"] = 0.5 + 4 * np.sqrt(routes["n_vols"] / routes["n_vols"].max())

    apt = (routes.assign(n_retards=routes["n_vols"] * routes["taux_retard"] / 100)
                 .groupby(["origin_airport", "origin_city", "origin_lon", "origin_lat"], as_index=False)
                 .agg(n_vols=("n_vols", "sum"), n_retards=("n_retards", "sum")))
    apt["taux_retard"] = (100 * apt["n_retards"] / apt["n_vols"]).round(1)
    apt["color"] = _rate_rgb(apt["taux_retard"], 230)

    arcs = pdk.Layer("ArcLayer", routes, get_source_position=["origin_lon", "origin_lat"],
                     get_target_position=["dest_lon", "dest_lat"], get_source_color="color", get_target_color="color",
                     get_width="width", get_height=0.6, great_circle=False, pickable=True, auto_highlight=True)
    columns = pdk.Layer("ColumnLayer", apt, get_position=["origin_lon", "origin_lat"], get_elevation="n_vols",
                        elevation_scale=60, radius=16000, get_fill_color="color", extruded=True, pickable=True,
                        auto_highlight=True)
    view = pdk.ViewState(latitude=37.5, longitude=-96, zoom=3.4, pitch=52, bearing=-12)
    tooltip = {"html": "<b>{origin_airport}</b> {origin_city}<br/>{n_vols} vols · {taux_retard} % en retard",
               "style": {"backgroundColor": "#0f172a", "color": "#e2e8f0"}}
    return pdk.Deck(layers=[arcs, columns], initial_view_state=view, map_provider="carto", map_style="dark", tooltip=tooltip)


@st.cache_data(show_spinner="Calcul de l'animation 3D…")
def _cached_replay(day: pd.DataFrame):
    return build_replay_figure(day)


def render(load_gold):
    st.header("Le ciel américain en 3D")
    replay = load_gold("flight_replay")
    if replay is not None:
        days = (replay[["flight_date", "day_label"]].drop_duplicates().sort_values("flight_date"))
        labels = [f"{r.day_label} — {pd.Timestamp(r.flight_date):%d/%m/%Y}" for r in days.itertuples()]
        choice = st.selectbox("Journée à rejouer", labels, index=0)
        date = days.iloc[labels.index(choice)]["flight_date"]
        day = replay[replay["flight_date"] == date]

        flown = day[~day["is_cancelled"].astype(bool)]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Vols de l'échantillon", f"{len(day):,}".replace(",", " "))
        c2.metric("Arrivés en retard (≥ 15 min)", f"{100 * (flown['arrival_delay'] >= 15).mean():.1f} %")
        c3.metric("Annulés", f"{100 * day['is_cancelled'].astype(bool).mean():.1f} %")
        c4.metric("Retard médian à l'arrivée", f"{flown['arrival_delay'].median():+.0f} min")

        st.plotly_chart(_cached_replay(day), width="stretch")
        st.caption("Faites pivoter la scène à la souris, puis ▶ Lecture. Chaque losange est un avion, coloré selon son retard "
                   "à l'arrivée ; la hauteur de l'arc grandit avec la distance. Échantillon de 5 % des vols (table Silver).")
        with st.expander("Requête SQL & méthode"):
            st.markdown(
                "Les horaires du dataset sont en **heure locale** de chaque aéroport : on les convertit en **heure de l'Est** "
                "(fuseau de l'État de départ et heure d'été 2015) pour que tous les avions partagent la même horloge. "
                "Décollage = départ prévu + retard au départ + roulage (`taxi_out`) ; atterrissage = décollage + `air_time`.\n\n"
                "Les journées sont choisies en Spark SQL avec des fenêtres `ROW_NUMBER()` sur le taux de retard quotidien.")
            st.code(
                "SELECT flight_date, COUNT(*) AS n_vols,\n"
                "       100 * AVG(CAST(is_delayed_15 AS INT)) AS taux_retard,\n"
                "       ROW_NUMBER() OVER (ORDER BY AVG(CAST(is_delayed_15 AS INT)) DESC) AS rang_pire,\n"
                "       ROW_NUMBER() OVER (ORDER BY AVG(CAST(is_delayed_15 AS INT)) ASC)  AS rang_meilleur\n"
                "FROM v_arrives WHERE airport_code_valid\nGROUP BY flight_date", language="sql")

    routes = load_gold("route_flows")
    if routes is not None:
        st.subheader("Le réseau sur l'année : routes et aéroports en 3D")
        col_a, col_b = st.columns(2)
        min_vols = col_a.slider("Vols minimum par route (échantillon)", 10, 150, 30, step=10)
        min_rate = col_b.slider("Taux de retard minimum de la route (%)", 0, 40, 0)
        sel = routes[(routes["n_vols"] >= min_vols) & (routes["taux_retard"] >= min_rate)]
        st.caption(f"{len(sel)} routes affichées. Arcs : couleur = % de retard (cyan → rouge). "
                   "Colonnes : hauteur = nombre de départs. Clic droit + glisser pour incliner la carte.")
        if len(sel):
            st.pydeck_chart(build_network_deck(sel), height=620)
        with st.expander("Requête SQL & justification"):
            st.code(
                "SELECT origin_airport, destination_airport, COUNT(*) AS n_vols,\n"
                "       ROUND(100 * AVG(CAST(is_delayed_15 AS INT)), 1) AS taux_retard,\n"
                "       PERCENTILE_APPROX(arrival_delay, 0.5) AS retard_median\n"
                "FROM v_arrives WHERE airport_code_valid\n"
                "GROUP BY origin_airport, destination_airport HAVING COUNT(*) >= 10", language="sql")
            st.markdown("Le taux de retard d'une route n'est fiable qu'avec assez de vols : le filtre « vols minimum » "
                        "évite d'afficher des taux calculés sur une poignée d'observations.")
