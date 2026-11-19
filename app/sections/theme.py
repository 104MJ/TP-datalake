"""Thème du dashboard : couleurs, CSS, mise en forme des graphiques Plotly et des nombres."""

from urllib.parse import quote

import plotly.io as pio
import streamlit as st

# Chrome (interface)
NAVY = "#0B2545"
INK = "#13253D"
INK2 = "#4A5A70"
MUTED = "#8592A3"
PAGE = "#F2F5F9"
CARD = "#FFFFFF"
LINE = "#E1E6EE"
GRID = "#E9EDF3"

# Données
ORANGE = "#EB6834"      # retard, sélection
BLUE = "#2A78D6"        # référence (ensemble des vols), à l'heure
GRAY = "#C9D0DA"        # éléments hors sélection
RAMPE = ["#FDE9DC", "#F9C4A3", "#F39A6B", "#EB6834", "#C24C1C", "#8C3512"]  # taux de retard, clair -> foncé
ECHELLE = [[i / (len(RAMPE) - 1), c] for i, c in enumerate(RAMPE)]
SEGMENTS = {"Grands hubs congestionnés": "#2A78D6", "Retards en cascade": "#EB6834",
            "Aéroports régionaux perturbés": "#1BAF7A", "Aéroports exposés à la météo": "#6250D6"}

NOM_COURT = {"AA": "American", "AS": "Alaska", "B6": "JetBlue", "DL": "Delta", "EV": "Atlantic Southeast",
             "F9": "Frontier", "HA": "Hawaiian", "MQ": "American Eagle", "NK": "Spirit", "OO": "SkyWest",
             "UA": "United", "US": "US Airways", "VX": "Virgin America", "WN": "Southwest"}

# Mode « vol de nuit » : mêmes rôles, valeurs choisies pour un fond sombre
CLAIR = {"page": PAGE, "card": CARD, "ink": INK, "ink2": INK2, "muted": MUTED, "line": LINE, "grid": GRID,
         "gray": GRAY, "blue": BLUE, "land": "#E8EDF3", "track": "#EEF2F7"}
SOMBRE = {"page": "#071A33", "card": "#0E2645", "ink": "#E7EEF8", "ink2": "#B4C3D7", "muted": "#7F94B0",
          "line": "#21406A", "grid": "#1A3559", "gray": "#344B6D", "blue": "#3987E5", "land": "#15304F", "track": "#1A3559"}
RAMPE_NUIT = ["#5E4E66", "#88524A", "#B5552F", "#EB6834", "#F5A27A", "#FDD9C2"]  # discret -> lumineux
_REMAP = {**{a: b for a, b in zip(RAMPE, RAMPE_NUIT) if a != ORANGE},
          INK: SOMBRE["ink"], INK2: SOMBRE["ink2"], MUTED: SOMBRE["muted"], GRID: SOMBRE["grid"], LINE: SOMBRE["line"],
          GRAY: SOMBRE["gray"], BLUE: SOMBRE["blue"], "#E8EDF3": SOMBRE["land"], "#FFFFFF": SOMBRE["card"],
          "white": SOMBRE["card"]}


def nuit() -> bool:
    return bool(st.session_state.get("nuit"))


def pal() -> dict:
    return SOMBRE if nuit() else CLAIR


FONT = "DM Sans, system-ui, sans-serif"
MOIS = ["Janv.", "Févr.", "Mars", "Avr.", "Mai", "Juin", "Juil.", "Août", "Sept.", "Oct.", "Nov.", "Déc."]


def fr(x, d=1) -> str:
    """Nombre au format français : 12 345,6."""
    return f"{x:,.{d}f}".replace(",", " ").replace(".", ",")


def pct(x, d=1) -> str:
    return f"{fr(x, d)} %"


def compact(n) -> str:
    if n >= 1e6:
        return f"{fr(n / 1e6, 2)} M"
    if n >= 1e4:
        return f"{fr(n / 1e3, 0)} k"
    return fr(n, 0)


