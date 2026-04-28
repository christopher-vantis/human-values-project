"""
Schwartz Radar — interaktives HTML für Deutschland über alle ESS-Runden
=======================================================================
Erzeugt eine selbst-enthaltene HTML-Datei mit:
  - Flüssiger 60fps-Animation via requestAnimationFrame (kein Stottern)
  - Zeitgewichteter Interpolation (2018→2023 dauert proportional länger)
  - Scrubbare Timeline + Play/Pause-Button
  - Jahrmarkierungen klickbar
  - Alles inline (Flagge als base64, kein CDN nötig)

Ausgabe: visualizations/schwartz_radar_animation_DE.html
"""

# ── Lernprotokoll ──────────────────────────────────────────────────────────────
# Konzept: requestAnimationFrame vs. setInterval
#   requestAnimationFrame synchronisiert mit dem Browser-Repaint (~60fps),
#   verbraucht keine CPU wenn der Tab im Hintergrund ist, und liefert
#   hochgenaue Timestamps (DOMHighResTimeStamp, Mikrosekunden-Präzision).
#
# Konzept: Zeitgewichtete Segmente
#   Die ESS-Abstände sind ungleich: 2002–2018 je 2 Jahre, 2018–2023 fünf Jahre.
#   cumWeights = kumulierte Anteile der Zeitspannen am Gesamtzeitraum.
#   Damit dauert der Übergang 2018→2023 proportional länger als je 2 Jahre.
#
# Technik: SVG paint-order="stroke"
#   paint-order="stroke fill" zeichnet den Stroke HINTER dem Fill, was einen
#   sauberen weißen Halo-Effekt um Texte erzeugt — ohne doppelte Text-Elemente.
#
# Konzept: Self-contained HTML
#   Alle Assets (Flagge) werden als base64-Data-URL eingebettet.
#   Das macht die Datei groß, aber vollständig offline-fähig und
#   einfach deploybar (eine einzige Datei auf den Webserver laden).
#
# Technik: String-Konkatenation statt f-String für JS-Blöcke
#   Python f-Strings erfordern {{ }} um literale JS-Klammern. Um lesbaren
#   JS-Code zu schreiben, werden Python-Variablen per Konkatenation injiziert:
#     html = '...<script>const DATA = ' + json.dumps(data) + ';</script>...'
# ─────────────────────────────────────────────────────────────────────────────

import json, base64, os, requests
import numpy as np
import pandas as pd
from io import BytesIO
from PIL import Image

# ── Konfiguration ──────────────────────────────────────────────────────────────
COUNTRY    = 'DE'
TOTAL_MS   = 11000   # ms für einen kompletten Durchlauf (≈ doppelte MP4-Speed)
SCALE      = 100     # SVG-Einheiten pro Radar-Einheit
RADAR_R    = 100
LABEL_R    = 116
ARC_R      = 162
HILAB_R    = 180
D_MIN, D_MAX = -1.0, 1.0
N_VALUES   = 10

DATA_CSV = (
    '/home/c-vantis/jd/40_projects/43_human_values_project/'
    'data/merged_datasets/macro_schwartz_analysis_data.csv'
)
OUTPUT = (
    '/home/c-vantis/jd/40_projects/43_human_values_project/'
    'visualizations/schwartz_radar_animation_DE.html'
)

C = {
    'bg':           '#f4f6fb',
    'radar_bg':     '#e8edf5',
    'grid_zero':    '#7a90b0',
    'grid_minor':   '#c0ccd8',
    'spoke_in':     '#c8d4e0',
    'spoke_out':    '#d8e0ea',
    'stroke':       '#1a5fb4',
    'fill':         '#3a7ad4',
    'dot':          '#1a5fb4',
    'label':        '#1a2840',
    'delta':        '#0d0d0d',
    'title':        '#0d1b2a',
    'annot':        '#5a6a80',
}

HIGHER_ORDER = [
    (342,  18, 'Offenheit für Wandel',   '#1a6bbd'),
    ( 18,  90, 'Selbsttranszendenz',      '#7d3c98'),
    ( 90, 198, 'Bewahrung',               '#1a8040'),
    (198, 306, 'Selbsterhöhung',          '#c0392b'),
]

VALUE_LABELS = [
    'Selbst-\nbestimmung', 'Universalismus', 'Wohlwollen',  'Tradition',
    'Konformität',         'Sicherheit',     'Macht',       'Leistung',
    'Hedonismus',          'Stimulation',
]

