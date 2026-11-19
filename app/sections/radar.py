"""Ouverture de l'accueil : radar de nuit en 3D, des avions animés sur les routes de l'année (table Gold route_flows)."""

import json
from pathlib import Path

import streamlit as st

from sections.theme import fr, pal

GABARIT = Path(__file__).with_name("radar.html")


def radar(routes, moyenne: float, chiffres: list[tuple[str, str]], kicker: str, titre: str, sous_titre: str,
          n_routes: int = 320, hauteur: int = 360):
    r = routes[routes["origin_lon"].between(-125.5, -66.5) & routes["dest_lon"].between(-125.5, -66.5)
               & routes["origin_lat"].between(24, 49.5) & routes["dest_lat"].between(24, 49.5)]
    r = r.nlargest(n_routes, "n_vols")
    data = [[round(x.origin_lon, 3), round(x.origin_lat, 3), round(x.dest_lon, 3), round(x.dest_lat, 3), int(x.n_vols),
             float(x.taux_retard), x.origin_airport, x.destination_airport, round(1.609 * x.distance)] for x in r.itertuples()]
    html = GABARIT.read_text(encoding="utf-8").replace("background: #F2F5F9", f"background: {pal()['page']}")
    for cle, val in {"__ROUTES__": json.dumps(data), "__MOY__": f"{moyenne:.2f}", "__KICKER__": kicker,
                     "__TITRE__": titre, "__SOUS__": sous_titre,
                     "__CHIFFRES__": "".join(f"<div class='chiffre'><b>{v}</b><span>{l}</span></div>" for v, l in chiffres)}.items():
        html = html.replace(cle, val)
    st.iframe(html, height=hauteur)