def mise_en_forme(fig, hauteur=300, legende=False):
    """Style commun : fond transparent, grille fine, police du dashboard, séparateurs français."""
    fig.update_layout(
        height=hauteur, margin={"l": 4, "r": 8, "t": 28 if legende else 6, "b": 4},
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", separators=", ",
        font={"family": FONT, "color": INK2, "size": 12}, showlegend=legende,
        legend={"orientation": "h", "x": 0, "y": 1.12, "title": None, "font": {"size": 12, "color": INK2}},
        hoverlabel={"bgcolor": "white", "bordercolor": LINE, "font": {"family": FONT, "color": INK, "size": 13}},
        barcornerradius=4, bargap=0.35,
    )
    axe = {"gridcolor": GRID, "linecolor": LINE, "zeroline": False, "tickfont": {"color": MUTED}, "title": None, "automargin": True}
    fig.update_xaxes(**axe)
    fig.update_yaxes(**axe)
    return fig


def graphique(fig, key=None, clic=None):
    """Affiche un graphique ; `clic` (callback) rend ses barres ou points cliquables."""
    if clic:
        fig.update_traces(selected={"marker": {"opacity": 1}}, unselected={"marker": {"opacity": 1}},
                          selector=lambda t: t.type in ("bar", "scatter", "scattergeo"))
    if nuit():
        js = fig.to_json()
        for a, b in _REMAP.items():
            js = js.replace(f'"{a}"', f'"{b}"')
        fig = pio.from_json(js)
    options = {"on_select": clic, "selection_mode": "points"} if clic else {}
    st.plotly_chart(fig, width="stretch", theme=None, key=key, config={"displayModeBar": False}, **options)


def table_html(df, colonnes, hauteur=None):
    """Tableau HTML qui suit le thème. `colonnes` : (champ, titre, type) avec type 'texte', 'nombre',
    ou ('barre', max) pour une jauge suivie de la valeur en %."""
    tete = "".join(f"<th>{t}</th>" for _, t, _ in colonnes)
    lignes = ""
    for row in df.itertuples(index=False):
        cases = ""
        for champ, _, typ in colonnes:
            v = getattr(row, champ)
            if isinstance(typ, tuple):
                cases += (f"<td class='barre'><span><i style='width:{min(100 * v / typ[1], 100):.0f}%'></i></span>"
                          f"{pct(v)}</td>")
            elif typ == "nombre":
                cases += f"<td class='nb'>{fr(v, 0)}</td>"
            elif typ == "pct":
                cases += f"<td class='nb'>{pct(v)}</td>"
            else:
                cases += f"<td>{v}</td>"
        lignes += f"<tr>{cases}</tr>"
    style = f" style='max-height:{hauteur}px'" if hauteur else ""
    st.markdown(f"<div class='tab-conteneur'{style}><table class='tab'><thead><tr>{tete}</tr></thead>"
                f"<tbody>{lignes}</tbody></table></div>", unsafe_allow_html=True)


def titre(texte: str, sous_titre: str = ""):
    """Titre de carte : la conclusion en une ligne, puis ce qui est mesuré."""
    st.markdown(f"<div class='carte-titre'>{texte}</div>"
                + (f"<div class='carte-sous-titre'>{sous_titre}</div>" if sous_titre else ""),
                unsafe_allow_html=True)


TRAJET = "M12 60 Q210 -20 408 60"
ESCALES = ["Embarquement", "Le départ", "La compagnie", "L'aéroport", "En vol", "Votre vol", "Arrivée"]


