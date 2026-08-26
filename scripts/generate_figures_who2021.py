#!/usr/bin/env python3
"""Generate figures for the WHO 2021 schema-variant report.

Three figures, all driven from the pipeline outputs (data/output_who2021/):
  fig1_who2021_mfs.png        — 7 trapezoidal severity MFs (threshold universe)
  fig2_reclassification.png   — heatmap: deployed 6-grade label x WHO 2021 label
  fig3_distance_accuracy.png  — boundary-zone accuracy vs distance to WHO 2021 boundaries
Also emits SVG variants for each (editable).
"""
import json, sys
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import skfuzzy as fuzz

PROJECT = Path('/opt/data/fuzzy-audiogram')
OUT = PROJECT / 'data' / 'output_who2021'
FIG = PROJECT / 'data' / 'output_who2021' / 'figures'
FIG.mkdir(parents=True, exist_ok=True)

# Distinct colour palette (classic 10-colour set)
PALETTE = ['#e6194B', '#3cb44b', '#ffe119', '#4363d8', '#f58231',
           '#911eb4', '#42d4f4', '#f032e6', '#bfef45', '#800000']
CATS = ['normal', 'mild', 'moderate', 'moderately_severe', 'severe', 'profound', 'complete']
HUMAN = ['Normal', 'Mild', 'Moderate', 'Moderately Severe', 'Severe', 'Profound', 'Complete']

params = json.load(open(OUT / 'params_who2021.json'))

# ---- Fig 1: membership functions ----
universe = np.arange(0, 121, 1)
fig, ax = plt.subplots(figsize=(10, 5.5), dpi=300)
for i, cat in enumerate(CATS):
    mf = fuzz.trapmf(universe, params[cat])
    ax.plot(universe, mf, color=PALETTE[i], linewidth=2.2,
            label=f'{HUMAN[i]}  [{params[cat][0]:.0f}–{params[cat][3]:.0f} dB]')
# WHO 2021 crisp boundaries as dashed vertical lines
for b, lab in [(20, '20'), (35, '35'), (50, '50'), (65, '65'), (80, '80'), (95, '95')]:
    ax.axvline(b, color='#999', linestyle=':', linewidth=1.0)
    ax.text(b, 1.02, lab, ha='center', va='bottom', fontsize=8, color='#666')
ax.set_xlabel('Hearing threshold (dB HL)')
ax.set_ylabel('Membership degree')
ax.set_title('WHO 2021 severity membership functions (training-optimised)')
ax.set_xlim(0, 120)
ax.set_ylim(0, 1.12)
ax.legend(loc='upper left', fontsize=8, framealpha=0.9)
ax.grid(alpha=0.25)
fig.tight_layout()
fig.savefig(FIG / 'fig1_who2021_mfs.png')
fig.savefig(FIG / 'fig1_who2021_mfs.svg')
plt.close(fig)
print('OK fig1_who2021_mfs')

# ---- Fig 2: reclassification heatmap ----
rec = pd.read_csv(OUT / 'reclassification_matrix.csv', index_col=0)
G6 = ['Normal', 'Mild', 'Moderate', 'Moderately Severe', 'Severe', 'Profound']
fig, ax = plt.subplots(figsize=(9, 6), dpi=300)
mat = rec.values.astype(int)
im = ax.imshow(mat, cmap='YlOrRd', aspect='auto')
ax.set_xticks(range(7)); ax.set_xticklabels(HUMAN, rotation=30, ha='right', fontsize=8)
ax.set_yticks(range(6)); ax.set_yticklabels(G6, fontsize=9)
ax.set_xlabel('WHO 2021 fuzzy label (7 grades)')
ax.set_ylabel('Deployed 6-grade fuzzy label')
ax.set_title('Same test ears: deployed 6-grade label vs WHO 2021 label')
for i in range(6):
    for j in range(7):
        v = mat[i, j]
        if v:
            ax.text(j, i, str(v), ha='center', va='center', fontsize=8,
                    color='#111' if v < 0.6 * mat.max() else 'white')
fig.colorbar(im, fraction=0.046, pad=0.04, label='ears')
fig.tight_layout()
fig.savefig(FIG / 'fig2_reclassification.png')
fig.savefig(FIG / 'fig2_reclassification.svg')
plt.close(fig)
print('OK fig2_reclassification')

# ---- Fig 3: distance-to-boundary accuracy ----
dist = pd.read_csv(OUT / 'distance_accuracy.csv')
fig, ax = plt.subplots(figsize=(8, 4.8), dpi=300)
ax.plot(dist['within_dB'], dist['accuracy_pct'], marker='o', color=PALETTE[3],
        linewidth=2.2, markersize=6)
for _, r in dist.iterrows():
    ax.annotate(f"{r['accuracy_pct']:.0f}%\n(n={int(r['n'])})",
                (r['within_dB'], r['accuracy_pct']),
                textcoords='offset points', xytext=(0, 8), ha='center', fontsize=7)
ax.set_xlabel('Distance to nearest WHO 2021 boundary (dB)')
ax.set_ylabel('Agreement with WHO 2021 reference (%)')
ax.set_title('Boundary-zone agreement: WHO 2021 variant FIS')
ax.set_xticks(dist['within_dB'].astype(int))
ax.set_ylim(75, 100)
ax.grid(alpha=0.3)
fig.tight_layout()
fig.savefig(FIG / 'fig3_distance_accuracy.png')
fig.savefig(FIG / 'fig3_distance_accuracy.svg')
plt.close(fig)
print('OK fig3_distance_accuracy')
