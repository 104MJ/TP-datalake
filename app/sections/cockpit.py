"""Composants « cockpit » (st.components.v2) : instruments de bord animés et profil de vol cliquable."""

import streamlit as st

from sections.theme import ORANGE, RAMPE, RAMPE_NUIT, nuit, pal

AVION = ("M14 1c1.2 0 2 1.4 2 3v6l9 5.2v2.6l-9-2.6v5.6l3 2.3v2.1l-5-1.4-5 1.4v-2.1l3-2.3v-5.6l-9 2.6v-2.6"
         "l9-5.2V4c0-1.6.8-3 2-3z")

COMMUN_JS = """
const CALME = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
const nf = (d) => new Intl.NumberFormat("fr-FR", { minimumFractionDigits: d, maximumFractionDigits: d });
const NS = "http://www.w3.org/2000/svg";
const el = (tag, attrs = {}, parent) => {
  const e = document.createElementNS(NS, tag);
  for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
  if (parent) parent.appendChild(e);
  return e;
};
const racine = (parent) => {
  let r = parent.querySelector(".racine");
  if (!r) { r = document.createElement("div"); r.className = "racine"; parent.appendChild(r); }
  r.innerHTML = "";
  return r;
};
const compte = (node, de, a, fmt, duree = 1100) => {
  if (CALME) { node.textContent = fmt(a); return; }
  const t0 = performance.now();
  const pas = (t) => {
    const k = Math.min((t - t0) / duree, 1), e = 1 - Math.pow(1 - k, 3);
    node.textContent = fmt(de + (a - de) * e);
    if (k < 1) requestAnimationFrame(pas);
  };
  requestAnimationFrame(pas);
};
"""

# ---------------------------------------------------------------- instruments
INSTRUMENTS_CSS = """
:host { display: block; }
.grille { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 16px; font-family: 'DM Sans', system-ui, sans-serif; }
@media (max-width: 1000px) { .grille { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
.inst { background: var(--card); border: 1px solid var(--line); border-radius: 16px; padding: 14px 16px 12px;
        transition: transform .2s ease, box-shadow .2s ease; animation: monte .55s cubic-bezier(.2, .7, .3, 1) both; }
.inst:hover { transform: translateY(-3px); box-shadow: 0 14px 30px rgba(11, 37, 69, 0.12); }
.inst:nth-child(2) { animation-delay: .08s; } .inst:nth-child(3) { animation-delay: .16s; } .inst:nth-child(4) { animation-delay: .24s; }
@keyframes monte { from { opacity: 0; transform: translateY(14px); } to { opacity: 1; transform: none; } }
.nom { font-size: 13.5px; font-weight: 600; color: var(--ink2); display: flex; justify-content: space-between; }
.nom span { font-weight: 500; color: var(--muted); font-size: 12px; }
svg { display: block; width: 100%; height: auto; overflow: visible; }
.valeur { font-size: 28px; font-weight: 700; color: var(--ink); line-height: 1; margin-top: 2px; }
.sous { font-size: 12.5px; color: var(--ink2); margin-top: 5px; min-height: 18px; }
.ecart { display: inline-flex; gap: 4px; align-items: center; padding: 2px 8px; border-radius: 99px; font-weight: 700; font-size: 12px; }
.mieux { background: rgba(12, 163, 12, 0.14); color: var(--bon); } .pire { background: rgba(208, 59, 59, 0.14); color: var(--mauvais); }
.aiguille { transition: transform 1.3s cubic-bezier(.3, 1.4, .5, 1); }
.aiguille-h { transition: transform 1.3s cubic-bezier(.3, 1.2, .5, 1); }
@media (prefers-reduced-motion: reduce) { .aiguille, .aiguille-h, .inst { transition: none; animation: none; } }
"""