def entete(surtitre: str, texte: str, etape: int | None = None):
    """En-tête de page ; `etape` place l'avion sur la carte de vol du voyage (0 à 6)."""
    carte = ""
    if etape is not None:
        n = len(ESCALES) - 1
        fin = 100 * etape / n
        debut = 100 * max(etape - 1, 0) / n
        escales = "".join(f"<span class='escale{' passee' if i <= etape else ''}' style='offset-distance:{100 * i / n:.1f}%'"
                          f" title='{e}'></span>" for i, e in enumerate(ESCALES))
        carte = (f"<div class='carte-vol' style='--debut:{debut:.1f}%;--fin:{fin:.1f}%'>"
                 f"<svg viewBox='0 0 420 72'><path class='trajet' d='{TRAJET}'/>"
                 f"<path class='parcouru' d='{TRAJET}' pathLength='100' stroke-dasharray='{fin:.1f} 100'/></svg>"
                 f"{escales}<span class='avion-progression'></span>"
                 f"<div class='carte-vol-legende'>Étape {etape}/{n} · <b>{ESCALES[etape]}</b></div></div>")
    st.markdown(f"<div class='page-entete'><div><div class='surtitre'>{surtitre}</div><div class='titre'>{texte}</div></div>"
                f"{carte}</div>", unsafe_allow_html=True)


CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:opsz,wght@9..40,400;9..40,500;9..40,600;9..40,700&display=swap');
:root {{ --navy: {NAVY}; --ink: {INK}; --ink2: {INK2}; --muted: {MUTED}; --page: {PAGE}; --line: {LINE};
         --orange: {ORANGE}; --blue: {BLUE}; }}
