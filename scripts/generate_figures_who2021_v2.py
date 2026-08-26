#!/usr/bin/env python3
"""Full WHO 2021 schema-variant figure set (report + manuscript).

Six figures, all driven from pipeline outputs (data/output_who2021/):
  fig1_who2021_mfs.png      — 7 trapezoidal severity MFs (threshold universe)
  fig2_reclassification.png — heatmap: deployed 6-grade label x WHO 2021 label
  fig3_distance_accuracy.png— boundary-zone agreement vs distance to boundary
  fig4_head_to_head.png     — WHO 2021 variant vs deployed 6-grade (same ears,
                              WHO 2021 reference): agreement metrics + MAE
  fig5_bland_altman.png     — Bland-Altman, FAI vs PTA-4 (WHO 2021 variant)
  fig6_confusion.png        — 7x7 confusion: variant label vs WHO 2021 crisp ref

Journal-spec: NO embedded titles (captions live in the documents).
Also emits SVG variants for each (editable).
"""
import json, pickle
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import skfuzzy as fuzz

PROJECT = Path('/opt/data/fuzzy-audiogram')
OUT = PROJECT / 'data' / 'output_who2021'
FIG = OUT / 'figures'
FIG.mkdir(parents=True, exist_ok=True)

PALETTE = ['#e6194B', '#3cb44b', '#ffe119', '#4363d8', '#f58231',
           '#911eb4', '#42d4f4', '#f032e6', '#bfef45', '#800000']
VARIANT_C = PALETTE[3]   # blue  -> WHO 2021 variant
DEPLOYED_C = PALETTE[4]  # orange-> deployed 6-grade

CATS = ['normal', 'mild', 'moderate', 'moderately_severe', 'severe', 'profound', 'complete']
HUMAN = ['Normal', 'Mild', 'Moderate', 'Moderately Severe', 'Severe', 'Profound', 'Complete']
G6 = ['Normal', 'Mild', 'Moderate', 'Moderately Severe', 'Severe', 'Profound']

params = json.load(open(OUT / 'params_who2021.json'))
metrics = json.load(open(OUT / 'metrics_who2021.json'))
with open(OUT / 'predictions_who2021.pkl', 'rb') as f:
    preds = pickle.load(f)

# ================= Fig 1: membership functions =================
universe = np.arange(0, 121, 1)
fig, ax = plt.subplots(figsize=(10, 5.5), dpi=300)
for i, cat in enumerate(CATS):
    mf = fuzz.trapmf(universe, params[cat])
    ax.plot(universe, mf, color=PALETTE[i], linewidth=2.2,
            label=f'{HUMAN[i]}  [{params[cat][0]:.0f}–{params[cat][3]:.0f} dB]')
for b, lab in [(20, '20'), (35, '35'), (50, '50'), (65, '65'), (80, '80'), (95, '95')]:
    ax.axvline(b, color='#999', linestyle=':', linewidth=1.0)
    ax.text(b, 1.02, lab, ha='center', va='bottom', fontsize=8, color='#666')
ax.set_xlabel('Hearing threshold (dB HL)')
ax.set_ylabel('Membership degree')
ax.set_xlim(0, 120)
ax.set_ylim(0, 1.12)
ax.legend(loc='upper left', fontsize=8, framealpha=0.9)
ax.grid(alpha=0.25)
fig.tight_layout()
fig.savefig(FIG / 'fig1_who2021_mfs.png')
fig.savefig(FIG / 'fig1_who2021_mfs.svg')
plt.close(fig)
print('OK fig1_who2021_mfs')

# ================= Fig 2: reclassification heatmap =================
rec = pd.read_csv(OUT / 'reclassification_matrix.csv', index_col=0)
fig, ax = plt.subplots(figsize=(9, 6), dpi=300)
mat = rec.values.astype(int)
im = ax.imshow(mat, cmap='YlOrRd', aspect='auto')
ax.set_xticks(range(7)); ax.set_xticklabels(HUMAN, rotation=30, ha='right', fontsize=8)
ax.set_yticks(range(6)); ax.set_yticklabels(G6, fontsize=9)
ax.set_xlabel('WHO 2021 variant label (7 grades)')
ax.set_ylabel('Deployed 6-grade label')
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

# ================= Fig 3: distance-to-boundary agreement =================
dist = pd.read_csv(OUT / 'distance_accuracy.csv')
fig, ax = plt.subplots(figsize=(8, 4.8), dpi=300)
ax.plot(dist['within_dB'], dist['accuracy_pct'], marker='o', color=VARIANT_C,
        linewidth=2.2, markersize=6)
for _, r in dist.iterrows():
    ax.annotate(f"{r['accuracy_pct']:.0f}%\n(n={int(r['n'])})",
                (r['within_dB'], r['accuracy_pct']),
                textcoords='offset points', xytext=(0, 8), ha='center', fontsize=7)
ax.set_xlabel('Distance to nearest WHO 2021 boundary (dB)')
ax.set_ylabel('Agreement with WHO 2021 reference (%)')
ax.set_xticks(dist['within_dB'].astype(int))
ax.set_ylim(75, 100)
ax.grid(alpha=0.3)
fig.tight_layout()
fig.savefig(FIG / 'fig3_distance_accuracy.png')
fig.savefig(FIG / 'fig3_distance_accuracy.svg')
plt.close(fig)
print('OK fig3_distance_accuracy')

