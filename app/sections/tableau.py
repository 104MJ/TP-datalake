"""Tableau des départs façon aéroport (palettes qui défilent), à partir de la table Gold route_flows."""

import json
import streamlit as st


GABARIT = """<!doctype html><html><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@500;700&family=DM+Sans:wght@500;700&display=swap" rel="stylesheet">
<style>
  html, body { margin: 0; background: transparent; font-family: 'JetBrains Mono', ui-monospace, monospace; }
  .board { background: #0A1626; border-radius: 18px; padding: 16px 20px 14px; color: #FFC857; box-shadow: 0 10px 28px rgba(11, 37, 69, 0.22); }
  .tete { display: flex; justify-content: space-between; align-items: baseline; font-family: 'DM Sans', sans-serif; margin-bottom: 10px; }
  .tete b { color: #fff; font-size: 17px; letter-spacing: 0.04em; }
  .tete span { color: #8FA3BD; font-size: 12.5px; }
  table { width: 100%; border-collapse: separate; border-spacing: 0 5px; }
  th { text-align: left; font: 700 11px 'DM Sans', sans-serif; letter-spacing: 0.12em; color: #8FA3BD; padding: 0 6px 2px; }
  td { padding: 0 6px; white-space: nowrap; }
  .f { display: inline-block; width: 0.78em; height: 1.45em; line-height: 1.45em; margin-right: 2px; text-align: center;
       background: #16263A; border-radius: 3px; font-size: 15px; font-weight: 700; position: relative; }
  .f::after { content: ""; position: absolute; left: 0; right: 0; top: 50%; height: 1px; background: rgba(0, 0, 0, 0.55); }
  .f.tourne { animation: flip 0.09s linear; }
  @keyframes flip { 0% { transform: rotateX(0); } 50% { transform: rotateX(90deg); } 100% { transform: rotateX(0); } }
  .code .f { color: #FFFFFF; }
  .statut { display: inline-block; padding: 3px 10px; border-radius: 6px; font: 700 12px 'DM Sans', sans-serif; letter-spacing: 0.06em;
            opacity: 0; transition: opacity 0.4s; }
  .statut.vu { opacity: 1; }
  .ok { background: #0CA30C; color: #fff; } .moyen { background: #FAB219; color: #0B0B0B; } .mauvais { background: #D03B3B; color: #fff; }
  @media (prefers-reduced-motion: reduce) { .f.tourne { animation: none; } }
</style></head><body>
<div class="board">
  <div class="tete"><b>✈ __TITRE__</b><span>__SOUS__</span></div>
  <table><thead><tr><th>DESTINATION</th><th>CODE</th><th>VOLS / SEM.</th><th>À L'HEURE</th><th>STATUT</th></tr></thead>
  <tbody id="lignes"></tbody></table>
</div>
<script>
const LIGNES = __LIGNES__;
const CALME = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
const ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789";
const corps = document.getElementById("lignes");
const cases = [];
const palettes = (texte, largeur, classe) => {
  const td = document.createElement("td");
  if (classe) td.className = classe;
  texte.padEnd(largeur).slice(0, largeur).split("").forEach(c => {
    const s = document.createElement("span");
    s.className = "f"; s.textContent = CALME ? c : " "; td.appendChild(s); cases.push([s, c]);
  });
  return td;
};
LIGNES.forEach((l, i) => {
  const tr = document.createElement("tr");
  tr.appendChild(palettes(l.ville, 15));
  tr.appendChild(palettes(l.code, 3, "code"));
  tr.appendChild(palettes(l.vols, 4));
  tr.appendChild(palettes(l.ponctuel, 4));
  const td = document.createElement("td"), st = document.createElement("span");
  st.className = "statut " + l.classe; st.textContent = l.statut; td.appendChild(st); tr.appendChild(td);
  corps.appendChild(tr);
  setTimeout(() => st.classList.add("vu"), CALME ? 0 : 900 + i * 160);
});
if (!CALME) cases.forEach(([s, fin], k) => {
  const arret = 350 + Math.floor(k / 26) * 160 + (k % 26) * 22;
  const debut = performance.now();
  const roule = () => {
    if (performance.now() - debut >= arret || fin === " ") { s.textContent = fin; s.classList.remove("tourne"); return; }
    s.textContent = ALPHABET[Math.floor(Math.random() * ALPHABET.length)];
    s.classList.remove("tourne"); void s.offsetWidth; s.classList.add("tourne");
    setTimeout(roule, 70);
  };
  setTimeout(roule, (k % 26) * 8);
});
</script></body></html>"""


def tableau_departs(routes, moyenne: float, aeroport: str | None, ville: str | None, n: int = 9):
    if aeroport:
        r = routes[routes["origin_airport"] == aeroport].nlargest(n, "n_vols")
        titre, sous = f"DÉPARTS · {aeroport}", f"{ville} · lignes les plus fréquentées en 2015"
    else:
        r = routes.nlargest(n, "n_vols")
        titre, sous = "DÉPARTS · ÉTATS-UNIS", "les routes les plus fréquentées de 2015"
    lignes = []
    for x in r.itertuples():
        ecart = x.taux_retard - moyenne
        classe, statut = (("ok", "À L'HEURE") if ecart < -3 else ("mauvais", "RETARDS FRÉQUENTS") if ecart > 3
                          else ("moyen", "À SURVEILLER"))
        ville_dest = (x.dest_city or x.destination_airport).upper()
        if not aeroport:
            ville_dest = f"{x.origin_airport}>{(x.dest_city or '').upper()}"
        lignes.append({"ville": ville_dest.replace("-", " "), "code": x.destination_airport,
                       "vols": str(round(x.n_vols / 52)), "ponctuel": f"{100 - x.taux_retard:.0f}%",
                       "classe": classe, "statut": statut})
    html = (GABARIT.replace("__LIGNES__", json.dumps(lignes, ensure_ascii=False))
            .replace("__TITRE__", titre).replace("__SOUS__", sous))
    st.iframe(html, height=78 + 34 * len(lignes))
