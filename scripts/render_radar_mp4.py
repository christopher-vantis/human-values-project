"""
Schwartz Radar — MP4-Export für Deutschland (LinkedIn/Social Media)
===================================================================
Erzeugt visualizations/schwartz_radar_animation_DE.mp4

Gleiche Logik wie animate_radar_de_html.py:
  - Zeitgewichtete Segmente (2018→2023 dauert proportional länger)
  - Keine Holds an Keyframes — durchgehend flüssig
  - ~11 Sekunden, 30 fps
"""

# ── Lernprotokoll → scripts/learning_protocols/render_radar_mp4.pdf ───────────

import os, warnings
import numpy as np
import pandas as pd
import requests
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import matplotlib.patheffects as pe
from matplotlib.patches import Circle, Polygon as MplPolygon
from matplotlib.gridspec import GridSpec
from PIL import Image
from io import BytesIO

warnings.filterwarnings('ignore')

# ── Konfiguration ──────────────────────────────────────────────────────────────
TOTAL_MS   = 11_000   # Animationslänge in ms
FPS        = 30
TOTAL_FRAMES = int(TOTAL_MS / 1000 * FPS)   # 330

DATA_CSV = ('/home/c-vantis/jd/40_projects/43_human_values_project/'
            'data/merged_datasets/macro_schwartz_analysis_data.csv')
OUTPUT   = ('/home/c-vantis/jd/40_projects/43_human_values_project/'
            'visualizations/schwartz_radar_animation_DE.mp4')

C = dict(
    fig_bg      ='#f4f6fb', radar_bg='#e8edf5',
    grid_zero   ='#7a90b0', grid_minor='#c0ccd8',
    spoke_in    ='#c8d4e0', spoke_out='#d8e0ea',
    stroke      ='#1a5fb4', fill='#3a7ad4',
    dot         ='#1a5fb4', label='#1a2840',
    delta       ='#0d0d0d', title='#0d1b2a', annot='#5a6a80',
    tl_active   ='#1a5fb4', tl_inactive='#b0bccf',
)

HIGHER_ORDER = [
    (342,  18, 'Offenheit\nfür Wandel',  '#1a6bbd'),
    ( 18,  90, 'Selbst-\ntranszendenz',  '#7d3c98'),
    ( 90, 198, 'Bewahrung',              '#1a8040'),
    (198, 306, 'Selbst-\nerhöhung',      '#c0392b'),
]
VALUE_LABELS = {
    0:'Selbst-\nbestimmung', 1:'Universalismus', 2:'Wohlwollen', 3:'Tradition',
    4:'Konformität',         5:'Sicherheit',     6:'Macht',      7:'Leistung',
    8:'Hedonismus',          9:'Stimulation',
}

N_VAL   = 10
ANGLES  = np.linspace(0, 2*np.pi, N_VAL, endpoint=False)
D_MIN, D_MAX = -1.0, 1.0
RADAR_R = 1.0
LABEL_R = 1.16
ARC_R   = 1.62
HILAB_R = 1.80

def delta_to_r(d):
    return float(np.clip((d - D_MIN) / (D_MAX - D_MIN), 0, 1) * RADAR_R)

def p2xy(ang, r):
    return r * np.sin(ang), r * np.cos(ang)

def arc_pts(s_deg, e_deg, r, n=180):
    if e_deg <= s_deg: e_deg += 360
    th = np.linspace(np.deg2rad(s_deg), np.deg2rad(e_deg), n)
    return r * np.sin(th), r * np.cos(th)

# ── Daten ──────────────────────────────────────────────────────────────────────
df    = pd.read_csv(DATA_CSV)
df_de = df[df['cntry'] == 'DE'].sort_values('year').reset_index(drop=True)