ANGLES = [i * 2 * np.pi / N_VALUES for i in range(N_VALUES)]

# ── Geometrie-Helfer ──────────────────────────────────────────────────────────
def p2xy(ang, r):
    """Uhrzeigersinn ab 12 Uhr → SVG-Koordinaten (y-Achse gespiegelt)."""
    return float(r * np.sin(ang)), float(-r * np.cos(ang))

def delta_to_r(d):
    return float(np.clip((d - D_MIN) / (D_MAX - D_MIN), 0.0, 1.0) * RADAR_R)

def arc_path(s_deg, e_deg, r, n=180):
    if e_deg <= s_deg:
        e_deg += 360
    angles = np.linspace(np.radians(s_deg), np.radians(e_deg), n)
    pts = [(r * np.sin(a), -r * np.cos(a)) for a in angles]
    d = f'M {pts[0][0]:.2f},{pts[0][1]:.2f}'
    d += ''.join(f' L {x:.2f},{y:.2f}' for x, y in pts[1:])
    return d

def text_anchor(x, y, threshold=22):
    ha = 'middle' if abs(x) < threshold else ('start' if x > 0 else 'end')
    va = 'middle' if abs(y) < threshold else ('auto' if y > 0 else 'hanging')
    return ha, va

# ── Daten laden ───────────────────────────────────────────────────────────────
df = pd.read_csv(DATA_CSV)
df_de = df[df['cntry'] == COUNTRY].sort_values('year').reset_index(drop=True)

df_de['SD'] = df_de['ipcrtiv_mean']
df_de['ST'] = df_de['ipadvnt_mean']
df_de['HE'] = df_de['ipgdtim_mean']
df_de['AC'] = df_de['ipsuces_mean']
df_de['PO'] = df_de['ipshabt_mean']
df_de['SE'] = df_de['ipstrgv_mean']
df_de['CO'] = df_de[['ipbhprp_mean', 'ipfrule_mean', 'ipmodst_mean']].mean(axis=1)
df_de['TR'] = df_de['iprspot_mean']
df_de['BE'] = df_de[['iphlppl_mean', 'iplylfr_mean']].mean(axis=1)
df_de['UN'] = df_de[['ipeqopt_mean', 'ipudrst_mean']].mean(axis=1)

VALUE_KEYS = ['SD', 'UN', 'BE', 'TR', 'CO', 'SE', 'PO', 'AC', 'HE', 'ST']
row_mean   = df_de[VALUE_KEYS].mean(axis=1)
for k in VALUE_KEYS:
    df_de[f'D_{k}'] = df_de[k] - row_mean
DELTA_KEYS = [f'D_{k}' for k in VALUE_KEYS]

years      = df_de['year'].astype(int).tolist()
keyframes  = [df_de.loc[i, DELTA_KEYS].values.round(4).tolist() for i in range(len(df_de))]

# Zeitgewichtete kumulative Anteile (damit 2018→2023 proportional länger dauert)
gaps         = [years[i+1] - years[i] for i in range(len(years) - 1)]
total_span   = years[-1] - years[0]
cum_weights  = [0.0] + list(np.cumsum([g / total_span for g in gaps]))

# ── Flagge als base64 ─────────────────────────────────────────────────────────
print('Flagge laden...')
try:
    resp     = requests.get(f'https://flagpedia.net/data/flags/w320/{COUNTRY.lower()}.png', timeout=12)
    img      = Image.open(BytesIO(resp.content)).convert('RGBA')
    buf      = BytesIO()
    img.save(buf, format='PNG')
    flag_b64 = 'data:image/png;base64,' + base64.b64encode(buf.getvalue()).decode()
    print('  ✓  Flagge geladen.')
except Exception as e:
    flag_b64 = ''
    print(f'  [!] Flagge nicht verfügbar: {e}')

# ── Statische SVG-Elemente ────────────────────────────────────────────────────
parts = []

# Gitterringe
for dv, col, sw, dash in [
    (-0.5, C['grid_minor'], 0.7, '4 4'),
    ( 0.0, C['grid_zero'],  1.6, ''),
    (+0.5, C['grid_minor'], 0.7, '4 4'),
    (+1.0, C['grid_minor'], 0.7, '4 4'),
]:
    r  = delta_to_r(dv)
    da = f' stroke-dasharray="{dash}"' if dash else ''
    if r > 0.5:
        parts.append(
            f'<circle cx="0" cy="0" r="{r:.2f}" fill="none" '
            f'stroke="{col}" stroke-width="{sw}"{da}/>'
        )