.stApp {{ background: var(--page); }}
.stApp :is(p, li, label, input, button, td, th, h1, h2, h3, h4) {{ font-family: 'DM Sans', system-ui, sans-serif; }}
.stApp :is(p, li, label) {{ color: var(--ink); }}
.block-container {{ padding-top: 4.6rem; padding-bottom: 2rem; max-width: 1440px; }}
[data-testid="stAppDeployButton"], [data-testid="stMainMenu"] {{ display: none; }}
.st-key-mode {{ position: fixed; top: 0.85rem; right: 1.4rem; z-index: 1000001; width: auto !important; background: transparent !important; box-shadow: none !important; animation: none !important; transform: none !important; }}
.st-key-mode label p, .st-key-mode [data-testid="stWidgetLabel"] p {{ color: #DCE5F2 !important; font-weight: 600; }}
.st-key-mode label > div:first-of-type {{ background: rgba(255, 255, 255, 0.3) !important; }}
.st-key-mode label:has(input:checked) > div:first-of-type {{ background: var(--orange) !important; }}

/* Bandeau de navigation */
header[data-testid="stHeader"] {{ background: var(--navy); }}
[data-testid="stTopNavLink"] {{ border-radius: 999px; padding: 0.3rem 0.85rem; }}
[data-testid="stTopNavLink"] p, [data-testid="stTopNavLink"] [data-testid="stIconMaterial"] {{ color: #AFC0D6 !important; font-weight: 600; }}
[data-testid="stTopNavLink"]:hover {{ background: rgba(255, 255, 255, 0.08); }}
[data-testid="stTopNavLink"][aria-current="page"] {{ background: rgba(255, 255, 255, 0.14); }}
[data-testid="stTopNavLink"][aria-current="page"] p, [data-testid="stTopNavLink"][aria-current="page"] [data-testid="stIconMaterial"] {{ color: #FFFFFF !important; }}

/* En-tête de page */
.page-entete .surtitre {{ font-size: 0.76rem; font-weight: 700; letter-spacing: 0.12em; text-transform: uppercase; color: var(--orange); }}
.page-entete .titre {{ font-size: 1.75rem; font-weight: 700; color: var(--ink); margin: 0.1rem 0 0.5rem; letter-spacing: -0.015em; line-height: 1.2; }}

/* Cartes */
[data-testid="stLayoutWrapper"] > [data-testid="stVerticalBlock"] {{ background: {CARD}; box-shadow: 0 1px 3px rgba(11, 37, 69, 0.04); }}
button[aria-checked="true"] {{ background: var(--orange) !important; border-color: var(--orange) !important; }}
button[aria-checked="true"] p {{ color: #FFFFFF !important; }}
[class*="st-key-barre"] button[aria-checked="false"] p {{ color: {INK} !important; }}
.material {{ font-family: 'Material Symbols Rounded'; font-size: 1.5rem; line-height: 1; color: var(--orange); font-weight: 400; }}
.test {{ padding: 0.65rem 0; border-bottom: 1px solid var(--line); display: grid; grid-template-columns: 1.1fr 1fr; gap: 0.3rem 1.2rem; }}
.test:last-child {{ border-bottom: none; }}
.test b {{ color: var(--ink); }} .test small {{ color: var(--muted); }}
.test .q {{ font-size: 0.86rem; color: var(--ink2); }}
.test .c {{ grid-column: 1 / 3; font-size: 0.86rem; color: var(--ink2); }}
.test .jauge {{ height: 8px; border-radius: 99px; background: #EEF2F7; margin-top: 0.35rem; }}
.test .jauge div {{ height: 100%; border-radius: 99px; background: var(--orange); }}
[class*="st-key-barre"] {{ background: var(--navy) !important; border-radius: 14px; padding: 0.7rem 1rem 0.8rem !important; border: none !important; }}
[class*="st-key-barre"] label p, [class*="st-key-barre"] [data-testid="stSliderTickBarMin"], [class*="st-key-barre"] [data-testid="stSliderTickBarMax"] {{ color: #DCE5F2 !important; font-weight: 600; }}
[class*="st-key-barre"] button p, [class*="st-key-barre"] button [data-testid="stIconMaterial"] {{ color: {INK} !important; }}
[class*="st-key-barre"] [data-testid="stSliderThumbValue"] {{ display: none !important; }}
[class*="st-key-barre"] [data-testid="stSliderThumbValue"] {{ color: #FFFFFF !important; font-weight: 700; }}
[class*="st-key-barre"] [data-testid="stSliderTickBar"] {{ color: #8FA3BD !important; }}
.chiffre-cle {{ background: #FDF1EA; border-radius: 10px; padding: 0.6rem 0.9rem; color: var(--ink); font-size: 0.92rem; }}
.chiffre-cle b {{ font-size: 1.35rem; margin-right: 0.35rem; color: var(--ink); }}
[data-testid="stExpander"] details summary {{ padding-top: 0.35rem; padding-bottom: 0.35rem; }}
/* Carte d'embarquement */
.ce {{ display: grid; grid-template-columns: 1fr 190px; background: #FFFFFF; border-radius: 18px; border: 1px solid var(--line); margin-bottom: 0.9rem;
       overflow: hidden; box-shadow: 0 6px 24px rgba(11, 37, 69, 0.08); }}
.ce-main {{ padding: 1.1rem 1.4rem 1.2rem; }}
.ce-entete {{ display: flex; justify-content: space-between; font-size: 0.74rem; font-weight: 700; letter-spacing: 0.12em;
              text-transform: uppercase; color: var(--muted); }}
.ce-entete b {{ color: var(--orange); }}
.ce-route {{ display: flex; align-items: center; gap: 1.2rem; margin: 0.9rem 0 1rem; }}
.ce-route small, .ce-risque small, .ce-talon small {{ display: block; font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.08em; color: var(--muted); }}
.ce-route b {{ display: block; font-size: 2.6rem; line-height: 1; font-weight: 700; color: var(--ink); letter-spacing: 0.02em; }}
.ce-route span {{ font-size: 0.88rem; color: var(--ink2); }}
.ce-vol {{ flex: 1; border-top: 2px dashed #C9D0DA; position: relative; height: 0; }}
.ce-vol::after {{ content: "✈"; position: absolute; left: 50%; top: -0.85rem; transform: translateX(-50%); color: var(--orange);
                  font-size: 1.3rem; background: #fff; padding: 0 0.4rem; }}
.ce-periode b {{ font-size: 1.25rem !important; }}
.ce-risque b {{ font-size: 2.3rem; font-weight: 700; color: var(--ink); }}
.ce-jauge {{ position: relative; height: 10px; border-radius: 99px; background: #FDE9DC; margin: 0.5rem 0 0.35rem; }}
.ce-jauge div {{ height: 100%; border-radius: 99px; background: var(--orange); }}
.ce-jauge i {{ position: absolute; top: -5px; width: 2px; height: 20px; background: var(--ink); }}
.ce-pied {{ font-size: 0.82rem; color: var(--ink2); }}
.ce-talon {{ background: var(--navy); color: #fff; padding: 1.1rem 1.1rem; border-left: 2px dashed rgba(255, 255, 255, 0.35);
             display: flex; flex-direction: column; gap: 0.9rem; }}
.ce-talon small {{ color: #9FB3CC; }}
.ce-talon b {{ font-size: 1.25rem; color: #fff; }}
.niveau {{ display: inline-flex; align-items: center; gap: 0.35rem; padding: 0.25rem 0.7rem; border-radius: 99px; font-weight: 700; font-size: 0.9rem; }}
.niveau.faible {{ background: #DDF3DD; color: #0B6B0B; }}
.niveau.moyen {{ background: #FFF1CC; color: #7A5500; }}
.niveau.eleve {{ background: #F9DCDC; color: #9E2323; }}
.conseil {{ display: flex; gap: 0.8rem; align-items: flex-start; padding: 0.55rem 0; border-bottom: 1px solid var(--line); }}
.conseil:last-child {{ border-bottom: none; }}
.conseil .ico {{ font-size: 1.4rem; line-height: 1; }}
.conseil b {{ color: var(--ink); }}
.conseil div {{ font-size: 0.9rem; color: var(--ink2); }}
.profil {{ padding: 0.7rem 0.1rem; border-bottom: 1px solid var(--line); opacity: 0.5; }}
.profil.actif {{ opacity: 1; }}
.profil:last-child {{ border-bottom: none; }}
.profil-tete {{ display: flex; align-items: center; gap: 0.5rem; color: var(--ink); }}
.profil-tete i {{ width: 10px; height: 10px; border-radius: 3px; flex: none; }}
.profil-tete span {{ margin-left: auto; font-size: 0.8rem; color: var(--muted); }}
.profil-desc, .profil-chiffres {{ font-size: 0.82rem; color: var(--ink2); margin: 0.15rem 0 0.35rem 1.1rem; }}
.profil-barre {{ height: 8px; border-radius: 99px; background: #EEF2F7; margin-left: 1.1rem; overflow: hidden; }}
.profil-barre div {{ height: 100%; border-radius: 99px; }}
[class*="st-key-barre"] .barre-titre {{ color: #FFFFFF; font-weight: 700; font-size: 1.02rem; display: flex; gap: 0.6rem; align-items: baseline; padding-bottom: 0.45rem; }}
[class*="st-key-barre"] .barre-titre span {{ color: #9FB3CC; font-weight: 500; font-size: 0.9rem; }}
.carte-titre {{ font-size: 1.02rem; font-weight: 700; color: var(--ink); line-height: 1.3; }}
.carte-sous-titre {{ font-size: 0.84rem; color: var(--muted); margin-top: 0.1rem; }}
[data-testid="stMetric"] {{ background: {CARD}; }}
[data-testid="stMetricLabel"] p {{ color: var(--ink2) !important; font-weight: 600; }}
[data-testid="stMetricValue"] div {{ color: var(--ink) !important; font-weight: 700; }}
[data-testid="stExpander"] summary p {{ color: var(--ink2) !important; font-size: 0.86rem; }}
[data-testid="stCaptionContainer"] p {{ color: var(--muted) !important; }}
</style>
"""


# Avions en SVG (encodés pour les URL CSS) : curseur, curseur cliquable, poignées de curseur
_AVION = ("M14 1c1.2 0 2 1.4 2 3v6l9 5.2v2.6l-9-2.6v5.6l3 2.3v2.1l-5-1.4-5 1.4v-2.1l3-2.3v-5.6l-9 2.6v-2.6"
          "l9-5.2V4c0-1.6.8-3 2-3z")


def _svg(couleur, angle, taille=28):
    svg = (f"<svg xmlns='http://www.w3.org/2000/svg' width='{taille}' height='{taille}' viewBox='0 0 28 28'>"
           f"<g transform='rotate({angle} 14 14)'><path fill='{couleur}' stroke='white' stroke-width='1.3' d='{_AVION}'/></g></svg>")
    return f'url("data:image/svg+xml,{quote(svg)}")'


EFFETS = f"""
<style>
/* Curseur avion (le nez de l'avion est le point actif) */
.stApp, .stApp * {{ cursor: {_svg(NAVY, -45)} 5 5, auto; }}
.stApp :is(a, button, [role="slider"], [role="tab"], [role="option"], [role="radio"], summary, label[data-baseweb]),
.stApp :is(a, button, [role="tab"], summary) * {{ cursor: {_svg(ORANGE, -45)} 5 5, pointer; }}
.stApp :is(input, textarea) {{ cursor: text; }}

/* Poignées des curseurs : de petits avions */
[data-testid="stSlider"] div:has(> div > input[type="range"]) {{ background: {_svg(ORANGE, 90, 30)} center / 28px 28px no-repeat !important;
    background-color: transparent !important; border: none !important; box-shadow: none !important; border-radius: 0 !important;
    width: 28px !important; height: 28px !important; }}

/* Carte de vol de l'en-tête */
.page-entete {{ display: flex; justify-content: space-between; align-items: flex-end; gap: 2rem; }}
.carte-vol {{ position: relative; width: 420px; height: 86px; flex: none; }}
.carte-vol svg {{ position: absolute; left: 0; top: 0; width: 420px; height: 72px; overflow: visible; }}
.carte-vol .trajet {{ fill: none; stroke: #C9D0DA; stroke-width: 2; stroke-dasharray: 4 6; }}
.carte-vol .parcouru {{ fill: none; stroke: {ORANGE}; stroke-width: 2.5; stroke-linecap: round; }}
.escale, .avion-progression {{ position: absolute; left: 0; top: 0; offset-path: path('{TRAJET}'); }}
.escale {{ width: 11px; height: 11px; border-radius: 50%; background: #FFFFFF; border: 2px solid #C9D0DA; offset-rotate: 0deg; }}
.escale.passee {{ background: {ORANGE}; border-color: {ORANGE}; }}
.avion-progression {{ width: 30px; height: 30px; background: {_svg(NAVY, 90, 30)} center / contain no-repeat;
    offset-rotate: auto; offset-distance: var(--fin); animation: vol 1.6s cubic-bezier(.25, .8, .3, 1) both; }}
@keyframes vol {{ from {{ offset-distance: var(--debut); }} to {{ offset-distance: var(--fin); }} }}
.carte-vol-legende {{ position: absolute; right: 0; bottom: 0; font-size: 0.8rem; color: {MUTED}; }}
.carte-vol-legende b {{ color: {INK}; }}
@media (max-width: 1000px) {{ .carte-vol {{ display: none; }} }}

/* Apparition des cartes et relief au survol */
[data-testid="stLayoutWrapper"] > [data-testid="stVerticalBlock"], [data-testid="stMetric"], .ce {{
    animation: monte .55s cubic-bezier(.2, .7, .3, 1) both; transition: transform .2s ease, box-shadow .2s ease; }}
[data-testid="stLayoutWrapper"] > [data-testid="stVerticalBlock"]:hover, [data-testid="stMetric"]:hover {{
    transform: translateY(-3px); box-shadow: 0 14px 30px rgba(11, 37, 69, 0.10); }}
[data-testid="stColumn"]:nth-child(2) :is([data-testid="stMetric"], [data-testid="stLayoutWrapper"] > [data-testid="stVerticalBlock"]) {{ animation-delay: .08s; }}
[data-testid="stColumn"]:nth-child(3) [data-testid="stMetric"] {{ animation-delay: .16s; }}
[data-testid="stColumn"]:nth-child(4) [data-testid="stMetric"] {{ animation-delay: .24s; }}
@keyframes monte {{ from {{ opacity: 0; transform: translateY(14px); }} to {{ opacity: 1; transform: none; }} }}
.ce {{ transform-style: preserve-3d; }}
.ce:hover {{ transform: perspective(900px) rotateX(3deg) rotateY(-3deg) translateY(-3px); box-shadow: 0 22px 40px rgba(11, 37, 69, 0.16); }}
[data-testid="stTopNavLink"] [data-testid="stIconMaterial"] {{ transition: transform .25s ease; }}
[data-testid="stTopNavLink"]:hover [data-testid="stIconMaterial"] {{ transform: translate(2px, -2px) rotate(-8deg); }}

@media (prefers-reduced-motion: reduce) {{
  *, *::before, *::after {{ animation: none !important; transition: none !important; }}
}}
</style>
"""


TABLEAUX = f"""
<style>
.tab-conteneur {{ overflow: auto; border: 1px solid var(--line); border-radius: 12px; }}
.tab {{ width: 100%; border-collapse: collapse; font-size: 0.86rem; }}
.tab th {{ position: sticky; top: 0; background: var(--card, {CARD}); text-align: left; font-weight: 600; color: var(--ink2);
          padding: 0.5rem 0.7rem; border-bottom: 1px solid var(--line); }}
.tab td {{ padding: 0.45rem 0.7rem; border-bottom: 1px solid var(--line); color: var(--ink); white-space: nowrap; }}
.tab tr:last-child td {{ border-bottom: none; }}
.tab tbody tr:hover td {{ background: rgba(235, 104, 52, 0.06); }}
.tab td.nb {{ text-align: right; font-variant-numeric: tabular-nums; }}
.tab td.barre {{ font-variant-numeric: tabular-nums; }}
.tab td.barre span {{ display: inline-block; width: 90px; height: 7px; border-radius: 99px; background: var(--track, #EEF2F7);
                      margin-right: 0.5rem; vertical-align: middle; overflow: hidden; }}
.tab td.barre i {{ display: block; height: 100%; border-radius: 99px; background: {ORANGE}; }}
</style>
"""


def _css_sombre() -> str:
    c = SOMBRE
    return f"""
<style>
:root {{ --ink: {c["ink"]}; --ink2: {c["ink2"]}; --muted: {c["muted"]}; --page: {c["page"]}; --line: {c["line"]};
         --card: {c["card"]}; --track: {c["track"]}; }}
.stApp {{ background: {c["page"]} !important; }}
.stApp :is(p, li, label, h1, h2, h3) {{ color: {c["ink"]}; }}
[data-testid="stLayoutWrapper"] > [data-testid="stVerticalBlock"], [data-testid="stMetric"] {{ background: {c["card"]} !important;
    border-color: {c["line"]} !important; box-shadow: 0 1px 3px rgba(0, 0, 0, 0.3); }}
[data-testid="stMetricLabel"] p {{ color: {c["ink2"]} !important; }}
[data-testid="stMetricValue"] div {{ color: {c["ink"]} !important; }}
[data-testid="stMetricDelta"] p, [data-testid="stMetricDelta"] div {{ color: inherit !important; }}
[data-testid="stExpander"] details {{ background: {c["card"]}; border-color: {c["line"]} !important; }}
[data-testid="stExpander"] summary p, [data-testid="stCaptionContainer"] p {{ color: {c["muted"]} !important; }}
[data-testid="stTabs"] button p {{ color: {c["ink2"]} !important; }}
[data-testid="stTabs"] button[aria-selected="true"] p {{ color: {c["ink"]} !important; }}
.carte-vol .trajet {{ stroke: {c["gray"]}; }}
.escale {{ background: {c["page"]}; border-color: {c["gray"]}; }}
.carte-vol-legende b {{ color: {c["ink"]}; }}
.chiffre-cle {{ background: rgba(235, 104, 52, 0.14); }}
.ce {{ background: {c["card"]}; border-color: {c["line"]}; }}
.ce-vol {{ border-top-color: {c["gray"]}; }}
.ce-vol::after {{ background: {c["card"]}; }}
.ce-jauge {{ background: {c["track"]}; }}
.ce-jauge i {{ background: {c["ink"]}; }}
.test .jauge, .profil-barre {{ background: {c["track"]}; }}
.stApp .avion-progression {{ filter: invert(1) brightness(1.6); }}
</style>
"""


def appliquer():
    st.markdown(CSS + EFFETS + TABLEAUX + (_css_sombre() if nuit() else ""), unsafe_allow_html=True)