df_de['SD'] = df_de['ipcrtiv_mean']
df_de['ST'] = df_de['ipadvnt_mean']
df_de['HE'] = df_de['ipgdtim_mean']
df_de['AC'] = df_de['ipsuces_mean']
df_de['PO'] = df_de['ipshabt_mean']
df_de['SE'] = df_de['ipstrgv_mean']
df_de['CO'] = df_de[['ipbhprp_mean','ipfrule_mean','ipmodst_mean']].mean(1)
df_de['TR'] = df_de['iprspot_mean']
df_de['BE'] = df_de[['iphlppl_mean','iplylfr_mean']].mean(1)
df_de['UN'] = df_de[['ipeqopt_mean','ipudrst_mean']].mean(1)

VK = ['SD','UN','BE','TR','CO','SE','PO','AC','HE','ST']
rm = df_de[VK].mean(1)
for k in VK: df_de[f'D_{k}'] = df_de[k] - rm
DK = [f'D_{k}' for k in VK]

years     = df_de['year'].astype(int).tolist()
keyframes = [df_de.loc[i, DK].values.astype(float) for i in range(len(df_de))]

# Zeitgewichtete kumulative Anteile
gaps        = [years[i+1] - years[i] for i in range(len(years)-1)]
total_span  = years[-1] - years[0]
cum_weights = [0.0] + list(np.cumsum([g/total_span for g in gaps]))

def get_deltas_at(progress):
    cw  = cum_weights
    seg = len(cw) - 2
    for i in range(len(cw)-1):
        if progress < cw[i+1]: seg = i; break
    dw = cw[seg+1] - cw[seg]
    t  = min(1.0, (progress - cw[seg]) / dw) if dw > 0 else 1.0
    a, b = keyframes[seg], keyframes[min(seg+1, len(keyframes)-1)]
    return a*(1-t) + b*t

def get_year_at(progress):
    cw  = cum_weights
    seg = len(cw) - 2
    for i in range(len(cw)-1):
        if progress < cw[i+1]: seg = i; break
    dw = cw[seg+1] - cw[seg]
    t  = min(1.0, (progress - cw[seg]) / dw) if dw > 0 else 1.0
    return years[seg] + (years[min(seg+1, len(years)-1)] - years[seg]) * t

# ── Flagge ─────────────────────────────────────────────────────────────────────
print('Flagge laden...')
try:
    resp     = requests.get('https://flagpedia.net/data/flags/w320/de.png', timeout=12)
    flag_img = np.array(Image.open(BytesIO(resp.content)).convert('RGBA'))
    print('  ✓')
except Exception as e:
    flag_img = None
    print(f'  [!] {e}')

# ── Figur aufbauen ─────────────────────────────────────────────────────────────
fig = plt.figure(figsize=(8, 10), facecolor=C['fig_bg'])  # 1040×1300 px, 4:5 für LinkedIn
gs  = GridSpec(2, 1, figure=fig, height_ratios=[10, 2.5],
               left=0.02, right=0.98, top=0.97, bottom=0.02, hspace=0.02)
ax    = fig.add_subplot(gs[0])
ax_tl = fig.add_subplot(gs[1])

ax.set_aspect('equal'); ax.axis('off')
ax_tl.axis('off')
ax_tl.set_facecolor('#e8ecf4')
fig.patch.set_facecolor(C['fig_bg'])

t_full = np.linspace(0, 2*np.pi, 720)
LIM    = HILAB_R * 1.24   # enger als zuvor (1.32) → weniger Weißraum

# ── Statische Radar-Elemente ───────────────────────────────────────────────────
ax.add_patch(Circle((0,0), RADAR_R, color=C['radar_bg'], zorder=0))

if flag_img is not None:
    clip = Circle((0,0), RADAR_R, transform=ax.transData)
    im   = ax.imshow(flag_img, extent=[-RADAR_R,RADAR_R,-RADAR_R,RADAR_R],
                     aspect='auto', origin='upper', alpha=0.22, zorder=1)
    im.set_clip_path(clip)