# Speichen
for ang in ANGLES:
    xi, yi = p2xy(ang, RADAR_R)
    xo, yo = p2xy(ang, ARC_R * 0.985)
    parts.append(
        f'<line x1="0" y1="0" x2="{xi:.2f}" y2="{yi:.2f}" '
        f'stroke="{C["spoke_in"]}" stroke-width="0.85"/>'
    )
    parts.append(
        f'<line x1="{xi:.2f}" y1="{yi:.2f}" x2="{xo:.2f}" y2="{yo:.2f}" '
        f'stroke="{C["spoke_out"]}" stroke-width="0.65" stroke-dasharray="2 3"/>'
    )

# Grauer Basis-Farbring
parts.append(
    f'<circle cx="0" cy="0" r="{ARC_R}" fill="none" stroke="#b8c8da" stroke-width="1"/>'
)

# Farbige Bögen
for s, e, label, color in HIGHER_ORDER:
    parts.append(
        f'<path d="{arc_path(s, e, ARC_R)}" fill="none" '
        f'stroke="{color}" stroke-width="7" stroke-linecap="butt"/>'
    )

# Überordnungs-Labels
for s, e, label, color in HIGHER_ORDER:
    mid   = (s + e + 360) / 2 % 360 if e <= s else (s + e) / 2
    tx,ty = p2xy(np.radians(mid), HILAB_R)
    ha,_  = text_anchor(tx, ty)
    lines = label.split('\n')
    tspans = ''.join(
        f'<tspan x="{tx:.2f}" dy="{"0" if i == 0 else "1.15em"}">{ln}</tspan>'
        for i, ln in enumerate(lines)
    )
    # Vertikal zentrieren bei mehrzeiligen Labels
    dy_base = (len(lines) - 1) * 0.575 * 10  # halbe Gesamthöhe nach oben
    parts.append(
        f'<text x="{tx:.2f}" y="{ty - dy_base:.2f}" text-anchor="{ha}" '
        f'font-size="10" font-weight="bold" fill="{color}" '
        f'paint-order="stroke" stroke="{C["bg"]}" stroke-width="3">{tspans}</text>'
    )

# Werte-Labels (statisch)
for i, (ang, label) in enumerate(zip(ANGLES, VALUE_LABELS)):
    lx, ly = p2xy(ang, LABEL_R)
    ha, _  = text_anchor(lx, ly)
    lines  = label.split('\n')
    tspans = ''.join(
        f'<tspan x="{lx:.2f}" dy="{"0" if k == 0 else "1.15em"}">{ln}</tspan>'
        for k, ln in enumerate(lines)
    )
    dy_base = (len(lines) - 1) * 0.575 * 9.5
    parts.append(
        f'<text x="{lx:.2f}" y="{ly - dy_base:.2f}" text-anchor="{ha}" '
        f'font-size="9.5" font-weight="bold" fill="{C["label"]}" '
        f'paint-order="stroke" stroke="{C["bg"]}" stroke-width="2.5">{tspans}</text>'
    )

static_svg = '\n  '.join(parts)

# ── Initiale dynamische Elemente ──────────────────────────────────────────────
init_radii = [delta_to_r(d) for d in keyframes[0]]
init_pts   = [p2xy(ang, r) for ang, r in zip(ANGLES, init_radii)]
poly_pts   = ' '.join(f'{x:.2f},{y:.2f}' for x, y in (init_pts + [init_pts[0]]))

dots_svg = '\n  '.join(
    f'<circle class="rdot" id="dot{i}" cx="{x:.2f}" cy="{y:.2f}" '
    f'r="3.5" fill="{C["dot"]}" stroke="white" stroke-width="1.1"/>'
    for i, (x, y) in enumerate(init_pts)
)

def delta_lbl(i, d, ang, ri):
    lx, ly = p2xy(ang, ri + 12)
    sign   = '+' if d >= 0 else ''
    return (
        f'<text class="dlbl" id="dlbl{i}" x="{lx:.2f}" y="{ly:.2f}" '
        f'text-anchor="middle" dominant-baseline="middle" '
        f'font-size="8.5" font-weight="bold" fill="{C["delta"]}" '
        f'paint-order="stroke" stroke="{C["bg"]}" stroke-width="2">'
        f'{sign}{d:.2f}</text>'
    )

dlbls_svg = '\n  '.join(
    delta_lbl(i, keyframes[0][i], ANGLES[i], init_radii[i])
    for i in range(N_VALUES)
)

