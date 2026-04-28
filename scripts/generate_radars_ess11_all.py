"""
Schwartz Value Radar Charts — alle ESS11-Länder (2023)
=======================================================
Liest direkt aus dem ESS11-Rohdatensatz und erzeugt Radarcharts
für alle 30 Länder (nicht nur die 14 aus dem Makro-Merge).

Neu gegenüber generate_radars.py:
  - Quelle: ESS11 Roh-CSV (nicht macro_schwartz_analysis_data.csv)
  - Alle 30 Länder im ESS11
  - 'a'-Suffix der Variablen wird bereinigt
  - Ungültige Codes (66, 77, 88, 99) werden als NaN behandelt
  - Aggregation: Median je Land (robuster als Mittelwert bei Skalen)
"""

# ── Lernprotokoll ──────────────────────────────────────────────────────────────
# Konzept: Direkte Rohdatenverarbeitung vs. vorbereitete Analyse-Datasets
#   Vorteile: mehr Länder verfügbar, keine Abhängigkeit vom Merge-Pipeline
#   Nachteil: Kodierungen (Missing Codes 66/77/88/99) müssen selbst behandelt werden
#
# Technik: pandas .replace() zum Maskieren ungültiger Codes → NaN
#   df.replace({66: np.nan, 77: np.nan, ...}) ist idiomatischer als
#   df[df < 7] weil es explizit dokumentiert was gefiltert wird.
#
# Konzept: groupby().median() für robuste Aggregation
#   Median ist bei ordinalen Likert-Skalen (1–6) robuster als Mittelwert,
#   da er weniger durch Ausreißer oder schiefe Verteilungen beeinflusst wird.
#
# Technik: np.ceil() für dynamisches Grid-Layout
#   ncols = 5, nrows = ceil(n / ncols) → passt sich automatisch an Länderzahl an.
# ─────────────────────────────────────────────────────────────────────────────

import os
import warnings

import matplotlib.patheffects as pe
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import requests
from io import BytesIO
from matplotlib.patches import Circle
from PIL import Image

warnings.filterwarnings('ignore')

# ── Pfade ──────────────────────────────────────────────────────────────────────
ESS11_CSV  = (
    '/home/c-vantis/jd/40_projects/43_human_values_project/'
    'data/raw/ess/ESS11/ESS11e04_1.csv'
)
OUTPUT_DIR = (
    '/home/c-vantis/jd/40_projects/43_human_values_project/'
    'visualizations/schwartz_radar_ess11_all'
)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ── Rohdaten laden ─────────────────────────────────────────────────────────────
# ESS11 nutzt 'a'-Suffix (ipcrtiva statt ipcrtiv) für den ersten Zeitpunkt
PVQ_VARS_RAW = [
    'ipcrtiva', 'ipeqopta', 'ipshabta', 'ipfrulea', 'ipudrsta', 'ipmodsta',
    'ipgdtima', 'iphlppla', 'ipsucesa', 'ipstrgva', 'ipadvnta', 'ipbhprpa',
    'iprspota', 'iplylfra',
]
MISSING_CODES = [66, 77, 88, 99]

df_raw = pd.read_csv(ESS11_CSV, usecols=['cntry'] + PVQ_VARS_RAW)

# Ungültige Codes → NaN, dann umbenennen (Suffix 'a' entfernen)
df_raw.replace({c: np.nan for c in MISSING_CODES}, inplace=True)
df_raw.rename(columns={v: v.rstrip('a') for v in PVQ_VARS_RAW}, inplace=True)

# ── Ländermittelwerte (Median) ─────────────────────────────────────────────────
PVQ_VARS = [v.rstrip('a') for v in PVQ_VARS_RAW]
df_med = df_raw.groupby('cntry')[PVQ_VARS].median()

# ── PVQ-21 → 10 Schwartz-Grundwerte ──────────────────────────────────────────
df_med['SD'] = df_med['ipcrtiv']
df_med['ST'] = df_med['ipadvnt']
df_med['HE'] = df_med['ipgdtim']
df_med['AC'] = df_med['ipsuces']
df_med['PO'] = df_med['ipshabt']
df_med['SE'] = df_med['ipstrgv']
df_med['CO'] = df_med[['ipbhprp', 'ipfrule', 'ipmodst']].mean(axis=1)
df_med['TR'] = df_med['iprspot']
df_med['BE'] = df_med[['iphlppl', 'iplylfr']].mean(axis=1)
df_med['UN'] = df_med[['ipeqopt', 'ipudrst']].mean(axis=1)