for dv, col, ls, lw in [(-0.5,C['grid_minor'],'--',0.6),(0.0,C['grid_zero'],'-',1.5),
                          (0.5,C['grid_minor'],'--',0.6),(1.0,C['grid_minor'],'--',0.6)]:
    r = delta_to_r(dv)
    if r > 0.001:
        ax.plot(r*np.sin(t_full), r*np.cos(t_full),
                color=col, linewidth=lw, linestyle=ls, zorder=2)

for ang in ANGLES:
    xi,yi = p2xy(ang, RADAR_R)
    xo,yo = p2xy(ang, ARC_R*0.985)
    ax.plot([0,xi],[0,yi], color=C['spoke_in'],  linewidth=0.85, zorder=2)
    ax.plot([xi,xo],[yi,yo], color=C['spoke_out'], linewidth=0.65,
            linestyle=':', zorder=2)

ax.plot(ARC_R*np.sin(t_full), ARC_R*np.cos(t_full),
        color='#b8c8da', linewidth=1.0, zorder=8)

for s,e,label,color in HIGHER_ORDER:
    bx,by = arc_pts(s, e, ARC_R)
    ax.plot(bx, by, color=color, linewidth=7.0, zorder=9, solid_capstyle='butt')
    mid   = (s+e+360)/2 % 360 if e<=s else (s+e)/2
    tx,ty = p2xy(np.deg2rad(mid), HILAB_R)
    ha    = 'center' if abs(tx)<0.25 else ('left' if tx>0 else 'right')
    va    = 'center' if abs(ty)<0.25 else ('bottom' if ty>0 else 'top')
    ax.text(tx, ty, label, color=color, fontsize=8.0, fontweight='bold',
            ha=ha, va=va, zorder=10, multialignment='center',
            path_effects=[pe.withStroke(linewidth=3, foreground=C['fig_bg'])])

for i, ang in enumerate(ANGLES):
    lx,ly = p2xy(ang, LABEL_R)
    ha = 'center' if abs(lx)<0.22 else ('left' if lx>0 else 'right')
    va = 'center' if abs(ly)<0.22 else ('bottom' if ly>0 else 'top')
    ax.text(lx, ly, VALUE_LABELS[i],
            color=C['label'], fontsize=7.5, fontweight='bold',
            ha=ha, va=va, zorder=7, multialignment='center',
            path_effects=[pe.withStroke(linewidth=2.5, foreground=C['fig_bg'])])

ax.text(0, HILAB_R*1.22, 'Deutschland',
        color=C['title'], fontsize=21, fontweight='bold',
        ha='center', va='center', zorder=11)

ax.set_xlim(-LIM, LIM)
ax.set_ylim(-1.88, LIM*1.06)   # unterer Rand knapp hinter Arc (-1.62) → kein Leerraum

# ── Statische Timeline ─────────────────────────────────────────────────────────
year_min, year_max = years[0], years[-1]

def yr2x(y): return (y - year_min) / (year_max - year_min)

ax_tl.axhline(0.92, xmin=0.0, xmax=1.0,
               color=C['tl_inactive'], linewidth=2.5, zorder=1)

for i, yr in enumerate(years):
    xp = yr2x(yr)
    ax_tl.plot(xp, 0.92, 'o', color=C['tl_inactive'], markersize=7, zorder=2,
               markeredgecolor='white', markeredgewidth=1.3)
    ax_tl.text(xp, 0.70, str(yr), color=C['tl_inactive'],
               fontsize=7.5, fontweight='bold', ha='center', va='top')

# Quelltext am unteren Rand des Timeline-Streifens
ax_tl.text(0.5, 0.05,
           'Δ = Wert − Ländermittel aller 10 Grundwerte (Schwartz 1992)  ·  '
           'ESS PVQ-21  ·  Skala 1–6\nQuelle: European Social Survey  ·  '
           'Ländermittelwerte aus ESS-Individualdaten',
           color=C['annot'], fontsize=7.5, ha='center', va='bottom',
           transform=ax_tl.transAxes, multialignment='center')