# ── ViewBox ───────────────────────────────────────────────────────────────────
VBX = -(HILAB_R * 1.35 + 5)
VBY = -(HILAB_R * 1.35 + 38)   # Platz für Titel oben
VBW = abs(VBX) * 2
VBH = abs(VBY) + (HILAB_R * 1.35 + 55)  # Platz für Annotation unten

TITLE_Y  = VBY + 26
ANNOT_Y  = -VBY - 10

# ── Timeline-Marker HTML ──────────────────────────────────────────────────────
tl_marks = '\n'.join(
    f'<button class="ym" data-idx="{i}" data-t="{cum_weights[i]:.6f}" '
    f'style="left:{cum_weights[i]*100:.4f}%">'
    f'<span class="yd"></span>'
    f'<span class="yl">{yr}</span>'
    f'</button>'
    for i, yr in enumerate(years)
)

# ── Daten-JSON ────────────────────────────────────────────────────────────────
data_json = json.dumps({
    'years':      years,
    'keyframes':  keyframes,
    'cumWeights': cum_weights,
}, separators=(',', ':'))

# ── HTML zusammenbauen ────────────────────────────────────────────────────────
# Hinweis: JS-Blöcke werden per String-Konkatenation injiziert (nicht f-String),
# damit JS-Klammern {} nicht escaped werden müssen.