# ── Δ-Scores (Schwartz 1992) ──────────────────────────────────────────────────
VALUE_KEYS = ['SD', 'UN', 'BE', 'TR', 'CO', 'SE', 'PO', 'AC', 'HE', 'ST']
DELTA_KEYS = [f'D_{k}' for k in VALUE_KEYS]
row_mean   = df_med[VALUE_KEYS].mean(axis=1)
for k in VALUE_KEYS:
    df_med[f'D_{k}'] = df_med[k] - row_mean

DELTA_ORDER = DELTA_KEYS
N = len(DELTA_ORDER)

# ── Ländernamen (alle ESS11-Länder) ───────────────────────────────────────────
COUNTRY_NAMES = {
    'AT': 'Österreich',   'BE': 'Belgien',      'BG': 'Bulgarien',
    'CH': 'Schweiz',      'CY': 'Zypern',       'DE': 'Deutschland',
    'EE': 'Estland',      'ES': 'Spanien',       'FI': 'Finnland',
    'FR': 'Frankreich',   'GB': 'Großbritannien','GR': 'Griechenland',
    'HR': 'Kroatien',     'HU': 'Ungarn',        'IE': 'Irland',
    'IL': 'Israel',       'IS': 'Island',        'IT': 'Italien',
    'LT': 'Litauen',      'LV': 'Lettland',      'ME': 'Montenegro',
    'NL': 'Niederlande',  'NO': 'Norwegen',      'PL': 'Polen',
    'PT': 'Portugal',     'RS': 'Serbien',       'SE': 'Schweden',
    'SI': 'Slowenien',    'SK': 'Slowakei',      'UA': 'Ukraine',
}

# ── Wertebeschriftungen ────────────────────────────────────────────────────────
VALUE_LABELS = {
    'D_SD': 'Selbst-\nbestimmung',
    'D_UN': 'Universalismus',
    'D_BE': 'Wohlwollen',
    'D_TR': 'Tradition',
    'D_CO': 'Konformität',
    'D_SE': 'Sicherheit',
    'D_PO': 'Macht',
    'D_AC': 'Leistung',
    'D_HE': 'Hedonismus',
    'D_ST': 'Stimulation',
}

# Übergeordnete Bereiche (identisch mit generate_radars.py)
HIGHER_ORDER = [
    (342,  18, 'Offenheit für Wandel',   '#1a6bbd'),
    ( 18,  90, 'Selbsttranszendenz',      '#7d3c98'),
    ( 90, 198, 'Bewahrung',               '#1a8040'),
    (198, 306, 'Selbsterhöhung',          '#c0392b'),
]

# ── Skalierung ────────────────────────────────────────────────────────────────
D_MIN, D_MAX = -1.0, 1.0
PLOT_R       = 1.0

def delta_to_r(delta):
    return np.clip((delta - D_MIN) / (D_MAX - D_MIN), 0.0, 1.0) * PLOT_R

RADAR_R  = 1.00
LABEL_R  = 1.16
ARC_R    = 1.62
HILAB_R  = 1.80

# ── Farbschema ────────────────────────────────────────────────────────────────
C = dict(
    fig_bg       = '#f4f6fb',
    radar_bg     = '#e8edf5',
    grid_zero    = '#7a90b0',
    grid_minor   = '#c0ccd8',
    spoke_inner  = '#c8d4e0',
    spoke_gap    = '#d8e0ea',
    radar_stroke = '#1a5fb4',
    radar_fill   = '#3a7ad4',
    dot_face     = '#1a5fb4',
    dot_edge     = '#ffffff',
    label_val    = '#1a2840',
    label_delta  = '#0d0d0d',
    title_col    = '#0d1b2a',
    annot_col    = '#5a6a80',
)

# ── Flaggen-Cache ─────────────────────────────────────────────────────────────
FLAG_CACHE = {}

