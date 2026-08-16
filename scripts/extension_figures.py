#!/usr/bin/env python3
"""Figures for the pipeline-extension results.

- fig_ext_external.png      external validation (P_AUX): full / children / elders
- fig_ext_comparators.png   comparator suite side-by-side (kappa, overall, borderline, clear)
- fig_ext_sensitivity.png   overlap sweep + seed sweep (kappa/overall lines)
- fig_ext_decades.png       age-decade subgroups on participant test
"""
import sys, json, warnings
from pathlib import Path
warnings.filterwarnings('ignore')
PROJECT = Path('/opt/data/fuzzy-audiogram')
sys.path.insert(0, str(PROJECT))
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

OUT = PROJECT / 'data' / 'output_extension'
FIG = PROJECT / 'figures_extension'
FIG.mkdir(parents=True, exist_ok=True)
plt.rcParams.update({'font.family': 'serif', 'font.size': 11, 'figure.dpi': 300})


def save(fig, name):
    fig.savefig(FIG / name, dpi=300, bbox_inches='tight')
    plt.close(fig)
    print('saved', name)


# ---- external validation ----
ext = json.loads((OUT / 'external_validation.json').read_text())
labels = ['Full external\n(6-19 + >=70)', 'Children 6-19', 'Adults >=70']
mm = [ext['full'], ext['children_6_19'], ext['adults_70plus']]
kappa = [m['kappa'] for m in mm]
overall = [m['overall'] * 100 for m in mm]
fig, axes = plt.subplots(1, 2, figsize=(12, 5))
axes[0].bar(labels, kappa, color=['#2c3e50', '#2ecc71', '#e67e22'], width=0.55)
axes[0].set_ylabel('Weighted κ (quadratic)')
axes[0].set_title('External validation — P_AUX 2017-2020 (unseen)')
for x, y in zip(range(3), kappa):
    axes[0].annotate(f'{y:.3f}', (x, y), textcoords='offset points', xytext=(0, 6), ha='center', fontsize=10)
axes[0].set_ylim(0.7, 1.0); axes[0].grid(True, alpha=0.2)
axes[1].bar(labels, overall, color=['#2c3e50', '#2ecc71', '#e67e22'], width=0.55)
axes[1].set_ylabel('Overall agreement (%)')
axes[1].set_title(f"External set: n={ext['clean_ears']:,} ears")
for x, y in zip(range(3), overall):
    axes[1].annotate(f'{y:.1f}%', (x, y), textcoords='offset points', xytext=(0, 6), ha='center', fontsize=10)
axes[1].set_ylim(70, 102); axes[1].grid(True, alpha=0.2)
plt.tight_layout()
save(fig, 'fig_ext_external.png')

# ---- comparators ----
cmp = json.loads((OUT / 'comparators.json').read_text())
names = list(cmp.keys())
short = ['FAI\n(fuzzy)', 'Multinom.\nLR', 'kNN-15', 'MLP', 'XGBoost\n(clf)', 'Random\nForest']
ck = [cmp[n]['kappa'] for n in names]
co = [cmp[n]['overall'] * 100 for n in names]
cb = [cmp[n]['borderline'] * 100 if cmp[n]['borderline'] is not None else np.nan for n in names]
cc = [cmp[n]['clear'] * 100 if cmp[n]['clear'] is not None else np.nan for n in names]
x = np.arange(len(names))
fig, ax = plt.subplots(figsize=(10, 5.5))
w = 0.19
ax.bar(x - 1.5 * w, [v * 100 for v in ck], w, label='Weighted κ (×100)', color='#2c3e50')
ax.bar(x - 0.5 * w, co, w, label='Overall %', color='#2ecc71')
ax.bar(x + 0.5 * w, cb, w, label='Borderline %', color='#f1c40f')
ax.bar(x + 1.5 * w, cc, w, label='Clear %', color='#3498db')
ax.set_xticks(x); ax.set_xticklabels(short, fontsize=9)
ax.set_ylabel('Score')
ax.set_title('FAI vs multiclass ML comparators (participant test set, n=3,912)')
ax.legend(loc='lower right', fontsize=9); ax.grid(True, alpha=0.2)
plt.tight_layout()
save(fig, 'fig_ext_comparators.png')

# ---- sensitivity (only if available) ----
sens = None
try:
    sens = json.loads((OUT / 'sensitivity.json').read_text())
except Exception:
    print('sensitivity.json not ready yet — skipping sensitivity/decade figures')

if sens is not None:
    ov = sens['overlap_sweep']
    seeds = sens['seed_sweep']
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    ovx = [float(k) for k in ov.keys()]
    axes[0].plot(ovx, [ov[k]['kappa'] * 100 for k in ov], 'o-', color='#2c3e50', lw=2, label='κ (×100)')
    axes[0].plot(ovx, [ov[k]['overall'] * 100 for k in ov], 's-', color='#2ecc71', lw=2, label='Overall %')
    axes[0].set_xlabel('MF overlap (dB)'); axes[0].set_ylabel('Score')
    axes[0].set_title('Overlap-width sensitivity (seed 42)')
    axes[0].set_xticks(ovx); axes[0].legend(); axes[0].grid(True, alpha=0.2)
    sx = [int(k) for k in seeds.keys()]
    axes[1].plot(sx, [seeds[k]['kappa'] * 100 for k in seeds], 'o-', color='#2c3e50', lw=2, label='κ (×100)')
    axes[1].plot(sx, [seeds[k]['overall'] * 100 for k in seeds], 's-', color='#2ecc71', lw=2, label='Overall %')
    axes[1].set_xlabel('Split seed'); axes[1].set_ylabel('Score')
    axes[1].set_title('Split-seed sensitivity (overlap 2 dB)')
    axes[1].set_xticks(sx); axes[1].legend(); axes[1].grid(True, alpha=0.2)
    plt.tight_layout()
    save(fig, 'fig_ext_sensitivity.png')

    # ---- age decades ----
    dec = sens.get('age_decades', {})
    if dec:
        dx = sorted(dec)
        fig, ax = plt.subplots(figsize=(9, 5))
        ax.bar(dx, [dec[d]['kappa'] for d in dx], color='#2c3e50', width=0.6)
        ax.set_xlabel('Age decade'); ax.set_ylabel('Weighted κ')
        ax.set_title('Age-decade subgroups (participant test set)')
        for x_, d in zip(range(len(dx)), dx):
            ax.annotate(f"{dec[d]['kappa']:.2f}\n(n={dec[d]['n']:,})", (x_, dec[d]['kappa']),
                        textcoords='offset points', xytext=(0, 6), ha='center', fontsize=8)
        ax.set_xticks(range(len(dx))); ax.set_xticklabels(dx)
        ax.grid(True, alpha=0.2)
        plt.tight_layout()
        save(fig, 'fig_ext_decades.png')

print('done')