html = (
'''<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Schwartz-Werteprofile Deutschland · ESS 2002–2023</title>
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
body{
  background:''' + C['bg'] + ''';
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
  display:flex;flex-direction:column;align-items:center;
  min-height:100vh;padding:20px 16px 36px;
}
#radar{width:100%;max-width:580px;display:block}

/* ── Controls ── */
.ctrl{
  width:100%;max-width:580px;
  display:flex;align-items:flex-start;gap:12px;margin-top:10px;
}
#playBtn{
  flex-shrink:0;width:22px;height:22px;border:none;border-radius:50%;
  background:rgba(26,95,180,0.45);color:#fff;font-size:9px;cursor:pointer;
  display:flex;align-items:center;justify-content:center;
  transition:background .2s;margin-top:4px;
}
#playBtn:hover{background:rgba(26,95,180,0.75)}

/* ── Timeline ── */
.tlwrap{flex:1;position:relative;height:56px;user-select:none}
.tl-track{
  position:absolute;left:0;right:0;top:15px;
  height:3px;background:#c0ccd8;border-radius:2px;
}
.tl-prog{
  height:100%;background:''' + C['dot'] + ''';
  border-radius:2px;width:0;pointer-events:none;
}
/* year marker buttons */
.ym{
  position:absolute;top:0;
  transform:translateX(-50%);
  background:none;border:none;padding:0;
  display:flex;flex-direction:column;align-items:center;
  cursor:pointer;
}
.yd{
  width:11px;height:11px;border-radius:50%;
  background:#b0bccf;border:2.5px solid ''' + C['bg'] + ''';
  margin-top:9px;transition:background .2s,transform .2s;
  display:block;
}
.yl{
  font-size:10px;font-weight:600;color:#8090a8;
  margin-top:3px;transition:color .2s;display:block;
}
.ym.active .yd{background:''' + C['dot'] + ''';transform:scale(1.4)}
.ym.active .yl{color:''' + C['dot'] + '''}

/* Cursor-Punkt */
#tlCursor{
  position:absolute;top:7.5px;width:16px;height:16px;
  border-radius:50%;background:''' + C['dot'] + ''';
  border:2.5px solid #fff;box-shadow:0 1px 5px rgba(0,0,0,.22);
  transform:translateX(-50%);pointer-events:none;left:0;
}
/* Unsichtbarer Range-Input als Drag-Fläche */
#scrub{
  position:absolute;left:0;top:6px;
  width:100%;height:22px;opacity:0;cursor:pointer;margin:0;
  -webkit-appearance:none;
}
.note{
  max-width:580px;text-align:center;
  font-size:11px;color:''' + C['annot'] + ''';
  margin-top:9px;line-height:1.55;
}
</style>
</head>
<body>

<svg id="radar" viewBox="''' + f'{VBX:.2f} {VBY:.2f} {VBW:.2f} {VBH:.2f}' + '''"
     xmlns="http://www.w3.org/2000/svg" preserveAspectRatio="xMidYMid meet">
<defs>
  <clipPath id="fc"><circle cx="0" cy="0" r="''' + str(RADAR_R) + '''"/></clipPath>
</defs>

<!-- Radar-Hintergrund -->
<circle cx="0" cy="0" r="''' + str(RADAR_R) + '''" fill="''' + C['radar_bg'] + '''"/>

<!-- Flagge -->
''' + (
    f'<image x="-{RADAR_R}" y="-{RADAR_R}" width="{2*RADAR_R}" height="{2*RADAR_R}" '
    f'href="{flag_b64}" clip-path="url(#fc)" opacity="0.22" '
    f'preserveAspectRatio="xMidYMid slice"/>'
    if flag_b64 else ''
) + '''

<!-- Statische Elemente: Gitter, Speichen, Bögen, Labels -->
''' + static_svg + '''

<!-- Dynamisch: Radar-Polygon -->
<polygon id="rFill" points="''' + poly_pts + '''"
         fill="''' + C['fill'] + '''" fill-opacity="0.20"/>
<polyline id="rLine" points="''' + poly_pts + '''"
          fill="none" stroke="''' + C['stroke'] + '''" stroke-width="2.2" stroke-linejoin="round"/>

<!-- Dynamisch: Punkte -->
''' + dots_svg + '''

<!-- Dynamisch: Delta-Werte -->
''' + dlbls_svg + '''

<!-- Titel -->
<text x="0" y="''' + f'{TITLE_Y:.2f}' + '''" text-anchor="middle"
      font-size="22" font-weight="bold" fill="''' + C['title'] + '''">Deutschland</text>

<!-- Dynamisch: Jahreszahl in Mitte -->
<text id="yr" x="0" y="-6" text-anchor="middle" dominant-baseline="middle"
      font-size="34" font-weight="bold" fill="''' + C['title'] + '''"
      paint-order="stroke" stroke="''' + C['bg'] + '''" stroke-width="5">''' + str(years[0]) + '''</text>

<!-- Annotation -->
<text x="0" y="''' + f'{ANNOT_Y:.2f}' + '''" text-anchor="middle" font-size="8.5" fill="''' + C['annot'] + '''">
  <tspan x="0">Δ = Wert − Ländermittel aller 10 Grundwerte (Schwartz 1992) · ESS PVQ-21 · Skala 1–6</tspan>
  <tspan x="0" dy="12">Quelle: European Social Survey (ESS) · Ländermittelwerte aus Individualdaten</tspan>
</text>
</svg>

<!-- Controls -->
<div class="ctrl">
  <button id="playBtn" title="Play / Pause">⏸</button>
  <div class="tlwrap">
    <div class="tl-track"><div class="tl-prog" id="tlProg"></div></div>
''' + tl_marks + '''
    <div id="tlCursor"></div>
    <input type="range" id="scrub" min="0" max="10000" step="1" value="0">
  </div>
</div>

<script>
'use strict';
const DATA = ''' + data_json + ''';
const TOTAL_MS = ''' + str(TOTAL_MS) + ''';
const N  = DATA.years.length;
const NV = ''' + str(N_VALUES) + ''';
const RR = ''' + str(RADAR_R) + ''';
const ANGLES = Array.from({length: NV}, (_, i) => i * 2 * Math.PI / NV);

function dToR(d) {
  return Math.max(0, Math.min(1, (d + 1) / 2)) * RR;
}
function p2xy(ang, r) {
  return [r * Math.sin(ang), -r * Math.cos(ang)];
}
function lerp(a, b, t) {
  return a.map((v, i) => v * (1 - t) + b[i] * t);
}

// Gibt interpolierte Deltas für progress ∈ [0,1] zurück.
// Segmente sind zeitgewichtet (cumWeights).
function getDeltasAt(progress) {
  const cw = DATA.cumWeights;
  let seg = cw.length - 2;
  for (let i = 0; i < cw.length - 1; i++) {
    if (progress < cw[i + 1]) { seg = i; break; }
  }
  const dw = cw[seg + 1] - cw[seg];
  const t  = dw > 0 ? Math.min(1, (progress - cw[seg]) / dw) : 1;
  return lerp(DATA.keyframes[seg], DATA.keyframes[Math.min(seg + 1, N - 1)], t);
}

function getYearAt(progress) {
  const cw = DATA.cumWeights;
  let seg = cw.length - 2;
  for (let i = 0; i < cw.length - 1; i++) {
    if (progress < cw[i + 1]) { seg = i; break; }
  }
  const dw = cw[seg + 1] - cw[seg];
  const t  = dw > 0 ? Math.min(1, (progress - cw[seg]) / dw) : 1;
  return DATA.years[seg] + (DATA.years[Math.min(seg + 1, N - 1)] - DATA.years[seg]) * t;
}

// DOM
const rFill    = document.getElementById('rFill');
const rLine    = document.getElementById('rLine');
const yrTxt    = document.getElementById('yr');
const tlProg   = document.getElementById('tlProg');
const tlCursor = document.getElementById('tlCursor');
const scrub    = document.getElementById('scrub');
const playBtn  = document.getElementById('playBtn');
const dots     = Array.from({length: NV}, (_, i) => document.getElementById('dot' + i));
const dlbls    = Array.from({length: NV}, (_, i) => document.getElementById('dlbl' + i));
const ymarks   = Array.from(document.querySelectorAll('.ym'));

function updateRadar(progress) {
  const deltas = getDeltasAt(progress);
  const radii  = deltas.map(dToR);
  const pts    = ANGLES.map((a, i) => p2xy(a, radii[i]));
  const pStr   = [...pts, pts[0]].map(([x,y]) => x.toFixed(2)+','+y.toFixed(2)).join(' ');

  rFill.setAttribute('points', pStr);
  rLine.setAttribute('points', pStr);

  pts.forEach(([x, y], i) => {
    dots[i].setAttribute('cx', x.toFixed(2));
    dots[i].setAttribute('cy', y.toFixed(2));
  });

  deltas.forEach((d, i) => {
    const r        = radii[i] + 12;
    const [lx, ly] = p2xy(ANGLES[i], r);
    dlbls[i].setAttribute('x', lx.toFixed(2));
    dlbls[i].setAttribute('y', ly.toFixed(2));
    dlbls[i].textContent = (d >= 0 ? '+' : '') + d.toFixed(2);
  });

  yrTxt.textContent = Math.round(getYearAt(progress));

  const pct = progress * 100;
  tlProg.style.width   = pct + '%';
  tlCursor.style.left  = pct + '%';
  if (!userScrubbing) scrub.value = Math.round(progress * 10000);

  // Aktiven Jahr-Marker hervorheben
  const cw = DATA.cumWeights;
  let activeIdx = 0;
  for (let i = 0; i < cw.length - 1; i++) {
    if (progress >= cw[i]) activeIdx = i;
  }
  if (progress >= 0.9999) activeIdx = N - 1;
  ymarks.forEach((m, i) => m.classList.toggle('active', i === activeIdx));
}

// ── Animationsstate ────────────────────────────────────────────────────────────
let paused       = false;
let userScrubbing = false;
let progress     = 0;   // 0..1, globaler Zustand
let animStart    = null; // null → wird beim nächsten Frame gesetzt

function tick(ts) {
  if (!paused && !userScrubbing) {
    if (animStart === null) animStart = ts - progress * TOTAL_MS;
    progress = ((ts - animStart) % TOTAL_MS) / TOTAL_MS;
    updateRadar(progress);
  }
  requestAnimationFrame(tick);
}
requestAnimationFrame(tick);

// ── Play / Pause ───────────────────────────────────────────────────────────────
playBtn.addEventListener('click', () => {
  paused = !paused;
  if (!paused) animStart = null;  // wird beim nächsten Frame neu gesetzt
  playBtn.textContent = paused ? '▶' : '⏸';
});

// ── Scrubber ──────────────────────────────────────────────────────────────────
function startScrub() {
  userScrubbing = true;
  paused = true;
  playBtn.textContent = '▶';
}
function endScrub() {
  userScrubbing = false;
  paused = false;
  animStart = null;  // ab aktuellem progress weiterspielen
  playBtn.textContent = '⏸';
}
scrub.addEventListener('mousedown',  startScrub);
scrub.addEventListener('touchstart', startScrub, {passive: true});
scrub.addEventListener('mouseup',    endScrub);
scrub.addEventListener('touchend',   endScrub);
scrub.addEventListener('input', () => {
  progress = scrub.value / 10000;
  updateRadar(progress);
});

// ── Jahr-Marker klickbar ──────────────────────────────────────────────────────
ymarks.forEach(m => {
  m.addEventListener('click', () => {
    progress  = parseFloat(m.dataset.t);
    animStart = null;
    paused    = false;
    playBtn.textContent = '⏸';
    updateRadar(progress);
  });
});
</script>
</body>
</html>
''')

os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
with open(OUTPUT, 'w', encoding='utf-8') as f:
    f.write(html)

print(f'✓  Gespeichert: {OUTPUT}')