def get_flag(cc):
    if cc in FLAG_CACHE:
        return FLAG_CACHE[cc]
    url = f'https://flagpedia.net/data/flags/w320/{cc.lower()}.png'
    try:
        r   = requests.get(url, timeout=12)
        img = Image.open(BytesIO(r.content)).convert('RGBA')
        w, h  = img.size
        side  = min(w, h)
        img   = img.crop(((w - side) // 2, (h - side) // 2,
                           (w + side) // 2, (h + side) // 2))
        FLAG_CACHE[cc] = np.array(img)
        return FLAG_CACHE[cc]
    except Exception as exc:
        print(f'  [!] Flagge nicht geladen {cc}: {exc}')
        return None

# ── Hilfsfunktionen ───────────────────────────────────────────────────────────
def p2xy(ang, r):
    return r * np.sin(ang), r * np.cos(ang)

def arc_pts(start_deg, end_deg, r, n=180):
    if end_deg <= start_deg:
        end_deg += 360
    th = np.linspace(np.deg2rad(start_deg), np.deg2rad(end_deg), n)
    return r * np.sin(th), r * np.cos(th)

# ── Einzelchart ───────────────────────────────────────────────────────────────
def draw_radar(cc, save_path):
    row          = df_med.loc[cc]
    deltas       = row[DELTA_ORDER].values.astype(float)
    country_name = COUNTRY_NAMES.get(cc, cc)

    angles = np.linspace(0, 2 * np.pi, N, endpoint=False)
    radii  = np.array([delta_to_r(d) for d in deltas])
    ang_c  = np.append(angles, angles[0])
    rad_c  = np.append(radii,  radii[0])
    px, py = p2xy(ang_c, rad_c)

    fig, ax = plt.subplots(figsize=(11, 13))
    fig.subplots_adjust(left=0.03, right=0.97, top=0.90, bottom=0.10)
    ax.set_aspect('equal')
    ax.axis('off')
    fig.patch.set_facecolor(C['fig_bg'])

    t = np.linspace(0, 2 * np.pi, 720)

    # Hintergrund
    ax.add_patch(Circle((0, 0), RADAR_R, color=C['radar_bg'], zorder=0))

    # Flagge
    flag_img = get_flag(cc)
    if flag_img is not None:
        clip_circle = Circle((0, 0), RADAR_R, transform=ax.transData)
        im = ax.imshow(flag_img,
                       extent=[-RADAR_R, RADAR_R, -RADAR_R, RADAR_R],
                       aspect='auto', origin='upper', alpha=0.28, zorder=1)
        im.set_clip_path(clip_circle)

    # Gitterringe
    for dv, col, ls, lw in [(-1.0, C['grid_minor'], '--', 0.6),
                              (-0.5, C['grid_minor'], '--', 0.6),
                              ( 0.0, C['grid_zero'],  '-',  1.5),
                              (+0.5, C['grid_minor'], '--', 0.6),
                              (+1.0, C['grid_minor'], '--', 0.6)]:
        r = delta_to_r(dv) * RADAR_R
        if r < 0.001:
            continue
        ax.plot(r * np.sin(t), r * np.cos(t),
                color=col, linewidth=lw, linestyle=ls, zorder=2)

    # Speichen
    for ang in angles:
        sx_i, sy_i = p2xy(ang, RADAR_R)
        sx_o, sy_o = p2xy(ang, ARC_R * 0.985)
        ax.plot([0, sx_i], [0, sy_i],
                color=C['spoke_inner'], linewidth=0.85, zorder=2)
        ax.plot([sx_i, sx_o], [sy_i, sy_o],
                color=C['spoke_gap'], linewidth=0.65, linestyle=':', zorder=2)

    # Radar-Polygon
    ax.fill(px, py, color=C['radar_fill'], alpha=0.20, zorder=4)
    ax.plot(px, py, color=C['radar_stroke'], linewidth=2.2, zorder=5,
            solid_joinstyle='round')
    vx, vy = p2xy(angles, radii)
    ax.scatter(vx, vy, color=C['dot_face'], s=45, zorder=6,
               edgecolors=C['dot_edge'], linewidths=1.3)

    # Wertebeschriftungen + Δ-Zahlen
    for i, (ang, dk) in enumerate(zip(angles, DELTA_ORDER)):
        lx, ly = p2xy(ang, LABEL_R)
        ha = 'center' if abs(lx) < 0.22 else ('left' if lx > 0 else 'right')
        va = 'center' if abs(ly) < 0.22 else ('bottom' if ly > 0 else 'top')
        ax.text(lx, ly, VALUE_LABELS[dk],
                color=C['label_val'], fontsize=9.2, fontweight='bold',
                ha=ha, va=va, zorder=7, multialignment='center',
                path_effects=[pe.withStroke(linewidth=2.5,
                                            foreground=C['fig_bg'])])
        sign = '+' if deltas[i] >= 0 else ''
        dvx, dvy = p2xy(ang, radii[i] + 0.10)
        ax.text(dvx, dvy, f'{sign}{deltas[i]:.2f}',
                color=C['label_delta'], fontsize=8.5, fontweight='bold',
                ha='center', va='center', zorder=7,
                path_effects=[pe.withStroke(linewidth=2.2,
                                            foreground=C['fig_bg'])])

    # Farbring
    ax.plot(ARC_R * np.sin(t), ARC_R * np.cos(t),
            color='#b8c8da', linewidth=1.0, zorder=8)
    for s_deg, e_deg, label, color in HIGHER_ORDER:
        bx, by = arc_pts(s_deg, e_deg, ARC_R)
        ax.plot(bx, by, color=color, linewidth=7.0, zorder=9,
                solid_capstyle='butt')
        if e_deg <= s_deg:
            mid_deg = (s_deg + e_deg + 360) / 2 % 360
        else:
            mid_deg = (s_deg + e_deg) / 2
        tx, ty = p2xy(np.deg2rad(mid_deg), HILAB_R)
        ha_h = 'center' if abs(tx) < 0.25 else ('left' if tx > 0 else 'right')
        va_h = 'center' if abs(ty) < 0.25 else ('bottom' if ty > 0 else 'top')
        ax.text(tx, ty, label,
                color=color, fontsize=10.0, fontweight='bold',
                ha=ha_h, va=va_h, zorder=10, multialignment='center',
                path_effects=[pe.withStroke(linewidth=3.0,
                                            foreground=C['fig_bg'])])

    # Titel
    ax.text(0, HILAB_R * 1.22, country_name,
            color=C['title_col'], fontsize=24, fontweight='bold',
            ha='center', va='center', zorder=11)

    # Annotation
    annot = (
        f'ESS Round 11 (2023)  ·  Ländermediane aus ESS-Individualdaten\n'
        f'Δ = Wert − Ländermittel aller 10 Grundwerte (Schwartz 1992)\n'
        f'Ø-Ring = Länderdurchschnitt  ·  außen = überdurchschnittlich  ·  innen = unterdurchschnittlich\n'
        f'Quelle: European Social Survey (ESS)  ·  PVQ-21  ·  Skala 1 (unwichtig) – 6 (sehr wichtig)'
    )
    ax.text(0, -(HILAB_R * 1.22 + 0.08), annot,
            color=C['annot_col'], fontsize=9.0,
            ha='center', va='top', zorder=11, multialignment='center')

    LIM = HILAB_R * 1.32
    ax.set_xlim(-LIM, LIM)
    ax.set_ylim(-LIM * 1.28, LIM * 1.20)
    plt.savefig(save_path, dpi=180, facecolor=fig.get_facecolor())
    plt.close()
    print(f'  ✓  {country_name} ({cc})')


# ── Alle Länder ────────────────────────────────────────────────────────────────
countries = sorted(df_med.index.unique())
print(f'Schwartz-Radar-Charts ESS11 — alle {len(countries)} Länder...\n')
for cc in countries:
    draw_radar(cc, os.path.join(OUTPUT_DIR, f'schwartz_radar_{cc}.png'))

# ── Überblicksraster ──────────────────────────────────────────────────────────
print('\nÜberblicksraster...')
ncols = 5
nrows = int(np.ceil(len(countries) / ncols))
fig_ov, axes_ov = plt.subplots(nrows, ncols, figsize=(ncols * 6.0, nrows * 6.8))
fig_ov.patch.set_facecolor('#eef2f8')

for i, ax_ov in enumerate(axes_ov.flat):
    ax_ov.axis('off')
    if i < len(countries):
        img = Image.open(os.path.join(OUTPUT_DIR,
                         f'schwartz_radar_{countries[i]}.png'))
        ax_ov.imshow(np.array(img))

fig_ov.suptitle(
    'Schwartz-Werteprofile — Alle ESS-Round-11-Länder (2023)\n'
    'Δ-Scores: relative Werteprioritäten (zentriert am Ländermittel, Schwartz 1992)',
    color='#0d1b2a', fontsize=16, fontweight='bold', y=1.01
)
plt.tight_layout(pad=0.5)
plt.savefig(
    os.path.join(OUTPUT_DIR, 'schwartz_radar_overview_ess11_all.png'),
    dpi=150, bbox_inches='tight', facecolor=fig_ov.get_facecolor()
)
plt.close()
print('  ✓  Überblicksraster.\nFertig.')