ax_tl.set_xlim(-0.01, 1.01)
ax_tl.set_ylim(0, 1)

# ── Animierte Elemente (initial) ───────────────────────────────────────────────
init_d = keyframes[0]
init_r = np.array([delta_to_r(d) for d in init_d])
init_p = [p2xy(a, r) for a, r in zip(ANGLES, init_r)]

ang_c  = np.append(ANGLES, ANGLES[0])

def poly_xy(radii):
    rc = np.append(radii, radii[0])
    px, py = p2xy(ang_c, rc)
    return np.column_stack([px, py])

radar_patch = MplPolygon(poly_xy(init_r), closed=True,
                          color=C['fill'], alpha=0.20, zorder=4)
ax.add_patch(radar_patch)
radar_line, = ax.plot([], [], color=C['stroke'], linewidth=2.2,
                       zorder=5, solid_joinstyle='round')
vx0,vy0 = p2xy(ANGLES, init_r)
radar_dots = ax.scatter(vx0, vy0, color=C['dot'], s=42, zorder=6,
                         edgecolors='white', linewidths=1.2)

delta_txts = []
for i,(ang,d,r) in enumerate(zip(ANGLES, init_d, init_r)):
    dvx,dvy = p2xy(ang, r+0.10)
    sign = '+' if d >= 0 else ''
    t = ax.text(dvx, dvy, f'{sign}{d:.2f}',
                color=C['delta'], fontsize=8.0, fontweight='bold',
                ha='center', va='center', zorder=7,
                path_effects=[pe.withStroke(linewidth=2.2, foreground=C['fig_bg'])])
    delta_txts.append(t)

year_txt = ax.text(0, -0.08, str(years[0]),
                    color=C['title'], fontsize=32, fontweight='bold',
                    ha='center', va='center', zorder=11,
                    path_effects=[pe.withStroke(linewidth=4, foreground=C['fig_bg'])])

# Timeline-Cursor
tl_cursor, = ax_tl.plot([yr2x(years[0])], [0.92], 'o',
                          color=C['tl_active'], markersize=12, zorder=4,
                          markeredgecolor='white', markeredgewidth=2.0)

# ── Update-Funktion ────────────────────────────────────────────────────────────
def update(frame):
    progress = frame / TOTAL_FRAMES   # 0.0 … <1.0
    deltas   = get_deltas_at(progress)
    radii    = np.array([delta_to_r(d) for d in deltas])
    rc       = np.append(radii, radii[0])
    px, py   = p2xy(ang_c, rc)

    radar_patch.set_xy(poly_xy(radii))
    radar_line.set_data(px, py)
    vx, vy = p2xy(ANGLES, radii)
    radar_dots.set_offsets(np.column_stack([vx, vy]))

    for i,(ang,d,r) in enumerate(zip(ANGLES, deltas, radii)):
        dvx,dvy = p2xy(ang, r+0.10)
        sign = '+' if d >= 0 else ''
        delta_txts[i].set_position((dvx, dvy))
        delta_txts[i].set_text(f'{sign}{d:.2f}')

    year_txt.set_text(str(int(round(get_year_at(progress)))))
    tl_cursor.set_xdata([yr2x(get_year_at(progress))])

    return (radar_patch, radar_line, radar_dots,
            *delta_txts, year_txt, tl_cursor)

# ── Rendern ────────────────────────────────────────────────────────────────────
print(f'Rendere {TOTAL_FRAMES} Frames @ {FPS} fps ({TOTAL_MS/1000:.0f} s)...')
anim   = animation.FuncAnimation(fig, update, frames=TOTAL_FRAMES,
                                   interval=1000/FPS, blit=True)
writer = animation.FFMpegWriter(fps=FPS, codec='libx264', bitrate=4000,
                                 extra_args=['-pix_fmt','yuv420p'])
anim.save(OUTPUT, writer=writer, dpi=130)
plt.close()
print(f'\n✓  {OUTPUT}')
