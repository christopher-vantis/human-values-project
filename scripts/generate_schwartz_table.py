import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np
from pathlib import Path

DATA_PATH = Path(__file__).parent.parent / "data/merged_datasets/macro_schwartz_analysis_data.csv"
OUT_PATH  = Path(__file__).parent.parent / "visualizations/schwartz_delta_table.png"
OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

VALUE_KEYS = ['SD', 'ST', 'HE', 'AC', 'PO', 'SE', 'CO', 'TR', 'BE', 'UN']
VALUE_LABELS = {
    'SD': 'Self-\nDirection', 'ST': 'Stimu-\nlation', 'HE': 'Hedo-\nnism',
    'AC': 'Achieve-\nment',   'PO': 'Power',           'SE': 'Security',
    'CO': 'Confor-\nmity',    'TR': 'Tradition',        'BE': 'Benevo-\nlence',
    'UN': 'Universal-\nism',
}
COUNTRY_NAMES = {
    'BE': 'Belgium',     'CH': 'Switzerland', 'DE': 'Germany',
    'ES': 'Spain',       'FI': 'Finland',     'FR': 'France',
    'HU': 'Hungary',     'IE': 'Ireland',     'NL': 'Netherlands',
    'NO': 'Norway',      'PL': 'Poland',      'PT': 'Portugal',
    'SE': 'Sweden',      'SI': 'Slovenia',
}
# Higher-order dimension color per value column
DIM_COLORS = {
    'SD': '#3584e4', 'ST': '#3584e4', 'HE': '#3584e4',
    'UN': '#9141ac', 'BE': '#9141ac',
    'TR': '#2ec27e', 'CO': '#2ec27e', 'SE': '#2ec27e',
    'PO': '#e01b24', 'AC': '#e01b24',
}

df = pd.read_csv(DATA_PATH)

df['v_SD'] = df['ipcrtiv_mean']
df['v_ST'] = df['ipadvnt_mean']
df['v_HE'] = df['ipgdtim_mean']
df['v_AC'] = df['ipsuces_mean']
df['v_PO'] = df['ipshabt_mean']
df['v_SE'] = df['ipstrgv_mean']
df['v_CO'] = df[['ipbhprp_mean', 'ipfrule_mean', 'ipmodst_mean']].mean(axis=1)
df['v_TR'] = df['iprspot_mean']
df['v_BE'] = df[['iphlppl_mean', 'iplylfr_mean']].mean(axis=1)
df['v_UN'] = df[['ipeqopt_mean', 'ipudrst_mean']].mean(axis=1)

v_cols   = [f'v_{k}' for k in VALUE_KEYS]
row_mean = df[v_cols].mean(axis=1)
for k in VALUE_KEYS:
    df[f'd_{k}'] = df[f'v_{k}'] - row_mean

d_cols = [f'd_{k}' for k in VALUE_KEYS]
result = df.groupby('cntry')[d_cols].mean().round(2)
result.columns = VALUE_KEYS
result.index = [COUNTRY_NAMES[c] for c in result.index]
result = result.sort_index()

# ── Figure ────────────────────────────────────────────────────────────────────
n_rows, n_cols = result.shape
fig, ax = plt.subplots(figsize=(13, 7))
ax.set_axis_off()
fig.patch.set_facecolor('#f4f6fb')

col_labels = [VALUE_LABELS[k] for k in VALUE_KEYS]

tbl = ax.table(
    cellText=result.values,
    rowLabels=result.index.tolist(),
    colLabels=col_labels,
    loc='center',
    cellLoc='center',
)
tbl.auto_set_font_size(False)
tbl.set_fontsize(9.5)
tbl.scale(1.18, 2.1)

# Color each data cell by value using a diverging colormap
vmax = max(abs(result.values.min()), abs(result.values.max()))
norm = mcolors.TwoSlopeNorm(vmin=-vmax, vcenter=0, vmax=vmax)
cmap = plt.get_cmap('RdYlGn')

for (row, col), cell in tbl.get_celld().items():
    cell.set_edgecolor('#cdd5e0')
    cell.set_linewidth(0.6)

    if row == 0:
        # Column header: tint by higher-order dimension
        key = VALUE_KEYS[col - 1] if col > 0 else None
        bg = DIM_COLORS.get(key, '#dce2ef') if key else '#dce2ef'
        r, g, b, _ = mcolors.to_rgba(bg)
        cell.set_facecolor((r, g, b, 0.25))
        cell.set_text_props(fontweight='bold', fontsize=8.5, color='#0d1b2a')
        cell.set_height(cell.get_height() * 1.3)
    elif col == -1:
        # Row label
        cell.set_facecolor('#e4e9f2')
        cell.set_text_props(fontweight='600', color='#0d1b2a', ha='right')
    else:
        val = result.iloc[row - 1, col - 1]
        rgba = list(cmap(norm(val)))
        rgba[3] = 0.55  # soften alpha
        cell.set_facecolor(rgba)
        cell.set_text_props(color='#0d1b2a')

# Title
fig.text(
    0.5, 0.97,
    'Schwartz Values — Δ-Scores by Country (ESS Rounds 1–11, 2002–2023 average)',
    ha='center', va='top',
    fontsize=11, fontweight='bold', color='#0d1b2a',
)
fig.text(
    0.5, 0.935,
    'Δ = value mean − country mean across all 10 values  ·  positive = above-average priority',
    ha='center', va='top',
    fontsize=8.5, color='#4a5a70',
)

# Dimension legend
dim_items = [
    ('Openness to Change (SD · ST · HE)', '#3584e4'),
    ('Self-Transcendence (UN · BE)',       '#9141ac'),
    ('Conservation (TR · CO · SE)',        '#2ec27e'),
    ('Self-Enhancement (PO · AC)',         '#e01b24'),
]
x = 0.13
for label, color in dim_items:
    fig.text(x, 0.04, '■ ' + label, fontsize=8, color=color,
             va='bottom', fontweight='600')
    x += 0.22

plt.tight_layout(rect=[0, 0.06, 1, 0.93])
plt.savefig(OUT_PATH, dpi=160, bbox_inches='tight', facecolor=fig.get_facecolor())
print(f'Saved: {OUT_PATH}')