INSTRUMENTS_JS = COMMUN_JS + """
export default function (component) {
  const { data, parentElement } = component;
  const T = data.theme;
  const avant = parentElement.__avant || { risque: 0, vols: 0, annul: 0, heure: 0 };
  const g = racine(parentElement);
  g.classList.add("grille");
  for (const [k, v] of Object.entries({ "--card": T.card, "--line": T.line, "--ink": T.ink, "--ink2": T.ink2,
      "--muted": T.muted, "--bon": T.bon, "--mauvais": T.mauvais })) g.style.setProperty(k, v);

  const carte = (nom, aide) => {
    const c = document.createElement("div"); c.className = "inst";
    c.innerHTML = `<div class="nom">${nom}<span>${aide || ""}</span></div>`;
    g.appendChild(c); return c;
  };
  const texte = (c, cls) => { const d = document.createElement("div"); d.className = cls; c.appendChild(d); return d; };
  const ecart = (c, d, unite) => {
    const s = texte(c, "sous");
    if (d === null || d === undefined) { s.textContent = c.dataset.ref || ""; return; }
    const mieux = d < 0;
    s.innerHTML = `<span class="ecart ${mieux ? "mieux" : "pire"}">${mieux ? "▼" : "▲"} ${nf(1).format(Math.abs(d))} ${unite}</span>
                   <span style="color:${T.muted}"> vs tous les vols</span>`;
  };

  // Cadran semi-circulaire : aiguille de 0 à max, repère de la moyenne
  const cadran = (c, v, max, ref, pas, suffixe) => {
    const s = el("svg", { viewBox: "0 -8 200 126" }, c);
    const R = 76, cx = 100, cy = 100;
    const pt = (x, r = R) => { const a = Math.PI * (1 - x / max); return [cx + r * Math.cos(a), cy - r * Math.sin(a)]; };
    el("path", { d: `M ${cx - R} ${cy} A ${R} ${R} 0 0 1 ${cx + R} ${cy}`, fill: "none", stroke: T.track, "stroke-width": 12, "stroke-linecap": "round" }, s);
    const arc = el("path", { d: `M ${cx - R} ${cy} A ${R} ${R} 0 0 1 ${cx + R} ${cy}`, fill: "none", stroke: T.orange,
                             "stroke-width": 12, "stroke-linecap": "round", pathLength: 100, "stroke-dasharray": `0 100` }, s);
    arc.style.transition = "stroke-dasharray 1.3s cubic-bezier(.3, 1, .5, 1)";
    let i = 0;
    for (let x = 0; x <= max + 1e-9; x += pas, i++) {
      const [x1, y1] = pt(x, R - 13), [x2, y2] = pt(x, R - (i % 2 ? 16 : 20));
      el("line", { x1, y1, x2, y2, stroke: T.muted, "stroke-width": 1.2 }, s);
      if (i % 2) continue;
      const [tx, ty] = pt(x, R - 31);
      const t = el("text", { x: tx, y: ty + 3, "text-anchor": "middle", "font-size": 9.5, fill: T.muted }, s);
      t.textContent = nf(0).format(x);
    }
    if (ref !== null) {
      const [x1, y1] = pt(ref, R + 9), [x2, y2] = pt(ref, R - 9);
      el("line", { x1, y1, x2, y2, stroke: T.ink, "stroke-width": 2.2, "stroke-linecap": "round" }, s);
      const [tx, ty] = pt(ref, R + 17);
      const t = el("text", { x: tx, y: ty + 2, "text-anchor": "middle", "font-size": 9, fill: T.ink2 }, s);
      t.textContent = "moyenne";
    }
    const aig = el("g", { class: "aiguille" }, s);
    aig.style.transformOrigin = `${cx}px ${cy}px`;
    el("path", { d: `M ${cx - 3.5} ${cy} L ${cx} ${cy - R + 16} L ${cx + 3.5} ${cy} Z`, fill: T.ink }, aig);
    el("circle", { cx, cy, r: 7, fill: T.ink }, s);
    el("circle", { cx, cy, r: 3, fill: T.orange }, s);
    const angle = (x) => -90 + 180 * Math.min(x, max) / max;
    return { appliquer: (de) => {
      aig.style.transform = `rotate(${angle(de)}deg)`;
      arc.setAttribute("stroke-dasharray", `${100 * Math.min(de, max) / max} 100`);
      requestAnimationFrame(() => requestAnimationFrame(() => {
        aig.style.transform = `rotate(${angle(v)}deg)`;
        arc.setAttribute("stroke-dasharray", `${100 * Math.min(v, max) / max} 100`);
      }));
    } };
  };

  // 1. Risque de retard
  const r = data.risque, c1 = carte("Risque de retard", "≥ 15 min à l'arrivée");
  cadran(c1, r.valeur, r.max, r.ref, 5).appliquer(avant.risque);
  const v1 = texte(c1, "valeur"); compte(v1, avant.risque, r.valeur, x => nf(1).format(x) + " %");
  ecart(c1, r.delta, "pts");

  // 2. Vols : compteur et mini-barres mensuelles
  const vo = data.vols, c2 = carte("Vols", vo.part);
  const s2 = el("svg", { viewBox: "0 0 200 118" }, c2);
  const mx = Math.max(...vo.mois, 1);
  vo.mois.forEach((n, i) => {
    const h = 86 * n / mx, x = 8 + i * 15.5;
    const b = el("rect", { x, y: 104 - h, width: 10, height: h, rx: 3, fill: vo.dans[i] ? T.orange : T.gris }, s2);
    const tt = el("title", {}, b); tt.textContent = `${vo.noms[i]} : ${nf(0).format(n)} vols`;
    if (!CALME) { b.style.transformOrigin = `0 104px`; b.style.transform = "scaleY(0)";
      b.style.transition = `transform .7s cubic-bezier(.3, 1.2, .5, 1) ${i * 45}ms`;
      requestAnimationFrame(() => requestAnimationFrame(() => { b.style.transform = "scaleY(1)"; })); }
    if (i % 3 === 0) { const t = el("text", { x: x + 5, y: 116, "text-anchor": "middle", "font-size": 9, fill: T.muted }, s2); t.textContent = vo.noms[i]; }
  });
  const v2 = texte(c2, "valeur");
  compte(v2, avant.vols, vo.valeur, x => x >= 1e6 ? nf(2).format(x / 1e6) + " M" : x >= 1e4 ? nf(0).format(x / 1e3) + " k" : nf(0).format(x));
  texte(c2, "sous").textContent = "programmés, par mois";

  // 3. Annulations
  const a = data.annul, c3 = carte("Vols annulés", "sur tous les vols programmés");
  cadran(c3, a.valeur, a.max, a.ref, 1).appliquer(avant.annul);
  const v3 = texte(c3, "valeur"); compte(v3, avant.annul, a.valeur, x => nf(1).format(x) + " %");
  ecart(c3, a.delta, "pts");

  // 4. Horloge du risque : 24 secteurs colorés, l'aiguille montre la meilleure heure
  const ho = data.heure, c4 = carte("Meilleure heure de départ", "couleur = risque");
  const s4 = el("svg", { viewBox: "0 0 200 124" }, c4);
  const cx = 100, cy = 66, R1 = 50, R2 = 33;
  const par = Object.fromEntries(ho.heures.map(o => [o.h, o]));
  const vals = ho.heures.map(o => o.t), lo = Math.min(...vals), hi = Math.max(...vals);
  const pol = (h, r) => { const a = (h / 24) * 2 * Math.PI - Math.PI / 2; return [cx + r * Math.cos(a), cy + r * Math.sin(a)]; };
  for (let h = 0; h < 24; h++) {
    const [ax, ay] = pol(h - 0.46, R1), [bx, by] = pol(h + 0.46, R1), [cx2, cy2] = pol(h + 0.46, R2), [dx, dy] = pol(h - 0.46, R2);
    const o = par[h], k = o ? (o.t - lo) / Math.max(hi - lo, 1e-9) : null;
    const couleur = o ? T.rampe[Math.min(Math.round(k * (T.rampe.length - 1)), T.rampe.length - 1)] : T.track;
    const p = el("path", { d: `M ${ax} ${ay} A ${R1} ${R1} 0 0 1 ${bx} ${by} L ${cx2} ${cy2} A ${R2} ${R2} 0 0 0 ${dx} ${dy} Z`,
                           fill: couleur, stroke: T.card, "stroke-width": 1 }, s4);
    const tt = el("title", {}, p); tt.textContent = o ? `${h} h : ${nf(1).format(o.t)} % de retard` : `${h} h : trop peu de vols`;
  }
  [0, 6, 12, 18].forEach(h => { const [x, y] = pol(h, R1 + 9); const t = el("text", { x, y: y + 3, "text-anchor": "middle", "font-size": 9, fill: T.muted }, s4); t.textContent = `${h} h`; });
  const aigH = el("g", { class: "aiguille-h" }, s4);
  aigH.style.transformOrigin = `${cx}px ${cy}px`;
  el("path", { d: `M ${cx - 3} ${cy} L ${cx} ${cy - R2 + 6} L ${cx + 3} ${cy} Z`, fill: T.ink }, aigH);
  el("circle", { cx, cy, r: 5, fill: T.ink }, s4);
  aigH.style.transform = `rotate(${avant.heure * 15}deg)`;
  requestAnimationFrame(() => requestAnimationFrame(() => { aigH.style.transform = `rotate(${ho.meilleure * 15}deg)`; }));
  const v4 = texte(c4, "valeur"); v4.textContent = `${ho.meilleure} h`;
  texte(c4, "sous").textContent = `${nf(1).format(ho.taux)} % de retard à cette heure`;

  parentElement.__avant = { risque: r.valeur, vols: vo.valeur, annul: a.valeur, heure: ho.meilleure };
}
"""

