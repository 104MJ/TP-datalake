import json
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from pyspark.sql import SparkSession

st.set_page_config(
    page_title="Exo-Planette Lakehouse • Observatoire Interactif 2026",
    page_icon="🪐",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ==============================================================================
# STYLE COSMIQUE MODERNE & ÉLÉGANT
# ==============================================================================
st.markdown(
    """
    <style>
    .hero-banner {
        background: linear-gradient(135deg, #090d1f 0%, #172554 52%, #0f172a 100%);
        border: 1px solid rgba(99, 102, 241, 0.35);
        border-radius: 16px;
        padding: 1.4rem 1.8rem;
        margin-bottom: 1.1rem;
        color: #f8fafc;
        box-shadow: 0 10px 28px rgba(15, 23, 42, 0.28);
    }
    .hero-banner h1 {
        margin: 0 0 0.35rem 0;
        font-size: 1.95rem;
        background: linear-gradient(90deg, #e0e7ff, #38bdf8, #a78bfa);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .hero-sub {
        color: #cbd5e1;
        font-size: 0.96rem;
        margin: 0;
    }
    .kpi-card {
        background: linear-gradient(180deg, rgba(30, 41, 59, 0.92), rgba(15, 23, 42, 0.96));
        border: 1px solid rgba(148, 163, 184, 0.22);
        border-radius: 13px;
        padding: 0.95rem 1.1rem;
        color: #f1f5f9;
        height: 100%;
    }
    .kpi-label {
        font-size: 0.78rem;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: #94a3b8;
        margin-bottom: 0.25rem;
    }
    .kpi-val {
        font-size: 1.65rem;
        font-weight: 700;
        color: #38bdf8;
        line-height: 1.15;
    }
    .kpi-delta {
        font-size: 0.80rem;
        color: #cbd5e1;
        margin-top: 0.25rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

ARCHETYPE_COLORS = {
    "Jupiter Chaude (Hot Jupiter)": "#ef4444",
    "Géante Froide / Tempérée": "#f59e0b",
    "Mini-Neptune / Neptunienne": "#06b6d4",
    "Super-Terre Chaude / Lavique": "#a855f7",
    "Tellurique / Super-Terre Tempérée": "#10b981",
    "Non classée (données incomplètes)": "#64748b",
}

METHOD_COLORS = {
    "Transit": "#38bdf8",
    "Radial Velocity": "#f59e0b",
    "Microlensing": "#10b981",
    "Imaging": "#ec4899",
    "Transit Timing Variations": "#a78bfa",
    "Eclipse Timing Variations": "#fb7185",
    "Astrometry": "#fde047",
}

SOLAR_SYSTEM_REF = pd.DataFrame([
    {"name": "Mercure", "a_au": 0.387, "period_d": 87.97, "mass_e": 0.055, "rad_e": 0.383, "teq": 440, "seff": 6.67, "ecc": 0.2056},
    {"name": "Vénus",   "a_au": 0.723, "period_d": 224.70, "mass_e": 0.815, "rad_e": 0.949, "teq": 230, "seff": 1.91, "ecc": 0.0067},
    {"name": "Terre",   "a_au": 1.000, "period_d": 365.25, "mass_e": 1.000, "rad_e": 1.000, "teq": 255, "seff": 1.00, "ecc": 0.0167},
    {"name": "Mars",    "a_au": 1.524, "period_d": 686.98, "mass_e": 0.107, "rad_e": 0.532, "teq": 210, "seff": 0.43, "ecc": 0.0934},
    {"name": "Jupiter", "a_au": 5.203, "period_d": 4332.6, "mass_e": 317.83, "rad_e": 11.209, "teq": 110, "seff": 0.037, "ecc": 0.0489},
    {"name": "Saturne", "a_au": 9.537, "period_d": 10759.2, "mass_e": 95.16, "rad_e": 9.449, "teq": 81, "seff": 0.011, "ecc": 0.0565},
    {"name": "Neptune", "a_au": 30.07, "period_d": 60190.0, "mass_e": 17.15, "rad_e": 3.883, "teq": 47, "seff": 0.0011, "ecc": 0.0086},
])


# ==============================================================================
# CONNEXION HDFS + DELTA LAKE GOLD (CACHÉE)
# ==============================================================================
@st.cache_resource
def get_spark() -> SparkSession:
    return (
        SparkSession.builder
        .appName("StreamlitExoPlanetteGold")
        .config("spark.driver.memory", "768m")
        .config("spark.ui.enabled", "false")
        .getOrCreate()
    )


@st.cache_data(ttl=120)
def load_gold_delta(table_name: str) -> pd.DataFrame:
    spark = get_spark()
    return spark.read.format("delta").load(f"/lakehouse/gold/{table_name}").toPandas()


@st.cache_data(ttl=120)
def check_gold_ready() -> tuple[bool, list[str]]:
    spark = get_spark()
    jvm = spark._jvm
    fs = jvm.org.apache.hadoop.fs.FileSystem.get(spark._jsc.hadoopConfiguration())
    PathHDFS = jvm.org.apache.hadoop.fs.Path
    gold_root = PathHDFS("/lakehouse/gold")
    if not fs.exists(gold_root):
        return False, []
    found = sorted([
        s.getPath().getName()
        for s in fs.listStatus(gold_root)
        if s.isDirectory()
        and s.getPath().getName().startswith("exo_")
        and fs.exists(PathHDFS(s.getPath(), "_delta_log"))
    ])
    required = {
        "exo_planets_clustered",
        "exo_methods_bias",
        "exo_discovery_timeline",
        "exo_candidates_summary",
        "exo_tess_lightcurves",
        "exo_cluster_profiles",
        "exo_drift_audit",
        "exo_stats_tests",
    }
    return required.issubset(set(found)), found


# ==============================================================================
# UTILITAIRES MÉCANIQUE CÉLESTE KÉPLÉRIENNE & EXPORT UNIVERSE SANDBOX
# ==============================================================================
def solve_kepler(M: np.ndarray, e: float, n_iter: int = 8) -> np.ndarray:
    E = M + e * np.sin(M)
    for _ in range(n_iter):
        E = E - (E - e * np.sin(E) - M) / (1.0 - e * np.cos(E))
    return E


def star_color_from_teff(teff: float) -> str:
    if pd.isna(teff):
        return "#fde047"
    if teff >= 7500:
        return "#93c5fd"
    if teff >= 6000:
        return "#f8fafc"
    if teff >= 5200:
        return "#fde047"
    if teff >= 3700:
        return "#fb923c"
    return "#f87171"


def build_animated_orbits_2d(sys_df: pd.DataFrame, host_name: str, n_frames: int = 72, show_solar_inner: bool = False) -> go.Figure:
    sys_df = sys_df.sort_values("semi_major_axis_au_best").reset_index(drop=True)
    teff = float(sys_df["star_temperature_k"].dropna().iloc[0]) if sys_df["star_temperature_k"].notna().any() else 5778.0
    r_star = float(sys_df["star_radius_solar"].dropna().iloc[0]) if sys_df["star_radius_solar"].notna().any() else 1.0
    hz_in = float(sys_df["hz_inner_au"].dropna().iloc[0]) if sys_df["hz_inner_au"].notna().any() else None
    hz_out = float(sys_df["hz_outer_au"].dropna().iloc[0]) if sys_df["hz_outer_au"].notna().any() else None

    max_a = float(sys_df["semi_major_axis_au_best"].max())
    axis_lim = max_a * 1.30
    if hz_out and hz_out < max_a * 2.4:
        axis_lim = max(axis_lim, hz_out * 1.15)
    if show_solar_inner:
        axis_lim = max(axis_lim, 1.15)

    theta = np.linspace(0, 2 * np.pi, 220)
    traces = []

    # 1. Anneau de la Zone Habitable de Kopparapu
    if hz_in and hz_out and hz_out > hz_in:
        x_hz = np.concatenate([hz_out * np.cos(theta), hz_in * np.cos(theta[::-1]), [hz_out]])
        y_hz = np.concatenate([hz_out * np.sin(theta), hz_in * np.sin(theta[::-1]), [0.0]])
        traces.append(
            go.Scatter(
                x=x_hz,
                y=y_hz,
                fill="toself",
                fillcolor="rgba(34, 197, 94, 0.16)",
                line={"color": "rgba(34, 197, 94, 0.45)", "width": 1, "dash": "dot"},
                name=f"Zone Habitable [{hz_in:.3f} – {hz_out:.3f} UA]",
                hoverinfo="name",
            )
        )

    # 2. Orbites de référence du Système Solaire interne (optionnel)
    if show_solar_inner:
        for _, srow in SOLAR_SYSTEM_REF[SOLAR_SYSTEM_REF["a_au"] <= 1.6].iterrows():
            traces.append(
                go.Scatter(
                    x=srow["a_au"] * np.cos(theta),
                    y=srow["a_au"] * np.sin(theta),
                    mode="lines",
                    line={"color": "rgba(248, 250, 252, 0.28)", "width": 1, "dash": "dashdot"},
                    name=f"Orbite {srow['name']} ({srow['a_au']} UA)",
                    hoverinfo="name",
                )
            )

    # 3. Ellipses orbitales statiques de chaque exoplanète
    palette = px.colors.qualitative.Vivid + px.colors.qualitative.Bold
    p_min = float(sys_df["orbital_period_days"].min())
    orbital_params = []

    for idx, row in sys_df.iterrows():
        a = float(row["semi_major_axis_au_best"])
        e = float(row["eccentricity"]) if pd.notna(row["eccentricity"]) and 0 <= row["eccentricity"] < 0.92 else 0.0
        arg_p = idx * 0.55  # Orientation apsidale distincte quand ω non mesuré
        E_orb = solve_kepler(theta, e)
        x0 = a * (np.cos(E_orb) - e)
        y0 = a * np.sqrt(1.0 - e**2) * np.sin(E_orb)
        xr = x0 * np.cos(arg_p) - y0 * np.sin(arg_p)
        yr = x0 * np.sin(arg_p) + y0 * np.cos(arg_p)
        col = palette[idx % len(palette)]
        rp = float(row["radius_earth_est"]) if pd.notna(row["radius_earth_est"]) else 1.5
        orbital_params.append((row, a, e, arg_p, col, rp))

        traces.append(
            go.Scatter(
                x=xr,
                y=yr,
                mode="lines",
                line={"color": col, "width": 1.6, "dash": "dot"},
                opacity=0.65,
                name=f"Orbite {row['planet_name']} (P={row['orbital_period_days']:.2f}j)",
                hoverinfo="name",
                showlegend=False,
            )
        )

    # 4. Étoile hôte au foyer (0, 0)
    traces.append(
        go.Scatter(
            x=[0.0],
            y=[0.0],
            mode="markers+text",
            marker={
                "size": float(np.clip(22 + 8 * r_star, 20, 42)),
                "color": star_color_from_teff(teff),
                "line": {"color": "#ffffff", "width": 2},
                "symbol": "circle",
            },
            text=[f"★ {host_name}"],
            textposition="top center",
            textfont={"color": "#f8fafc", "size": 11},
            name=f"Étoile {host_name} ({teff:.0f} K, {r_star:.2f} R☉)",
            hovertemplate=f"<b>{host_name}</b><br>T_eff = {teff:.0f} K<br>Rayon = {r_star:.2f} R☉<extra></extra>",
        )
    )

    # Indice de la trace dynamique des planètes + sillages
    # Pour une animation fluide à 60 FPS dans Plotly, un unique trace de marqueurs animés + un trace de sillages multi-segments
    def frame_positions(step_idx: int):
        # La planète interne accomplit 2 révolutions complètes sur l'ensemble des frames
        t_days = (step_idx / n_frames) * (2.0 * p_min)
        px_list, py_list, sz_list, col_list, lbl_list, hov_list = [], [], [], [], [], []
        tx_all, ty_all = [], []

        for idx, (row, a, e, arg_p, col, rp) in enumerate(orbital_params):
            per = float(row["orbital_period_days"])
            phase0 = idx * 1.15
            M_now = (phase0 + 2.0 * np.pi * (t_days / per)) % (2.0 * np.pi)
            E_now = float(solve_kepler(np.array([M_now]), e)[0])
            x_c = a * (np.cos(E_now) - e)
            y_c = a * np.sqrt(1.0 - e**2) * np.sin(E_now)
            x_rot = x_c * np.cos(arg_p) - y_c * np.sin(arg_p)
            y_rot = x_c * np.sin(arg_p) + y_c * np.cos(arg_p)

            px_list.append(x_rot)
            py_list.append(y_rot)
            sz_list.append(float(np.clip(9.0 + 5.5 * np.sqrt(rp), 10.0, 34.0)))
            col_list.append(col)
            short_p = str(row["planet_letter"] or row["planet_name"].split()[-1])
            lbl_list.append(f" {short_p}")
            teq_str = f"{row['equilibrium_temp_k_best']:.0f} K" if pd.notna(row["equilibrium_temp_k_best"]) else "N/A"
            hov_list.append(
                f"<b>{row['planet_name']}</b><br>"
                f"Archétype : {row['planet_archetype']}<br>"
                f"Demi-grand axe : {a:.4f} UA | e = {e:.3f}<br>"
                f"Période : {per:.2f} jours<br>"
                f"Rayon : {rp:.2f} R⊕ | T_eq : {teq_str}"
            )

            # Sillage des 18 derniers instants sur la trajectoire képlérienne
            m_trail = np.linspace(M_now - 0.85, M_now, 20)
            E_trail = solve_kepler(m_trail, e)
            xt0 = a * (np.cos(E_trail) - e)
            yt0 = a * np.sqrt(1.0 - e**2) * np.sin(E_trail)
            tx_all.extend((xt0 * np.cos(arg_p) - yt0 * np.sin(arg_p)).tolist() + [None])
            ty_all.extend((xt0 * np.sin(arg_p) + yt0 * np.cos(arg_p)).tolist() + [None])

        return t_days, px_list, py_list, sz_list, col_list, lbl_list, hov_list, tx_all, ty_all

    _, px0, py0, sz0, col0, lbl0, hov0, tx0, ty0 = frame_positions(0)
    trail_trace_idx = len(traces)
    traces.append(
        go.Scatter(
            x=tx0,
            y=ty0,
            mode="lines",
            line={"color": "rgba(56, 189, 248, 0.60)", "width": 3},
            name="Sillage képlérien",
            hoverinfo="skip",
        )
    )
    planet_trace_idx = len(traces)
    traces.append(
        go.Scatter(
            x=px0,
            y=py0,
            mode="markers+text",
            marker={"size": sz0, "color": col0, "line": {"color": "white", "width": 1.3}},
            text=lbl0,
            textposition="top right",
            textfont={"color": "#e2e8f0", "size": 11},
            customdata=hov0,
            hovertemplate="%{customdata}<extra></extra>",
            name="Exoplanètes en orbite",
        )
    )

    frames = []
    slider_steps = []
    for k in range(n_frames):
        t_d, pxk, pyk, _, _, lblk, hovk, txk, tyk = frame_positions(k)
        fname = f"f{k}"
        frames.append(
            go.Frame(
                name=fname,
                traces=[trail_trace_idx, planet_trace_idx],
                data=[
                    go.Scatter(x=txk, y=tyk),
                    go.Scatter(x=pxk, y=pyk, text=lblk, customdata=hovk),
                ],
            )
        )
        slider_steps.append({
            "args": [[fname], {"frame": {"duration": 55, "redraw": False}, "mode": "immediate", "transition": {"duration": 0}}],
            "label": f"t = {t_d:.1f} j",
            "method": "animate",
        })

    fig = go.Figure(data=traces, frames=frames)
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#070b19",
        plot_bgcolor="#070b19",
        height=620,
        margin={"l": 20, "r": 20, "t": 55, "b": 40},
        title=f"Animation Képlérienne Exacte — Système {host_name} ({len(sys_df)} planètes, M = E − e·sin E)",
        xaxis={"range": [-axis_lim, axis_lim], "title": "Position X (Unités Astronomiques — UA)", "zeroline": False, "gridcolor": "rgba(148,163,184,0.12)"},
        yaxis={"range": [-axis_lim, axis_lim], "title": "Position Y (UA)", "scaleanchor": "x", "scaleratio": 1, "zeroline": False, "gridcolor": "rgba(148,163,184,0.12)"},
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.01, "x": 0},
        updatemenus=[{
            "type": "buttons",
            "showactive": False,
            "x": 0.01,
            "y": 0.02,
            "xanchor": "left",
            "yanchor": "bottom",
            "bgcolor": "#1e293b",
            "bordercolor": "#38bdf8",
            "font": {"color": "#f8fafc"},
            "buttons": [
                {
                    "label": "▶ Lancer l'orbite",
                    "method": "animate",
                    "args": [None, {"frame": {"duration": 55, "redraw": False}, "fromcurrent": True, "transition": {"duration": 0}}],
                },
                {
                    "label": "⏸ Pause",
                    "method": "animate",
                    "args": [[None], {"frame": {"duration": 0, "redraw": False}, "mode": "immediate"}],
                },
            ],
        }],
        sliders=[{
            "active": 0,
            "pad": {"t": 35, "b": 5},
            "currentvalue": {"prefix": "Temps orbital simulé : ", "font": {"color": "#38bdf8"}},
            "steps": slider_steps,
        }],
    )
    return fig


def build_orbits_3d(sys_df: pd.DataFrame, host_name: str) -> go.Figure:
    sys_df = sys_df.sort_values("semi_major_axis_au_best").reset_index(drop=True)
    teff = float(sys_df["star_temperature_k"].dropna().iloc[0]) if sys_df["star_temperature_k"].notna().any() else 5778.0
    hz_in = float(sys_df["hz_inner_au"].dropna().iloc[0]) if sys_df["hz_inner_au"].notna().any() else None
    hz_out = float(sys_df["hz_outer_au"].dropna().iloc[0]) if sys_df["hz_outer_au"].notna().any() else None

    theta = np.linspace(0, 2 * np.pi, 180)
    fig = go.Figure()

    # Anneau 3D de la Zone Habitable dans le plan invariant z = 0
    if hz_in and hz_out:
        for r_hz, lbl in [(hz_in, "Limite interne HZ"), (hz_out, "Limite externe HZ")]:
            fig.add_trace(
                go.Scatter3d(
                    x=r_hz * np.cos(theta),
                    y=r_hz * np.sin(theta),
                    z=np.zeros_like(theta),
                    mode="lines",
                    line={"color": "#22c55e", "width": 3, "dash": "dash"},
                    name=lbl,
                )
            )

    # Étoile au foyer (0, 0, 0)
    fig.add_trace(
        go.Scatter3d(
            x=[0.0],
            y=[0.0],
            z=[0.0],
            mode="markers+text",
            marker={"size": 14, "color": star_color_from_teff(teff), "line": {"color": "white", "width": 2}},
            text=[host_name],
            name=f"Étoile {host_name} ({teff:.0f} K)",
        )
    )

    palette = px.colors.qualitative.Vivid + px.colors.qualitative.Bold
    for idx, row in sys_df.iterrows():
        a = float(row["semi_major_axis_au_best"])
        e = float(row["eccentricity"]) if pd.notna(row["eccentricity"]) and 0 <= row["eccentricity"] < 0.92 else 0.0
        # Inclinaison par rapport au plan de référence (90° = edge-on transit -> 0° de déviation coplanaire)
        inc_deg = float(row["orbital_inclination_deg"]) - 90.0 if pd.notna(row["orbital_inclination_deg"]) else (idx * 2.2)
        inc_rad = np.deg2rad(inc_deg)
        omega = idx * 0.7

        E_orb = solve_kepler(theta, e)
        xp = a * (np.cos(E_orb) - e)
        yp = a * np.sqrt(1.0 - e**2) * np.sin(E_orb)

        x3 = xp * np.cos(omega) - yp * np.sin(omega) * np.cos(inc_rad)
        y3 = xp * np.sin(omega) + yp * np.cos(omega) * np.cos(inc_rad)
        z3 = yp * np.sin(inc_rad)
        col = palette[idx % len(palette)]

        fig.add_trace(
            go.Scatter3d(
                x=x3,
                y=y3,
                z=z3,
                mode="lines",
                line={"color": col, "width": 4},
                name=f"{row['planet_name']} (P={row['orbital_period_days']:.1f}j)",
            )
        )
        pos_i = (idx * 29) % len(theta)
        rp = float(row["radius_earth_est"]) if pd.notna(row["radius_earth_est"]) else 1.5
        fig.add_trace(
            go.Scatter3d(
                x=[x3[pos_i]],
                y=[y3[pos_i]],
                z=[z3[pos_i]],
                mode="markers",
                marker={"size": float(np.clip(5 + 3.5 * np.sqrt(rp), 6, 20)), "color": col, "line": {"color": "white", "width": 1}},
                showlegend=False,
                hovertemplate=f"<b>{row['planet_name']}</b><br>a = {a:.4f} UA | e = {e:.3f}<br>Δi = {inc_deg:+.2f}°<extra></extra>",
            )
        )

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#070b19",
        height=580,
        margin={"l": 0, "r": 0, "t": 45, "b": 0},
        title=f"Architecture 3D Inclinée — {host_name} (faites pivoter à la souris)",
        scene={
            "xaxis": {"title": "X (UA)", "backgroundcolor": "#070b19", "gridcolor": "rgba(148,163,184,0.15)"},
            "yaxis": {"title": "Y (UA)", "backgroundcolor": "#070b19", "gridcolor": "rgba(148,163,184,0.15)"},
            "zaxis": {"title": "Z hors-plan (UA)", "backgroundcolor": "#070b19", "gridcolor": "rgba(148,163,184,0.15)"},
            "aspectmode": "data",
        },
    )
    return fig


def export_universe_sandbox_json(sys_df: pd.DataFrame, host_name: str) -> str:
    AU_M = 1.495978707e11
    SOLAR_MASS_KG = 1.98847e30
    SOLAR_RAD_M = 6.9634e8
    EARTH_MASS_KG = 5.9722e24
    EARTH_RAD_M = 6.371e6
    G_SI = 6.67430e-11

    sys_df = sys_df.sort_values("semi_major_axis_au_best")
    m_star = float(sys_df["star_mass_solar"].dropna().iloc[0]) if sys_df["star_mass_solar"].notna().any() else 1.0
    r_star = float(sys_df["star_radius_solar"].dropna().iloc[0]) if sys_df["star_radius_solar"].notna().any() else 1.0
    t_star = float(sys_df["star_temperature_k"].dropna().iloc[0]) if sys_df["star_temperature_k"].notna().any() else 5778.0

    payload = {
        "system_name": host_name,
        "generated_from": "HDFS Delta Lake Gold (/lakehouse/gold/exo_planets_clustered)",
        "star": {
            "name": host_name,
            "mass_kg": m_star * SOLAR_MASS_KG,
            "radius_m": r_star * SOLAR_RAD_M,
            "temperature_k": t_star,
            "position_m": [0.0, 0.0, 0.0],
            "velocity_ms": [0.0, 0.0, 0.0],
        },
        "planets": [],
    }
    for _, row in sys_df.iterrows():
        a_m = float(row["semi_major_axis_au_best"]) * AU_M
        e = float(row["eccentricity"]) if pd.notna(row["eccentricity"]) and 0 <= row["eccentricity"] < 0.95 else 0.0
        mp_kg = float(row["mass_earth_est"] if pd.notna(row["mass_earth_est"]) else 1.0) * EARTH_MASS_KG
        rp_m = float(row["radius_earth_est"] if pd.notna(row["radius_earth_est"]) else 1.0) * EARTH_RAD_M
        r_peri = a_m * (1.0 - e)
        v_peri = float(np.sqrt((G_SI * m_star * SOLAR_MASS_KG / a_m) * ((1.0 + e) / (1.0 - e))))
        payload["planets"].append({
            "name": str(row["planet_name"]),
            "archetype": str(row["planet_archetype"]),
            "mass_kg": mp_kg,
            "radius_m": rp_m,
            "semi_major_axis_au": float(row["semi_major_axis_au_best"]),
            "orbital_period_days": float(row["orbital_period_days"]),
            "eccentricity": e,
            "position_m": [r_peri, 0.0, 0.0],
            "velocity_ms": [0.0, v_peri, 0.0],
        })
    return json.dumps(payload, indent=2, ensure_ascii=False)


# ==============================================================================
# CHARGEMENT INITIAL & CONTRÔLE DE L'ÉTAT DU CLUSTER
# ==============================================================================
st.markdown(
    """
    <div class="hero-banner">
        <h1>🪐 Exo-Planette Lakehouse — Observatoire Dynamique 2026</h1>
        <p class="hero-sub">
            Architecture <b>HDFS 3.5 (3 DataNodes, blocs 16 Mo)</b> • <b>PySpark 4.2</b> • <b>Delta Lake 4.4 (Bronze → Silver → Gold)</b> •
            Cycle complet <i>Data Detective</i> en 7 étapes : Orbites Képlériennes, Biais Instrumentaux, Courbes TESS, Taxonomie K-Means & Mondes Habitables.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

ready, existing_gold = check_gold_ready()
if not ready:
    st.warning(
        "⚠️ Les tables Delta Lake `/lakehouse/gold/exo_*` ne sont pas encore toutes générées sur HDFS. "
        "Exécutez les notebooks `01` à `05` dans le dossier `notebooks/example/exo-planette/` pour alimenter le Lakehouse !"
    )
    st.write("Tables Gold actuellement détectées :", existing_gold)
    st.stop()

planets_df = load_gold_delta("exo_planets_clustered")
methods_df = load_gold_delta("exo_methods_bias")
timeline_df = load_gold_delta("exo_discovery_timeline")
cand_df = load_gold_delta("exo_candidates_summary")
lc_df = load_gold_delta("exo_tess_lightcurves")
profiles_df = load_gold_delta("exo_cluster_profiles")
drift_df = load_gold_delta("exo_drift_audit")
tests_df = load_gold_delta("exo_stats_tests")

# ==============================================================================
# BARRE LATÉRALE : FILTRES GLOBAUX & ÉTAT DU LAKEHOUSE
# ==============================================================================
with st.sidebar:
    st.markdown("### 🛰️ Filtres d'Investigation")
    min_yr = int(planets_df["discovery_year"].dropna().min())
    max_yr = int(planets_df["discovery_year"].dropna().max())
    year_range = st.slider("Années de découverte", min_yr, max_yr, (min_yr, max_yr))

    all_methods = methods_df["discovery_method"].tolist()
    selected_methods = st.multiselect(
        "Méthodes de détection",
        options=all_methods,
        default=all_methods[:5],
    )

    archetype_opts = [a for a in ARCHETYPE_COLORS if a in set(planets_df["planet_archetype"])]
    selected_archetypes = st.multiselect(
        "Archétypes K-Means",
        options=archetype_opts,
        default=archetype_opts,
    )

    st.divider()
    st.caption(
        f"✅ Connecté à `hdfs://namenode:9000/lakehouse/gold/`\n\n"
        f"• **{len(existing_gold)} tables Delta Gold** actives\n"
        f"• Cache mémoire Streamlit TTL = 120s"
    )
    if st.button("🔄 Rafraîchir le cache HDFS"):
        st.cache_data.clear()
        st.rerun()

filtered_df = planets_df[
    planets_df["discovery_year"].between(year_range[0], year_range[1])
    & planets_df["discovery_method"].isin(selected_methods or all_methods)
    & planets_df["planet_archetype"].isin(selected_archetypes or archetype_opts)
].copy()

# Cartes KPI en tête de page
n_confirmed = len(filtered_df)
n_multi_sys = int(filtered_df.loc[filtered_df["planets_in_system"] >= 2, "host_star"].nunique())
n_hz_cons = int(filtered_df["habitable_zone_status"].str.startswith("Conservatrice", na=False).sum())
best_esi_row = filtered_df.dropna(subset=["esi_score"]).sort_values("esi_score", ascending=False).head(1)
best_esi_txt = f"{best_esi_row['esi_score'].iloc[0]:.3f} ({best_esi_row['planet_name'].iloc[0]})" if len(best_esi_row) else "N/A"
median_p = float(filtered_df["orbital_period_days"].median()) if len(filtered_df) else 0.0

k1, k2, k3, k4 = st.columns(4)
with k1:
    st.markdown(
        f'<div class="kpi-card"><div class="kpi-label">Exoplanètes filtrées (Catalogue 2026)</div>'
        f'<div class="kpi-val">{n_confirmed:,}</div>'
        f'<div class="kpi-delta">sur {len(planets_df):,} mondes uniques consolidés</div></div>',
        unsafe_allow_html=True,
    )
with k2:
    st.markdown(
        f'<div class="kpi-card"><div class="kpi-label">Systèmes Multi-Planétaires</div>'
        f'<div class="kpi-val">{n_multi_sys:,}</div>'
        f'<div class="kpi-delta">Période orbitale médiane : {median_p:.1f} jours</div></div>',
        unsafe_allow_html=True,
    )
with k3:
    st.markdown(
        f'<div class="kpi-card"><div class="kpi-label">Mondes en Zone Habitable Conservatrice</div>'
        f'<div class="kpi-val">{n_hz_cons}</div>'
        f'<div class="kpi-delta">Flux Kopparapu [0,35 – 1,11 S⊕]</div></div>',
        unsafe_allow_html=True,
    )
with k4:
    st.markdown(
        f'<div class="kpi-card"><div class="kpi-label">Record Similarité Terrestre (ESI)</div>'
        f'<div class="kpi-val">{best_esi_txt.split()[0]}</div>'
        f'<div class="kpi-delta">{best_esi_txt}</div></div>',
        unsafe_allow_html=True,
    )

st.write("")

# ==============================================================================
# NAVIGATION PAR ONGLETS NARRATIFS
# ==============================================================================
tabs = st.tabs([
    "🪐 Planétarium & Orbites Animées",
    "🔭 Biais de Découverte & Courbes TESS",
    "🧠 Taxonomie K-Means & Drift MLOps",
    "🌌 Panorama, Animation 1995–2026 & Galaxie",
    "🌍 Chasse aux Mondes Habitables (ESI)",
    "📜 Conclusions, Stats SciPy & SQL",
])

# ------------------------------------------------------------------------------
# ONGLET 1 : PLANÉTARIUM INTERACTIF & ANIMATIONS ORBITALES KÉPLÉRIENNES (2D & 3D)
# ------------------------------------------------------------------------------
with tabs[0]:
    st.subheader("🪐 Simulateur Képlérien Dynamique des Systèmes Exoplanétaires")
    st.markdown(
        "Sélectionnez un système planétaire issu de `/lakehouse/gold/exo_planets_clustered` : les orbites elliptiques sont calculées en "
        "résolvant l'**équation de Kepler exacte** ($M = E - e\\sin E$) avec l'étoile au foyer $(0,0)$ et l'**anneau vert de la Zone Habitable**."
    )

    valid_orbit_planets = planets_df.dropna(subset=["semi_major_axis_au_best", "orbital_period_days"])
    sys_counts = (
        valid_orbit_planets.groupby("host_star")
        .agg(
            n_pl=("planet_name", "count"),
            n_hz=("habitable_zone_status", lambda s: int(s.str.startswith("Conservatrice", na=False).sum())),
            teff=("star_temperature_k", "first"),
        )
        .query("n_pl >= 2")
        .sort_values(["n_pl", "n_hz"], ascending=[False, False])
    )

    featured_first = ["TRAPPIST-1", "HD 110067", "Kepler-90", "Kepler-11", "55 Cnc", "TOI-178", "Kepler-186", "TOI-700"]
    ordered_hosts = [h for h in featured_first if h in sys_counts.index] + [h for h in sys_counts.index if h not in featured_first]
    host_labels = {
        h: f"{h} — {int(sys_counts.loc[h, 'n_pl'])} planètes"
           + (f" ({int(sys_counts.loc[h, 'n_hz'])} en Zone Habitable 🌍)" if sys_counts.loc[h, "n_hz"] > 0 else "")
        for h in ordered_hosts
    }

    c_sel1, c_sel2, c_sel3 = st.columns([2.3, 1.2, 1.3])
    with c_sel1:
        chosen_host = st.selectbox("Système stellaire à explorer", options=ordered_hosts, format_func=lambda h: host_labels[h])
    with c_sel2:
        n_anim_frames = st.select_slider("Finesse de l'animation", options=[48, 72, 96, 120], value=72)
    with c_sel3:
        compare_solar = st.checkbox("Superposer Mercure/Vénus/Terre", value=(chosen_host == "TRAPPIST-1"))

    sys_sub = valid_orbit_planets[valid_orbit_planets["host_star"] == chosen_host].sort_values("semi_major_axis_au_best")

    col_2d, col_3d = st.columns([1.25, 1.0])
    with col_2d:
        fig_2d = build_animated_orbits_2d(sys_sub, chosen_host, n_frames=n_anim_frames, show_solar_inner=compare_solar)
        st.plotly_chart(fig_2d, width="stretch")
    with col_3d:
        fig_3d = build_orbits_3d(sys_sub, chosen_host)
        st.plotly_chart(fig_3d, width="stretch")

    # Comparateur d'échelle des rayons planétaires face à la Terre, Neptune et Jupiter
    st.markdown(f"#### 📏 Échelle Comparative des Tailles — Système `{chosen_host}` vs Terre & Neptune")
    comp_items = [
        {"Corps": "🌍 Terre (Réf.)", "Rayon (R⊕)": 1.0, "Temp. Éq (K)": 255.0, "Famille": "Référence Système Solaire"},
        {"Corps": "🔵 Neptune (Réf.)", "Rayon (R⊕)": 3.883, "Temp. Éq (K)": 47.0, "Famille": "Référence Système Solaire"},
    ]
    for _, r in sys_sub.iterrows():
        comp_items.append({
            "Corps": r["planet_name"],
            "Rayon (R⊕)": float(r["radius_earth_est"]) if pd.notna(r["radius_earth_est"]) else 1.0,
            "Temp. Éq (K)": float(r["equilibrium_temp_k_best"]) if pd.notna(r["equilibrium_temp_k_best"]) else 300.0,
            "Famille": r["planet_archetype"],
        })
    comp_df = pd.DataFrame(comp_items)
    comp_df["x_pos"] = np.arange(len(comp_df))
    comp_df["y_pos"] = 0

    fig_sizes = px.scatter(
        comp_df,
        x="x_pos",
        y="y_pos",
        size="Rayon (R⊕)",
        color="Famille",
        text="Corps",
        size_max=68,
        color_discrete_map={**ARCHETYPE_COLORS, "Référence Système Solaire": "#38bdf8"},
        hover_data={"Rayon (R⊕)": ":.2f", "Temp. Éq (K)": ":.0f", "x_pos": False, "y_pos": False},
        template="plotly_dark",
    )
    fig_sizes.update_traces(textposition="top center")
    fig_sizes.update_layout(
        height=270,
        paper_bgcolor="#070b19",
        plot_bgcolor="#070b19",
        xaxis={"visible": False, "range": [-0.8, len(comp_df) - 0.2]},
        yaxis={"visible": False, "range": [-1.0, 1.35]},
        margin={"l": 10, "r": 10, "t": 15, "b": 10},
    )
    st.plotly_chart(fig_sizes, width="stretch")

    c_tbl, c_dl = st.columns([3.2, 1.0])
    with c_tbl:
        st.dataframe(
            sys_sub[[
                "planet_name", "planet_archetype", "orbital_period_days", "semi_major_axis_au_best",
                "eccentricity", "radius_earth_est", "mass_earth_est", "equilibrium_temp_k_best",
                "habitable_zone_status", "esi_score",
            ]].rename(columns={
                "planet_name": "Planète",
                "planet_archetype": "Archétype K-Means",
                "orbital_period_days": "Période (j)",
                "semi_major_axis_au_best": "Demi-grand axe (UA)",
                "eccentricity": "Excentricité e",
                "radius_earth_est": "Rayon (R⊕)",
                "mass_earth_est": "Masse (M⊕)",
                "equilibrium_temp_k_best": "T_eq (K)",
                "habitable_zone_status": "Zone Habitable",
                "esi_score": "Score ESI",
            }),
            width="stretch",
            hide_index=True,
        )
    with c_dl:
        usim_json = export_universe_sandbox_json(sys_sub, chosen_host)
        st.download_button(
            label=f"⬇️ Exporter {chosen_host} (Universe Sandbox JSON)",
            data=usim_json,
            file_name=f"{chosen_host.replace(' ', '_')}_universe_sandbox.json",
            mime="application/json",
            width="stretch",
        )
        st.caption("Inclut masses/rayons en unités SI et vecteurs vitesse périhéliques exacts ($v_p$).")

# ------------------------------------------------------------------------------
# ONGLET 2 : BIAIS DE DÉCOUVERTE, SIMULATEUR DE TÉLESCOPE & COURBES TESS
# ------------------------------------------------------------------------------
with tabs[1]:
    st.subheader("🔭 Pourquoi le Catalogue est-il Biaisé ? Simulateur Physique des Limites Instrumentales")
    st.markdown(
        "Ajustez les paramètres de votre observatoire virtuel ci-dessous pour visualiser **comment les lois physiques du Transit et de "
        "l'Effet Doppler sculptent artificiellement la population d'exoplanètes observées** — et pourquoi les analogues à la Terre, Mars ou Saturne "
        "demeurent dans l'angle mort actuel."
    )

    sim1, sim2, sim3 = st.columns(3)
    with sim1:
        transit_ppm_limit = st.slider(
            "Seuil photométrique Transit ΔF/F (ppm)",
            min_value=10,
            max_value=1000,
            value=80,
            step=10,
            help="Terre devant le Soleil = 84 ppm ; Jupiter devant le Soleil = 10 000 ppm (1%).",
        )
    with sim2:
        campaign_years = st.slider(
            "Durée continue de mission Transit (années)",
            min_value=0.2,
            max_value=10.0,
            value=4.0,
            step=0.2,
            help="Il faut observer au moins 3 transits consécutifs : P_max = Durée / 3 (Kepler = 4 ans -> ~487 j ; secteur TESS = 27 j !).",
        )
    with sim3:
        rv_limit_ms = st.slider(
            "Précision Doppler Vitesse Radiale K (m/s)",
            min_value=0.05,
            max_value=5.0,
            value=0.80,
            step=0.05,
            help="HARPS ≈ 0.8 m/s ; ESPRESSO ≈ 0.1 m/s ; Signal réflexe de la Terre sur le Soleil = 0.09 m/s !",
        )

    max_transit_period_d = (campaign_years * 365.25) / 3.0
    min_transit_rad_earth = np.sqrt(transit_ppm_limit * 1e-6) * 109.076  # autour d'une étoile solaire 1 R_sun

    # Test de détectabilité de notre propre Système Solaire avec ce télescope virtuel (observateur ayant la chance d'être aligné ou en Doppler)
    ss_eval = SOLAR_SYSTEM_REF.copy()
    ss_eval["K_doppler_ms"] = 28.4 * (ss_eval["mass_e"] / 317.83) * np.power(ss_eval["period_d"] / 365.25, -1.0 / 3.0)
    ss_eval["depth_ppm"] = ((ss_eval["rad_e"] / 109.076) ** 2) * 1e6
    ss_eval["geom_prob_pct"] = np.minimum(100.0, 100.0 * 0.00465047 / ss_eval["a_au"])
    ss_eval["Détectable Transit (si aligné)"] = (ss_eval["depth_ppm"] >= transit_ppm_limit) & (ss_eval["period_d"] <= max_transit_period_d)
    ss_eval["Détectable Doppler RV"] = ss_eval["K_doppler_ms"] >= rv_limit_ms

    n_ss_tr = int(ss_eval["Détectable Transit (si aligné)"].sum())
    n_ss_rv = int(ss_eval["Détectable Doppler RV"].sum())
    st.info(
        f"🎯 **Verdict sur le Système Solaire vu d'une autre étoile avec vos réglages :** "
        f"en **Transit** (même avec l'alignement géométrique rare de $0,47\\%$ à 1 UA !), seules **{n_ss_tr}/7 planètes** franchissent "
        f"$R_p \\ge {min_transit_rad_earth:.2f}\\,R_\\oplus$ et $P \\le {max_transit_period_d:.0f}\\text{{ j}}$ ; "
        f"en **Vitesse Radiale ($K \\ge {rv_limit_ms:.2f}$ m/s)**, **{n_ss_rv}/7 planètes** émergent du bruit stellaire !"
    )

    b_col1, b_col2 = st.columns(2)
    with b_col1:
        bias_sub = filtered_df.dropna(subset=["semi_major_axis_au_best", "mass_earth_est"]).query("semi_major_axis_au_best > 0 and mass_earth_est > 0")
        fig_rv_bias = px.scatter(
            bias_sub,
            x="semi_major_axis_au_best",
            y="mass_earth_est",
            color="discovery_method",
            color_discrete_map=METHOD_COLORS,
            log_x=True,
            log_y=True,
            opacity=0.58,
            hover_name="planet_name",
            hover_data={"orbital_period_days": ":.2f", "radius_earth_est": ":.2f", "distance_parsec": ":.1f"},
            labels={"semi_major_axis_au_best": "Demi-grand axe a (UA)", "mass_earth_est": "Masse planétaire M_p (M⊕)", "discovery_method": "Méthode"},
            title="Espace (a, M_p) : Seuil Doppler K(a) & Fenêtre Microlentille / Imagerie",
            template="plotly_dark",
        )
        a_line = np.logspace(-2.3, 3.3, 220)
        m_min_rv = (rv_limit_ms / 28.4) * 317.83 * np.sqrt(a_line)
        fig_rv_bias.add_trace(
            go.Scatter(
                x=a_line,
                y=m_min_rv,
                mode="lines",
                line={"color": "#fde047", "width": 3, "dash": "dash"},
                name=f"Limite Doppler K = {rv_limit_ms:.2f} m/s (1 M☉)",
            )
        )
        fig_rv_bias.add_trace(
            go.Scatter(
                x=SOLAR_SYSTEM_REF["a_au"],
                y=SOLAR_SYSTEM_REF["mass_e"],
                mode="markers+text",
                marker={"size": 13, "symbol": "star", "color": "#f43f5e", "line": {"color": "white", "width": 1}},
                text=SOLAR_SYSTEM_REF["name"],
                textposition="top center",
                name="Système Solaire",
            )
        )
        fig_rv_bias.update_layout(height=500, xaxis_range=[-2.3, 3.3], yaxis_range=[-1.7, 4.3])
        st.plotly_chart(fig_rv_bias, width="stretch")

    with b_col2:
        bias_tr = filtered_df.dropna(subset=["orbital_period_days", "radius_earth_est"]).query("orbital_period_days > 0 and radius_earth_est > 0")
        fig_tr_bias = px.scatter(
            bias_tr,
            x="orbital_period_days",
            y="radius_earth_est",
            color="discovery_method",
            color_discrete_map=METHOD_COLORS,
            log_x=True,
            log_y=True,
            opacity=0.55,
            hover_name="planet_name",
            labels={"orbital_period_days": "Période orbitale P (jours)", "radius_earth_est": "Rayon R_p (R⊕)", "discovery_method": "Méthode"},
            title="Espace (P, R_p) : Fenêtre de Transit (ΔF/F & ≥ 3 Transits)",
            template="plotly_dark",
        )
        fig_tr_bias.add_hline(y=min_transit_rad_earth, line_dash="dash", line_color="#38bdf8", annotation_text=f"R_min = {min_transit_rad_earth:.2f} R⊕ ({transit_ppm_limit} ppm)")
        fig_tr_bias.add_vline(x=max_transit_period_d, line_dash="dot", line_color="#fb7185", annotation_text=f"P_max (3 transits) = {max_transit_period_d:.0f} j")
        fig_tr_bias.add_trace(
            go.Scatter(
                x=SOLAR_SYSTEM_REF["period_d"],
                y=SOLAR_SYSTEM_REF["rad_e"],
                mode="markers+text",
                marker={"size": 13, "symbol": "star", "color": "#f43f5e", "line": {"color": "white", "width": 1}},
                text=SOLAR_SYSTEM_REF["name"],
                textposition="top center",
                name="Système Solaire",
            )
        )
        fig_tr_bias.update_layout(height=500, xaxis_range=[-1.1, 5.3], yaxis_range=[-0.6, 1.5])
        st.plotly_chart(fig_tr_bias, width="stretch")

    # Courbes de lumière réelles TESS & Entonnoir des faux positifs
    st.markdown("#### 📉 Vraies Courbes de Lumière Photométriques TESS & Diagnostic des Faux Positifs")
    lc_col1, lc_col2 = st.columns([1.35, 1.0])
    with lc_col1:
        prof_types = lc_df["transit_profile_type"].unique().tolist()
        sel_prof = st.selectbox("Catégorie de signal photométrique TESS", options=prof_types)
        sub_lc = lc_df[lc_df["transit_profile_type"] == sel_prof].reset_index(drop=True)
        sel_toi_idx = st.selectbox(
            "Objet TESS (TOI)",
            options=list(range(len(sub_lc))),
            format_func=lambda i: (
                f"TOI-{sub_lc.loc[i, 'toi_id']} (TIC {sub_lc.loc[i, 'tic']}) — "
                f"P={sub_lc.loc[i, 'period_days']:.2f}j | Profondeur={sub_lc.loc[i, 'measured_depth_ppm']:.0f} ppm | R≈{sub_lc.loc[i, 'est_radius_earth']:.1f} R⊕"
            ),
        )
        row_lc = sub_lc.loc[sel_toi_idx]
        local_flux = json.loads(row_lc["local_flux_json"])
        global_flux = json.loads(row_lc["global_flux_json"])

        fig_lc = go.Figure()
        fig_lc.add_trace(
            go.Scatter(
                x=np.linspace(-0.5, 0.5, len(global_flux)),
                y=global_flux,
                mode="lines",
                line={"color": "rgba(148, 163, 184, 0.55)", "width": 1.6},
                name="Vue globale (orbite complète : détection éclipse secondaire)",
            )
        )
        fig_lc.add_trace(
            go.Scatter(
                x=np.linspace(-0.15, 0.15, len(local_flux)),
                y=local_flux,
                mode="lines+markers",
                marker={"size": 4, "color": "#38bdf8"},
                line={"color": "#38bdf8", "width": 2.6},
                name="Vue locale centrée sur le transit primaire",
            )
        )
        fig_lc.update_layout(
            template="plotly_dark",
            height=380,
            title=f"Courbe de Lumière Pliée en Phase — TOI-{row_lc['toi_id']} (SNR ≈ {row_lc['snr_estimate']:.1f})",
            xaxis_title="Phase orbitale normalisée",
            yaxis_title="Flux stellaire normalisé (creux = transit)",
            legend={"orientation": "h", "y": 1.12},
        )
        st.plotly_chart(fig_lc, width="stretch")

    with lc_col2:
        fig_cand = px.bar(
            cand_df,
            x="survey",
            y="pct_within_survey",
            color="disposition_group",
            barmode="group",
            text="n_candidates",
            color_discrete_map={"CONFIRMED": "#10b981", "CANDIDATE": "#38bdf8", "FALSE POSITIVE": "#ef4444"},
            labels={"survey": "Catalogue spatial", "pct_within_survey": "% du pipeline", "disposition_group": "Statut"},
            title="Taux de Faux Positifs Instrumentaux (Kepler DR25 vs TESS)",
            template="plotly_dark",
        )
        fig_cand.update_layout(height=380)
        st.plotly_chart(fig_cand, width="stretch")

    with st.expander("🔍 Requête Spark SQL (`exo_methods_bias`) & Justification Statistique du Biais"):
        st.code(
            """WITH base AS (
    SELECT discovery_method,
           COUNT(*) AS n_planets,
           ROUND(PERCENTILE_APPROX(orbital_period_days, 0.5), 2) AS median_period_days,
           ROUND(PERCENTILE_APPROX(orbital_period_days, 0.75) - PERCENTILE_APPROX(orbital_period_days, 0.25), 2) AS iqr_period_days,
           ROUND(100.0 * AVG(geometric_transit_prob), 2) AS avg_geom_transit_prob_pct,
           ROUND(100.0 * AVG(CAST(has_measured_radius AS DOUBLE)), 1) AS pct_measured_radius,
           ROUND(100.0 * AVG(CAST(has_rv_amplitude AS DOUBLE)), 1) AS pct_measured_rv
    FROM v_exo_silver GROUP BY discovery_method
)
SELECT *, DENSE_RANK() OVER (ORDER BY n_planets DESC) AS rank_method,
       ROUND(100.0 * SUM(n_planets) OVER (ORDER BY n_planets DESC) / SUM(n_planets) OVER (), 2) AS pareto_cum_pct
FROM base;""",
            language="sql",
        )
        st.markdown(
            "**Justification :** Le couple **Transit + Vitesse Radiale** représente **> 92 %** de la courbe de Pareto, "
            "mais sonde deux sous-espaces biaisés (médiane $P \\approx 8\\text{ j}$ en Transit contre $> 350\\text{ j}$ en Vitesse Radiale "
            "et $> 10\\,000\\text{ j}$ en Imagerie Directe). De plus, près de **50 % des signaux bruts Kepler DR25** s'avèrent être des "
            "*faux positifs astrophysiques* (binaires à éclipses reconnaissables à leur éclipse secondaire à phase $\\pm 0,5$)."
        )

# ------------------------------------------------------------------------------
# ONGLET 3 : TAXONOMIE K-MEANS (k=5), VALLÉE DE FULTON & DRIFT MLOPS
# ------------------------------------------------------------------------------
with tabs[2]:
    st.subheader("🧠 Classification Non Supervisée K-Means ($k=5$) & Équation d'État Planétaire")
    st.markdown(
        "Entraîné dans l'espace $\\log_{10}(P, R_p, M_p, T_{\\text{eq}})$ standardisé (`StandardScaler`), K-Means fait émerger sans "
        "supervision les **5 grandes familles astrophysiques**, de la *Jupiter Chaude* gonflée par l'irradiation jusqu'aux *Mondes Telluriques Tempérés*."
    )

    km_c1, km_c2 = st.columns(2)
    clust_valid = filtered_df[filtered_df["cluster_id"] >= 0]

    with km_c1:
        fig_km_pr = px.scatter(
            clust_valid,
            x="orbital_period_days",
            y="radius_earth_est",
            color="planet_archetype",
            color_discrete_map=ARCHETYPE_COLORS,
            log_x=True,
            log_y=True,
            opacity=0.62,
            hover_name="planet_name",
            hover_data={"mass_earth_est": ":.2f", "equilibrium_temp_k_best": ":.0f", "discovery_method": True},
            labels={"orbital_period_days": "Période orbitale P (jours)", "radius_earth_est": "Rayon R_p (R⊕)", "planet_archetype": "Archétype K-Means"},
            title="Taxonomie K-Means dans le Plan (Période, Rayon) & Désert Neptunien",
            template="plotly_dark",
        )
        fig_km_pr.add_hline(y=1.8, line_dash="dot", line_color="#f8fafc", annotation_text="Vallée de Fulton (~1.8 R⊕)")
        fig_km_pr.update_layout(height=490)
        st.plotly_chart(fig_km_pr, width="stretch")

    with km_c2:
        mr_true = clust_valid[(clust_valid["has_measured_mass"] == 1) & (clust_valid["has_measured_radius"] == 1)]
        fig_mr = px.scatter(
            mr_true,
            x="mass_earth",
            y="radius_earth",
            color="planet_archetype",
            color_discrete_map=ARCHETYPE_COLORS,
            log_x=True,
            log_y=True,
            opacity=0.72,
            hover_name="planet_name",
            hover_data={"density_g_cm3": ":.2f", "equilibrium_temp_k_best": ":.0f"},
            labels={"mass_earth": "Masse vraie mesurée M_p (M⊕)", "radius_earth": "Rayon vrai mesuré R_p (R⊕)", "planet_archetype": "Archétype K-Means"},
            title="Diagramme Masse–Rayon (Mesures Conjointes Transit + Doppler)",
            template="plotly_dark",
        )
        m_ref = np.logspace(-1, 3.8, 160)
        # Courbes indicatives de composition interne (Zeng et al. simplifiées)
        fig_mr.add_trace(go.Scatter(x=m_ref[m_ref <= 30], y=1.00 * (m_ref[m_ref <= 30] ** 0.27), mode="lines", line={"color": "#a3e635", "dash": "dash"}, name="Rocheux type Terre (Silicates/Fer)"))
        fig_mr.add_trace(go.Scatter(x=m_ref[m_ref <= 30], y=1.26 * (m_ref[m_ref <= 30] ** 0.27), mode="lines", line={"color": "#38bdf8", "dash": "dot"}, name="Monde-Océan (50% H2O)"))
        fig_mr.update_layout(height=490)
        st.plotly_chart(fig_mr, width="stretch")

    km_c3, km_c4 = st.columns([1.05, 1.25])
    with km_c3:
        fig_pca = px.scatter(
            clust_valid.dropna(subset=["pca_1", "pca_2"]),
            x="pca_1",
            y="pca_2",
            color="planet_archetype",
            color_discrete_map=ARCHETYPE_COLORS,
            opacity=0.55,
            hover_name="planet_name",
            labels={"pca_1": "Composante Principale 1 (Irradiation / Proximité)", "pca_2": "Composante Principale 2 (Masse & Rayon)"},
            title="Séparation des 5 Clusters en Projection ACP (PCA 2D)",
            template="plotly_dark",
        )
        fig_pca.update_layout(height=420, showlegend=False)
        st.plotly_chart(fig_pca, width="stretch")

    with km_c4:
        fig_drift = px.bar(
            drift_df,
            x="mission_era",
            y="share_pct",
            color="planet_archetype",
            color_discrete_map=ARCHETYPE_COLORS,
            barmode="stack",
            text="share_pct",
            labels={"mission_era": "Ère d'observation spatiale", "share_pct": "Part des découvertes (%)", "planet_archetype": "Archétype"},
            title="Audit MLOps du Data Drift Temporel (PSI > 1.5 entre Pré-Kepler et Kepler !)",
            template="plotly_dark",
        )
        fig_drift.update_traces(texttemplate="%{text:.1f}%", textposition="inside")
        fig_drift.update_layout(height=420)
        st.plotly_chart(fig_drift, width="stretch")

    st.dataframe(profiles_df, width="stretch", hide_index=True)

    with st.expander("🔍 Requête Spark SQL (`exo_cluster_profiles`) & Surveillance MLOps du Drift"):
        st.code(
            """SELECT planet_archetype,
       COUNT(*) AS n_planets,
       ROUND(PERCENTILE_APPROX(orbital_period_days, 0.5), 2) AS median_period_days,
       ROUND(PERCENTILE_APPROX(radius_earth_est, 0.5), 2) AS median_radius_earth,
       ROUND(PERCENTILE_APPROX(mass_earth_est, 0.5), 2) AS median_mass_earth,
       ROUND(PERCENTILE_APPROX(equilibrium_temp_k_best, 0.5), 0) AS median_temp_k
FROM delta.`/lakehouse/gold/exo_planets_clustered`
WHERE cluster_id >= 0
GROUP BY planet_archetype ORDER BY n_planets DESC;""",
            language="sql",
        )
        st.markdown(
            "**Justification MLOps (Étapes 5 & 6 `intro-datascience`) :** La transformation $\\log_{10}$ couplée à `StandardScaler` empêche "
            "les périodes de $10^5$ jours d'écraser la distance euclidienne du K-Means. Le calcul du **Population Stability Index (PSI)** entre "
            "les 3 ères instrumentales démontre une dérive majeure ($\\text{PSI} \\gg 0,25$) : tout classifieur entraîné avant 2009 aurait prédit "
            "quasi exclusivement des géantes gazeuses."
        )

# ------------------------------------------------------------------------------
# ONGLET 4 : PANORAMA, ENTONNOIR DATA DETECTIVE, ANIMATION 1995-2026 & GALAXIE
# ------------------------------------------------------------------------------
with tabs[3]:
    st.subheader("🌌 L'Entonnoir du Data Detective & Histoire Animée des Découvertes (1995–2026)")

    pan1, pan2 = st.columns([1.0, 1.35])
    with pan1:
        funnel_fig = go.Figure(
            go.Funnel(
                y=[
                    "1. Signal Brut Multi-Sources (Bronze)",
                    "2. Solutions Publiées NASA (ps)",
                    "3. Exoplanètes Confirmées Uniques (Silver)",
                    "4. Profilées K-Means Multi-Paramètres (Gold)",
                    "5. Zone Habitable (Kopparapu)",
                    "6. Cibles Telluriques Haute Similarité (ESI ≥ 0.80)",
                ],
                x=[
                    39954 + 9564 + 3871,
                    39954,
                    len(planets_df),
                    int((planets_df["cluster_id"] >= 0).sum()),
                    int(planets_df["habitable_zone_status"].isin(["Conservatrice (0.35-1.11 S⊕)", "Optimiste (0.25-1.78 S⊕)"]).sum()),
                    int((planets_df["esi_score"] >= 0.80).sum()),
                ],
                textinfo="value+percent initial",
                marker={"color": ["#ef4444", "#f97316", "#eab308", "#06b6d4", "#10b981", "#8b5cf6"]},
            )
        )
        funnel_fig.update_layout(
            template="plotly_dark",
            height=440,
            title="Entonnoir de Raffinage de la Donnée (Signal Brut → Décision)",
            margin={"l": 10, "r": 10, "t": 50, "b": 10},
        )
        st.plotly_chart(funnel_fig, width="stretch")

    with pan2:
        tl_top = timeline_df[timeline_df["discovery_method"].isin(["Transit", "Radial Velocity", "Microlensing", "Imaging"])]
        fig_tl = px.bar(
            tl_top,
            x="discovery_year",
            y="n_discovered",
            color="discovery_method",
            color_discrete_map=METHOD_COLORS,
            labels={"discovery_year": "Année de découverte", "n_discovered": "Nouvelles exoplanètes", "discovery_method": "Méthode"},
            title="Vagues Technologiques Annuelles (Pics Kepler 2014/2016 → Relais TESS 2019–2026)",
            template="plotly_dark",
        )
        fig_tl.update_layout(height=440)
        st.plotly_chart(fig_tl, width="stretch")

    # Animation temporelle cumulative/annuelle 1995 -> 2026 et Carte Galactique
    anim_col, sky_col = st.columns(2)
    with anim_col:
        anim_src = (
            planets_df.dropna(subset=["discovery_year", "orbital_period_days", "radius_earth_est"])
            .query("discovery_year >= 1995 and orbital_period_days > 0 and radius_earth_est > 0")
            .sort_values("discovery_year")
            .copy()
        )
        anim_src["Année"] = anim_src["discovery_year"].astype(int)
        fig_hist_anim = px.scatter(
            anim_src,
            x="orbital_period_days",
            y="radius_earth_est",
            animation_frame="Année",
            color="discovery_method",
            color_discrete_map=METHOD_COLORS,
            log_x=True,
            log_y=True,
            range_x=[0.1, 2e5],
            range_y=[0.25, 30],
            hover_name="planet_name",
            title="🎬 Film Annuel des Découvertes (Appuyez sur ▶ Play : 1995 → 2026)",
            labels={"orbital_period_days": "Période P (jours)", "radius_earth_est": "Rayon R_p (R⊕)"},
            template="plotly_dark",
        )
        fig_hist_anim.update_layout(height=480)
        st.plotly_chart(fig_hist_anim, width="stretch")

    with sky_col:
        sky_df = filtered_df.dropna(subset=["galactic_longitude_deg", "galactic_latitude_deg"]).copy()
        sky_df["Mission"] = np.where(
            sky_df["discovery_facility"].str.contains("Kepler", case=False, na=False),
            "Champ fixe Kepler (Cygne/Lyre)",
            np.where(
                sky_df["discovery_facility"].str.contains("TESS", case=False, na=False),
                "Relevé tout-ciel TESS",
                "Autres Observatoires (Sol / K2 / OGLE)",
            ),
        )
        fig_sky = px.scatter(
            sky_df,
            x="galactic_longitude_deg",
            y="galactic_latitude_deg",
            color="Mission",
            color_discrete_map={
                "Champ fixe Kepler (Cygne/Lyre)": "#f43f5e",
                "Relevé tout-ciel TESS": "#38bdf8",
                "Autres Observatoires (Sol / K2 / OGLE)": "#a3e635",
            },
            opacity=0.58,
            hover_name="planet_name",
            hover_data={"distance_parsec": ":.1f", "discovery_facility": True},
            labels={"galactic_longitude_deg": "Longitude galactique l (°)", "galactic_latitude_deg": "Latitude galactique b (°)"},
            title="Empreinte Spatiale sur la Voie Lactée : Cône étroit de Kepler vs Tout-Ciel TESS",
            template="plotly_dark",
        )
        fig_sky.update_layout(height=480)
        st.plotly_chart(fig_sky, width="stretch")

# ------------------------------------------------------------------------------
# ONGLET 5 : CHASSE AUX MONDES HABITABLES (ESI & ZONE DE KOPPARAPU)
# ------------------------------------------------------------------------------
with tabs[4]:
    st.subheader("🌍 Chasse aux Mondes Potentiellement Habitables (Zone de Kopparapu & Score ESI)")

    hz_f1, hz_f2, hz_f3 = st.columns(3)
    with hz_f1:
        max_dist_ly = st.slider("Distance maximale à la Terre (années-lumière)", 4, 3000, 250)
    with hz_f2:
        max_rad_hab = st.slider("Rayon planétaire maximal (R⊕ — limite rocheuse ~1.8 R⊕)", 1.0, 3.0, 2.0, 0.1)
    with hz_f3:
        min_esi = st.slider("Earth Similarity Index minimal (ESI)", 0.50, 0.95, 0.72, 0.02)

    max_dist_pc = max_dist_ly / 3.26156
    hab_candidates = planets_df[
        planets_df["habitable_zone_status"].isin(["Conservatrice (0.35-1.11 S⊕)", "Optimiste (0.25-1.78 S⊕)"])
        & (planets_df["radius_earth_est"] <= max_rad_hab)
        & (planets_df["esi_score"] >= min_esi)
        & (planets_df["distance_parsec"].fillna(99999) <= max_dist_pc)
    ].sort_values("esi_score", ascending=False)

    hz_plot_df = planets_df.dropna(subset=["insolation_earth_best", "star_temperature_k", "radius_earth_est"]).query(
        "0.05 <= insolation_earth_best <= 8.0 and 2300 <= star_temperature_k <= 7200 and radius_earth_est <= 4.0"
    )

    fig_hz = px.scatter(
        hz_plot_df,
        x="insolation_earth_best",
        y="star_temperature_k",
        color="esi_score",
        size="radius_earth_est",
        size_max=18,
        color_continuous_scale="Viridis",
        hover_name="planet_name",
        hover_data={"habitable_zone_status": True, "distance_parsec": ":.1f", "orbital_period_days": ":.1f"},
        labels={
            "insolation_earth_best": "Flux stellaire incident S_eff (S⊕ — axe inversé : chaud à gauche, froid à droite)",
            "star_temperature_k": "Température effective de l'étoile hôte T_eff (K)",
            "esi_score": "Score ESI",
        },
        title="Diagramme d'Habitabilité de Kopparapu (Zone Conservatrice entre 1,11 et 0,35 S⊕)",
        template="plotly_dark",
    )
    fig_hz.add_vrect(x0=0.35, x1=1.11, fillcolor="#22c55e", opacity=0.16, line_width=1, annotation_text="HZ Conservatrice")
    fig_hz.add_vrect(x0=1.11, x1=1.78, fillcolor="#eab308", opacity=0.09, line_width=0)
    fig_hz.add_trace(
        go.Scatter(
            x=[1.91, 1.00, 0.43],
            y=[5778, 5778, 5778],
            mode="markers+text",
            marker={"size": 14, "symbol": "star", "color": "#f43f5e", "line": {"color": "white", "width": 1}},
            text=["Vénus", "Terre (ESI=1.00)", "Mars"],
            textposition="top center",
            name="Repères Système Solaire",
        )
    )
    fig_hz.update_xaxes(autorange="reversed")
    fig_hz.update_layout(height=500)
    st.plotly_chart(fig_hz, width="stretch")

    st.markdown(f"#### 🏆 {len(hab_candidates)} Cibles Habitables Prioritaires à moins de {max_dist_ly} années-lumière")
    hab_disp = hab_candidates.assign(distance_ly=lambda d: (d["distance_parsec"] * 3.26156).round(1))[[
        "planet_name", "host_star", "esi_score", "habitable_zone_status", "radius_earth_est",
        "mass_earth_est", "equilibrium_temp_k_best", "orbital_period_days", "distance_ly",
        "star_temperature_k", "n_transmission_spectra",
    ]]
    st.dataframe(hab_disp, width="stretch", hide_index=True)

# ------------------------------------------------------------------------------
# ONGLET 6 : CONCLUSIONS SCIENTIFIQUES, TESTS SCIPY & ARCHITECTURE LAKEHOUSE
# ------------------------------------------------------------------------------
with tabs[5]:
    st.subheader("📜 Conclusions du Data Detective & Validation Statistique (`scipy.stats`)")

    c_conc1, c_conc2 = st.columns(2)
    with c_conc1:
        st.markdown(
            """
            ### 1. Bilan sur les Populations Planétaires (K-Means & Fulton Gap)
            - **Les Super-Terres et Mini-Neptunes ($1\\text{–}4\\,R_\\oplus$) constituent les mondes les plus fréquents** de notre voisinage galactique proche, bien que totalement absents du Système Solaire !
            - Elles sont scindées en deux par la **Vallée des Rayons de Fulton ($\\sim 1,8\\,R_\\oplus$)** : en deçà, l'irradiation X/UV stellaire souffle l'atmosphère primordiale et laisse un cœur rocheux nu ; au-delà, la gravité retient une enveloppe de $1\\text{ à }10\\%$ d'$\\text{H}_2/\\text{He}$.
            - Sur le diagramme Masse–Rayon, au-delà de $\\sim 130\\,M_\\oplus$, la **pression de dégénérescence électronique** stabilise le rayon autour de $\\sim 1\\,R_J$ ($11,2\\,R_\\oplus$), sauf pour les **Jupiters Chaudes** gonflées jusqu'à $15\\text{–}20\\,R_\\oplus$ par chauffage stellaire intense.
            """
        )
    with c_conc2:
        st.markdown(
            """
            ### 2. Bilan sur le Biais de Sélection & les Missions Futures
            - Notre vision actuelle souffre d'un **triple filtre physique** : géométrique ($P_{\\text{transit}} = R_\\star / a$), temporel ($\\ge 3$ révolutions) et énergétique ($K \\propto M_p P^{-1/3}$).
            - C'est pourquoi les mondes habitables identifiés aujourd'hui (*TRAPPIST-1 e/f/g*, *Proxima Cen b*, *TOI-700 d*, *LHS 1140 b*) orbitent majoritairement autour de **naines rouges M**, où la Zone Habitable est $10\\text{ à }50\\times$ plus proche de l'étoile ($P = 4\\text{ à }40$ jours) !
            - Détecter une **vraie jumelle de la Terre autour d'une étoile de type G** ($P = 365\\text{ j}$, $K = 0,09\\text{ m/s}$, $\\Delta F/F = 84\\text{ ppm}$) est le défi direct des missions **ESA PLATO** (transits longue durée), **Nancy Grace Roman** (microlentille & coronographie) et **Habitable Worlds Observatory**.
            """
        )

    st.markdown("#### 🧪 Résultats Audités des 4 Tests d'Hypothèses Non-Paramétriques (`/lakehouse/gold/exo_stats_tests`)")
    st.dataframe(tests_df, width="stretch", hide_index=True)

    with st.expander("🏗️ Récapitulatif de l'Architecture Lakehouse Médaillon exécutée sur HDFS (`notebooks/example/exo-planette/`)"):
        st.markdown(
            """
            | Étape Notebook | Étapes `intro-datascience` | Tables HDFS Delta Lake produites |
            |---|---|---|
            | `01_Acquisition_Ingestion_HDFS_Bronze.ipynb` | **1. Acquisition** (5 datasets 2026, blocs 16 Mo, réplication=2) | `/lakehouse/bronze/exo_{ps_publications, archive_2026, kepler_koi, tess_toi, legacy_catalog}` |
            | `02_Data_Wrangling_Silver_ACID.ipynb` | **2. Nettoyage** (Regex JVM, MAR/MNAR, BroadcastJoin, ACID + Time Travel) | `/lakehouse/silver/exo_{planets, candidates_unified}` |
            | `03_EDA_Visualisation_Biais_Decouverte.ipynb` | **3. Visualisation & 4. EDA** (Skewness, Fulton, Biais, Pareto, `LAG`, `OPTIMIZE`) | `/lakehouse/gold/exo_{methods_bias, discovery_timeline, candidates_summary, tess_lightcurves}` |
            | `04_Modelisation_KMeans_Audit_Gold.ipynb` | **5. Modélisation & 6. MLOps** (Tests SciPy, K-Means $k=5$, Silhouette, Drift PSI) | `/lakehouse/gold/exo_{planets_clustered, cluster_profiles, drift_audit, stats_tests}` |
            | `05_Conclusions_Orbites_Storytelling.ipynb` + `dashboard.py` | **7. Communication** (Orbites Képlériennes 2D/3D, ESI, Export Universe Sandbox) | Application Streamlit temps réel sur `:8501` |
            """
        )