# ================= Fig 4: head-to-head (variant vs deployed) =================
w, d = metrics['who2021'], metrics['deployed_6grade']
agree_metrics = ['Weighted κ (×100)', 'Overall agreement', 'Borderline (±5 dB)', 'Clear cases']
var_agree = [w['kappa'] * 100, w['overall'] * 100, w['borderline'] * 100, w['clear'] * 100]
dep_agree = [d['kappa'] * 100, d['overall'] * 100, d['borderline'] * 100, d['clear'] * 100]

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.8), dpi=300,
                               gridspec_kw={'width_ratios': [2.6, 1]})
x = np.arange(len(agree_metrics))
wdt = 0.36
ax1.bar(x - wdt / 2, var_agree, wdt, color=VARIANT_C, label='WHO 2021 variant (7 grades)')
ax1.bar(x + wdt / 2, dep_agree, wdt, color=DEPLOYED_C, label='Deployed 6-grade system')
for xi, vv, dv in zip(x, var_agree, dep_agree):
    ax1.text(xi - wdt / 2, vv + 0.8, f'{vv:.1f}', ha='center', fontsize=7)
    ax1.text(xi + wdt / 2, dv + 0.8, f'{dv:.1f}', ha='center', fontsize=7)
ax1.set_xticks(x); ax1.set_xticklabels(agree_metrics, fontsize=8)
ax1.set_ylabel('Percent / score (κ × 100)')
ax1.set_ylim(0, 108)
ax1.legend(fontsize=8, loc='lower right')
ax1.grid(axis='y', alpha=0.3)

ax2.bar([0], w['mae'], 0.5, color=VARIANT_C, label='Variant')
ax2.bar([1], d['mae'], 0.5, color=DEPLOYED_C, label='Deployed')
ax2.text(0, w['mae'] + 0.06, f"{w['mae']:.2f}", ha='center', fontsize=9)
ax2.text(1, d['mae'] + 0.06, f"{d['mae']:.2f}", ha='center', fontsize=9)
ax2.set_xticks([0, 1]); ax2.set_xticklabels(['Variant', 'Deployed'], fontsize=8)
ax2.set_ylabel('MAE (dB)')
ax2.set_ylim(0, 6.2)
ax2.legend(fontsize=8, loc='upper right')
ax2.grid(axis='y', alpha=0.3)
fig.tight_layout()
fig.savefig(FIG / 'fig4_head_to_head.png')
fig.savefig(FIG / 'fig4_head_to_head.svg')
plt.close(fig)
print('OK fig4_head_to_head')

# ================= Fig 5: Bland-Altman (variant FAI vs PTA-4) =================
fai = preds['fai_who']
pta = preds['pta']
y_true = preds['y_true']
mean_xy = (fai + pta) / 2
diff = fai - pta
bias = diff.mean()
sd = diff.std()
lo, hi = bias - 1.96 * sd, bias + 1.96 * sd

fig, ax = plt.subplots(figsize=(9, 5.5), dpi=300)
for g in range(7):
    m = y_true == g
    ax.scatter(mean_xy[m], diff[m], s=9, alpha=0.45, color=PALETTE[g],
               label=HUMAN[g], edgecolors='none')
ax.axhline(bias, color=VARIANT_C, linewidth=1.8, label=f'Bias {bias:+.1f} dB')
ax.axhline(lo, color='#888', linestyle='--', linewidth=1.2)
ax.axhline(hi, color='#888', linestyle='--', linewidth=1.2)
ax.text(mean_xy.max() * 0.97, lo - 1.2, f'LoA {lo:+.1f}', ha='right', fontsize=8, color='#555')
ax.text(mean_xy.max() * 0.97, hi + 0.8, f'LoA {hi:+.1f}', ha='right', fontsize=8, color='#555')
ax.set_xlabel('Mean of FAI and PTA-4 (dB)')
ax.set_ylabel('FAI − PTA-4 (dB)')
ax.set_ylim(-26, 26)
ax.legend(fontsize=7, loc='upper left', ncol=2, markerscale=1.6)
ax.grid(alpha=0.25)
fig.tight_layout()
fig.savefig(FIG / 'fig5_bland_altman.png')
fig.savefig(FIG / 'fig5_bland_altman.svg')
plt.close(fig)
print(f'OK fig5_bland_altman (bias {bias:+.2f}, LoA {lo:+.1f}..{hi:+.1f})')

# ================= Fig 6: confusion matrix (variant vs crisp reference) =================
y_who = preds['y_who']
cm = np.zeros((7, 7), dtype=int)
for t, p in zip(y_true, y_who):
    cm[t, p] += 1

fig, ax = plt.subplots(figsize=(9, 7), dpi=300)
im = ax.imshow(cm, cmap='YlGnBu', aspect='auto')
ax.set_xticks(range(7)); ax.set_xticklabels(HUMAN, rotation=30, ha='right', fontsize=8)
ax.set_yticks(range(7)); ax.set_yticklabels(HUMAN, fontsize=8)
ax.set_xlabel('WHO 2021 variant label')
ax.set_ylabel('WHO 2021 crisp reference (PTA-4)')
for i in range(7):
    for j in range(7):
        v = cm[i, j]
        if v:
            ax.text(j, i, str(v), ha='center', va='center', fontsize=8,
                    color='#111' if v < 0.55 * cm.max() else 'white')
fig.colorbar(im, fraction=0.046, pad=0.04, label='ears')
fig.tight_layout()
fig.savefig(FIG / 'fig6_confusion.png')
fig.savefig(FIG / 'fig6_confusion.svg')
plt.close(fig)
print('OK fig6_confusion')
print('All figures written to', FIG)