# ---------------------------------------------------------------- profil de vol
PROFIL_CSS = """
:host { display: block; }
.boite { position: relative; font-family: 'DM Sans', system-ui, sans-serif; }
svg { display: block; width: 100%; overflow: visible; }
.bulle { position: absolute; pointer-events: none; background: var(--card); color: var(--ink); border: 1px solid var(--line);
         border-radius: 10px; padding: 7px 10px; font-size: 13px; box-shadow: 0 6px 18px rgba(11, 37, 69, .18); opacity: 0;
         transition: opacity .12s; white-space: nowrap; }
.bulle b { font-size: 15px; }
.colonne { cursor: pointer; }
.legende { display: flex; gap: 16px; font-size: 12.5px; color: var(--ink2); margin: 0 0 4px 2px; }
.legende i { display: inline-block; width: 16px; height: 2.5px; border-radius: 2px; margin-right: 6px; vertical-align: middle; }
"""

PROFIL_JS = COMMUN_JS + """
export default function (component) {
  const { data, parentElement, setTriggerValue } = component;
  const T = data.theme, P = data.points, REF = data.ref;
  const boite = racine(parentElement); boite.classList.add("boite");
  for (const [k, v] of Object.entries({ "--card": T.card, "--line": T.line, "--ink": T.ink, "--ink2": T.ink2 })) boite.style.setProperty(k, v);
  if (REF.length) {
    const lg = document.createElement("div"); lg.className = "legende";
    lg.innerHTML = `<span><i style="background:${T.orange}"></i>Votre sélection</span><span><i style="background:${T.gris}"></i>Tous les vols</span>`;
    boite.appendChild(lg);
  }
  const W = Math.max(boite.getBoundingClientRect().width || 700, 320), H = data.hauteur;
  const m = { l: 40, r: 18, t: 30, b: 28 };
  const ymax = Math.ceil(Math.max(...P.map(p => p.t), ...REF.map(p => p.t), 5) * 1.18 / 5) * 5;
  const X = h => m.l + (h - 4.5) / 19 * (W - m.l - m.r), Y = t => H - m.b - t / ymax * (H - m.t - m.b);
  const s = el("svg", { viewBox: `0 0 ${W} ${H}`, height: H, role: "img",
                        "aria-label": "Part des vols en retard selon l'heure de départ" }, boite);

  if (data.sel) el("rect", { x: X(data.sel[0] - 0.5), y: m.t - 8, width: X(data.sel[1] + 0.5) - X(data.sel[0] - 0.5),
                             height: H - m.t - m.b + 8, fill: T.orange, opacity: 0.08, rx: 6 }, s);
  for (let y = 0; y <= ymax; y += 5) {
    el("line", { x1: m.l, x2: W - m.r, y1: Y(y), y2: Y(y), stroke: y === 0 ? T.muted : T.grille, "stroke-width": y === 0 ? 1.5 : 1 }, s);
    const t = el("text", { x: m.l - 8, y: Y(y) + 4, "text-anchor": "end", "font-size": 11, fill: T.muted }, s); t.textContent = `${y} %`;
  }
  for (let h = 5; h <= 23; h += 3) { const t = el("text", { x: X(h), y: H - 8, "text-anchor": "middle", "font-size": 11, fill: T.muted }, s); t.textContent = `${h} h`; }
  // Piste de décollage
  el("line", { x1: X(4.6), x2: X(5.6), y1: Y(0), y2: Y(0), stroke: T.ink, "stroke-width": 4, "stroke-linecap": "round" }, s);

  const courbe = pts => {
    if (pts.length < 2) return "";
    let d = `M ${X(pts[0].h)} ${Y(pts[0].t)}`;
    for (let i = 0; i < pts.length - 1; i++) {
      const p0 = pts[Math.max(i - 1, 0)], p1 = pts[i], p2 = pts[i + 1], p3 = pts[Math.min(i + 2, pts.length - 1)];
      const c1 = [X(p1.h) + (X(p2.h) - X(p0.h)) / 6, Y(p1.t) + (Y(p2.t) - Y(p0.t)) / 6];
      const c2 = [X(p2.h) - (X(p3.h) - X(p1.h)) / 6, Y(p2.t) - (Y(p3.t) - Y(p1.t)) / 6];
      d += ` C ${c1[0]} ${c1[1]} ${c2[0]} ${c2[1]} ${X(p2.h)} ${Y(p2.t)}`;
    }
    return d;
  };
  if (REF.length) el("path", { d: courbe(REF), fill: "none", stroke: T.gris, "stroke-width": 2 }, s);
  const dC = courbe(P);
  el("path", { d: `${dC} L ${X(P[P.length - 1].h)} ${Y(0)} L ${X(P[0].h)} ${Y(0)} Z`, fill: T.orange, opacity: 0.10 }, s);
  const ligne = el("path", { d: dC, fill: "none", stroke: T.orange, "stroke-width": 2.5, "stroke-linecap": "round" }, s);
  const pts = P.map(p => el("circle", { cx: X(p.h), cy: Y(p.t), r: 4, fill: T.orange, stroke: T.card, "stroke-width": 2 }, s));
  const iMax = P.reduce((a, p, i) => p.t > P[a].t ? i : a, 0), iMin = P.reduce((a, p, i) => p.t < P[a].t ? i : a, 0);
  [[iMax, -14], [iMin, 20]].forEach(([i, dy]) => {
    const t = el("text", { x: X(P[i].h), y: Y(P[i].t) + dy, "text-anchor": "middle", "font-size": 13, "font-weight": 700, fill: T.ink }, s);
    t.textContent = `${nf(0).format(P[i].t)} %`;
  });

  // L'avion décolle à 5 h et trace la courbe jusqu'à 23 h
  const avion = el("g", {}, s);
  el("path", { d: "%AVION%", fill: T.ink, stroke: T.card, "stroke-width": 1.2, transform: "translate(-14 -14) rotate(90 14 14)" }, avion);
  const L = ligne.getTotalLength();
  const placer = l => {
    const a = ligne.getPointAtLength(l), b = ligne.getPointAtLength(Math.min(l + 1, L));
    const ang = Math.atan2(b.y - a.y, b.x - a.x) * 180 / Math.PI;
    avion.setAttribute("transform", `translate(${a.x} ${a.y - 13}) rotate(${ang})`);
  };
  if (CALME) { placer(L - 0.5); } else {
    ligne.setAttribute("stroke-dasharray", `${L} ${L}`);
    const t0 = performance.now(), duree = 2600;
    const vol = t => {
      const k = Math.min((t - t0) / duree, 1), e = k < .5 ? 2 * k * k : 1 - Math.pow(-2 * k + 2, 2) / 2;
      const l = e * L;
      ligne.setAttribute("stroke-dashoffset", `${L - l}`);
      placer(Math.min(l, L - 0.5));
      if (k < 1) requestAnimationFrame(vol);
      else { ligne.removeAttribute("stroke-dasharray"); ligne.removeAttribute("stroke-dashoffset"); }
    };
    requestAnimationFrame(vol);
  }

  // Survol et clic : une colonne par heure, plus large que le point
  const bulle = document.createElement("div"); bulle.className = "bulle"; boite.appendChild(bulle);
  const pas = (W - m.l - m.r) / 19;
  P.forEach((p, i) => {
    const col = el("rect", { x: X(p.h) - pas / 2, y: m.t - 10, width: pas, height: H - m.t - m.b + 10, fill: "transparent", class: "colonne" }, s);
    col.addEventListener("mouseenter", () => {
      pts[i].setAttribute("r", 6.5);
      bulle.innerHTML = `${p.h} h : <b>${nf(1).format(p.t)} %</b> de retard<br>${nf(0).format(p.n)} vols · cliquez pour choisir`;
      const x = Math.min(Math.max(X(p.h) - 90, 0), W - 200);
      bulle.style.left = `${x}px`; bulle.style.top = `${Math.max(Y(p.t) - 70, 0) + (REF.length ? 24 : 0)}px`; bulle.style.opacity = 1;
    });
    col.addEventListener("mouseleave", () => { pts[i].setAttribute("r", 4); bulle.style.opacity = 0; });
    col.addEventListener("click", () => setTriggerValue("heure", p.h));
  });
}
""".replace("%AVION%", AVION)

_instruments = st.components.v2.component("cockpit_instruments", css=INSTRUMENTS_CSS, js=INSTRUMENTS_JS)
_profil = st.components.v2.component("cockpit_profil", css=PROFIL_CSS, js=PROFIL_JS)


def _theme() -> dict:
    p = pal()
    return {"card": p["card"], "line": p["line"], "ink": p["ink"], "ink2": p["ink2"], "muted": p["muted"],
            "track": p["track"], "gris": p["gray"], "grille": p["grid"], "orange": ORANGE,
            "bon": "#0CA30C" if nuit() else "#006300", "mauvais": "#E66767" if nuit() else "#B42424",
            "rampe": RAMPE_NUIT if nuit() else RAMPE}


def instruments(risque: dict, vols: dict, annul: dict, heure: dict):
    _instruments(data={"theme": _theme(), "risque": risque, "vols": vols, "annul": annul, "heure": heure},
                 key="instruments", height="content")


def profil_vol(points: list, ref: list, sel, on_heure, hauteur: int = 300):
    _profil(data={"theme": _theme(), "points": points, "ref": ref, "sel": sel, "hauteur": hauteur},
            key="profil", height="content", on_heure_change=on_heure)
