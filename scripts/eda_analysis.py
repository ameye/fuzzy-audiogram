#!/usr/bin/env python3
"""Comprehensive EDA for NHANES audiometry data (P_AUX.xpt only, no demographics)."""
import sys, os, json
sys.path.insert(0, '/opt/data/fuzzy-audiogram')
os.environ['PATH'] = '/tmp/quarto-install/opt/quarto/bin:' + os.environ.get('PATH', '')

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pathlib import Path
from scipy import stats

from fuzzy_audiogram.data import load_nhanes, extract_audiometry

FIGS_DIR = Path('/opt/data/fuzzy-audiogram/figures')
OUT_DIR = Path('/opt/data/fuzzy-audiogram/data/output')
OUT_DIR.mkdir(exist_ok=True)

plt.rcParams.update({
    'font.family': 'serif', 'font.size': 11,
    'axes.labelsize': 12, 'axes.titlesize': 13,
    'legend.fontsize': 9, 'figure.dpi': 300,
})

print("Loading NHANES data...")
df = load_nhanes('/opt/data/P_AUX.xpt')
audio = extract_audiometry(df)
print(f"Loaded {len(audio)} participants")

# Column names from extract_audiometry:
# threshold_right_500, threshold_right_1000, ..., threshold_right_8000
# threshold_left_500, threshold_left_1000, ..., threshold_left_8000
SIDES = ['right', 'left']
FREQ_KEYS = ['500', '1000', '2000', '3000', '4000', '6000', '8000']
FREQ_LABELS = ['500 Hz', '1 kHz', '2 kHz', '3 kHz', '4 kHz', '6 kHz', '8 kHz']

def tc(side, freq):
    return f'threshold_{side}_{freq}'

# Compute PTA-4 (average of 500, 1000, 2000, 4000) with NHANES code filtering
NHANES_INVALID = {666, 777, 888, 999}  # codes for no response/refused/not obtained

def clean_threshold(val):
    """Replace NHANES special codes with NaN."""
    if pd.isna(val) or val in NHANES_INVALID or val < -10 or val > 120:
        return np.nan
    return val

for side in SIDES:
    for f in FREQ_KEYS:
        col = tc(side, f)
        audio[col] = audio[col].apply(clean_threshold)
    cols = [tc(side, f) for f in ['500', '1000', '2000', '4000']]
    audio[f'PTA_{side}'] = audio[cols].mean(axis=1, skipna=False)

def who_grade(pta):
    if pd.isna(pta): return np.nan
    if pta <= 25: return 0
    elif pta <= 40: return 1
    elif pta <= 55: return 2
    elif pta <= 70: return 3
    elif pta <= 90: return 4
    else: return 5

who_labels = {0:'Normal',1:'Mild',2:'Moderate',3:'Mod-Sev',4:'Severe',5:'Profound'}

# Ear-level data (melt)
ear_data = []
for side in SIDES:
    ear_label = side[0].upper()
    mask = audio[f'PTA_{side}'].notna()
    for idx in audio[mask].index:
        row = audio.loc[idx]
        thresh = [row[tc(side, f)] for f in FREQ_KEYS]
        if any(pd.isna(t) for t in thresh):
            continue
        ear_data.append({
            'ear': ear_label,
            'PTA': row[f'PTA_{side}'],
            'WHO_grade': who_grade(row[f'PTA_{side}']),
            **{FREQ_LABELS[i]: thresh[i] for i in range(7)}
        })
ears = pd.DataFrame(ear_data)
print(f"Ears with complete data: {len(ears)}")

# Summary stats
summary = {}
summary['n_participants'] = int(len(audio))
summary['n_ears_complete'] = int(len(ears))

# Threshold stats
for fname in FREQ_LABELS:
    vals = ears[fname]
    summary[f'threshold_{fname}_mean'] = round(float(vals.mean()), 1)
    summary[f'threshold_{fname}_std'] = round(float(vals.std()), 1)
    summary[f'threshold_{fname}_median'] = round(float(vals.median()), 1)

# PTA stats
pta_all = ears['PTA']
summary['pta_mean'] = round(float(pta_all.mean()), 1)
summary['pta_std'] = round(float(pta_all.std()), 1)
summary['pta_median'] = round(float(pta_all.median()), 1)

# WHO grade prevalence
for g in range(6):
    pct = (ears['WHO_grade'] == g).sum() / len(ears) * 100
    summary[f'who_grade_{who_labels[g]}_pct'] = round(float(pct), 1)

# Borderline
boundaries = [25, 40, 55, 70, 90]
def is_borderline(pta):
    if pd.isna(pta): return False
    return any(abs(pta - b) <= 5 for b in boundaries)
borderline = pta_all.apply(is_borderline)
summary['borderline_pct'] = round(float(borderline.mean() * 100), 1)

# Asymmetry (only where both ears available)
paired = audio[audio['PTA_right'].notna() & audio['PTA_left'].notna()]
asym = abs(paired['PTA_right'] - paired['PTA_left'])
summary['n_paired'] = int(len(paired))
summary['asymmetry_mean'] = round(float(asym.mean()), 1)
summary['asymmetry_median'] = round(float(asym.median()), 1)
summary['asymmetry_pct_gt_15dB'] = round(float((asym > 15).mean() * 100), 1)

# Correlation stats
right_cols = [tc('right', f) for f in FREQ_KEYS]
corr_data = audio[right_cols].dropna()
corr = corr_data.corr()
summary['corr_adjacent_mean'] = round(float(np.mean([corr.iloc[i,i+1] for i in range(6)])), 2)
summary['corr_distant'] = round(float(corr.iloc[0, 6]), 2)

with open(OUT_DIR / 'eda_summary.json', 'w') as f:
    json.dump(summary, f, indent=2)
print("\n=== EDA SUMMARY ===")
for k, v in summary.items():
    print(f"  {k}: {v}")

# ==============================
# FIGURE 1: Right ear threshold violin plot
# ==============================
print("\nFig EDA-1: Threshold distributions...")
fig, ax = plt.subplots(figsize=(10, 5))
data = [ears[ears['ear']=='R'][fname].values for fname in FREQ_LABELS]
parts = ax.violinplot(data, positions=range(1, 8), showmeans=True, showmedians=True)
colors = plt.cm.viridis(np.linspace(0.2, 0.8, 7))
for i, pc in enumerate(parts['bodies']):
    pc.set_facecolor(colors[i]); pc.set_alpha(0.7)
parts['cmeans'].set_color('red'); parts['cmedians'].set_color('darkblue')
ax.set_xticks(range(1, 8)); ax.set_xticklabels(FREQ_LABELS)
ax.set_xlabel('Frequency'); ax.set_ylabel('Threshold (dB HL)')
ax.set_title('Hearing Threshold Distributions by Frequency (Right Ear, NHANES)', fontsize=12, fontweight='bold')
ax.invert_yaxis(); ax.grid(True, alpha=0.2, axis='y')
plt.tight_layout()
plt.savefig(FIGS_DIR / 'fig_eda_threshold_dist.png', dpi=300, bbox_inches='tight')
plt.close()

# ==============================
# FIGURE 2: PTA-4 distribution with WHO bands
# ==============================
print("Fig EDA-2: PTA-4 distribution...")
fig, ax = plt.subplots(figsize=(10, 5))
band_colors = ['#2ecc71', '#f1c40f', '#e67e22', '#e74c3c', '#9b59b6', '#2c3e50']
band_labels = ['Normal (≤25)', 'Mild (26-40)', 'Moderate (41-55)',
               'Mod-Sev (56-70)', 'Severe (71-90)', 'Profound (>90)']
prev_b = 0
for i, (b, label) in enumerate(zip([25, 40, 55, 70, 90, 120], band_labels)):
    ax.axvspan(prev_b, b, alpha=0.1, color=band_colors[i])
    ax.text((prev_b+b)/2, ax.get_ylim()[1]*0.9, label, ha='center', fontsize=7, rotation=90)
    prev_b = b
ax.hist(pta_all, bins=60, color='gray', edgecolor='white', alpha=0.6)
ax.axvline(pta_all.mean(), color='#e74c3c', ls='--', lw=2, label=f'Mean={pta_all.mean():.1f}')
ax.axvline(pta_all.median(), color='#3498db', ls=':', lw=2, label=f'Median={pta_all.median():.1f}')
ax.set_xlabel('PTA-4 (dB HL)'); ax.set_ylabel('Count')
ax.set_title('PTA-4 Distribution with WHO Severity Bands', fontsize=12, fontweight='bold')
ax.legend(); ax.set_xlim(0, 120); ax.grid(True, alpha=0.2)
plt.tight_layout()
plt.savefig(FIGS_DIR / 'fig_eda_pta_dist.png', dpi=300, bbox_inches='tight')
plt.close()

# ==============================
# FIGURE 3: Correlation heatmap
# ==============================
print("Fig EDA-3: Correlation heatmap...")
fig, ax = plt.subplots(figsize=(8, 6))
im = ax.imshow(corr, cmap='RdYlBu_r', vmin=0.5, vmax=1.0)
for i in range(7):
    for j in range(7):
        val = corr.iloc[i, j]
        ax.text(j, i, f'{val:.2f}', ha='center', va='center', fontsize=9,
                color='white' if val > 0.85 else 'black', fontweight='bold')
ax.set_xticks(range(7)); ax.set_yticks(range(7))
ax.set_xticklabels(FREQ_LABELS, rotation=45); ax.set_yticklabels(FREQ_LABELS)
ax.set_title('Inter-Frequency Threshold Correlation (Right Ear)', fontsize=12, fontweight='bold')
cbar = fig.colorbar(im, ax=ax, shrink=0.7); cbar.set_label('Pearson r')
plt.tight_layout()
plt.savefig(FIGS_DIR / 'fig_eda_correlation.png', dpi=300, bbox_inches='tight')
plt.close()

# ==============================
# FIGURE 4: Configuration prevalence
# ==============================
print("Fig EDA-4: Configuration prevalence...")
def classify_config(row):
    try:
        low = (row[tc('right', '500')] + row[tc('right', '1000')]) / 2
        high = (row[tc('right', '4000')] + row[tc('right', '6000')]) / 2
        slope = high - low
        if slope < -5: return 'Rising'
        elif slope <= 12: return 'Flat'
        elif slope <= 28: return 'Gently Sloping'
        elif slope <= 45: return 'Steeply Sloping'
        else: return 'Precipitous'
    except: return np.nan

audio['config'] = audio.apply(classify_config, axis=1)
configs = audio['config'].dropna().value_counts()
config_order = ['Flat', 'Gently Sloping', 'Steeply Sloping', 'Precipitous', 'Rising']
config_colors = ['#2ecc71', '#3498db', '#e67e22', '#e74c3c', '#9b59b6']
counts = [configs.get(c, 0) for c in config_order]

fig, axes = plt.subplots(1, 2, figsize=(12, 5))
ax = axes[0]
bars = ax.bar(config_order, counts, color=config_colors, edgecolor='white')
y_max = max(counts)
for bar, count in zip(bars, counts):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + y_max*0.005,
            f'{count} ({count/len(audio)*100:.1f}%)', ha='center', fontsize=8.5, fontweight='bold')
ax.set_ylabel('Count'); ax.set_title('Audiogram Configuration Prevalence')
ax.tick_params(axis='x', rotation=30); ax.grid(True, alpha=0.2, axis='y')

ax = axes[1]
pcts = [c/len(audio)*100 for c in counts]
ax.pie(pcts, labels=config_order, colors=config_colors, autopct='%1.1f%%', startangle=90, textprops={'fontsize':9})
ax.set_title('Configuration Distribution')
plt.suptitle('Audiogram Configuration Classification (NHANES Right Ear)', fontsize=12, fontweight='bold')
plt.tight_layout()
plt.savefig(FIGS_DIR / 'fig_eda_config_dist.png', dpi=300, bbox_inches='tight')
plt.close()

# ==============================
# FIGURE 5: Asymmetry distribution
# ==============================
print("Fig EDA-5: Asymmetry distribution...")
fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
ax = axes[0]
asym_clean = asym[asym <= 60]
ax.hist(asym_clean, bins=40, color='#9b59b6', edgecolor='white', alpha=0.7)
ax.axvline(15, color='#e74c3c', ls='--', lw=2, label='Threshold (15 dB)')
ax.set_xlabel('|PTA Right − PTA Left| (dB)'); ax.set_ylabel('Count')
ax.set_title('Inter-Aural Asymmetry Distribution'); ax.legend(); ax.grid(True, alpha=0.2)

ax = axes[1]
sym = (asym <= 15).mean() * 100
mild_asym = ((asym > 15) & (asym <= 30)).mean() * 100
mod_asym = ((asym > 30) & (asym <= 45)).mean() * 100
sev_asym = (asym > 45).mean() * 100
ax.bar(['Symmetric\n(≤15 dB)', 'Mild\n(16-30 dB)', 'Moderate\n(31-45 dB)', 'Severe\n(>45 dB)'],
       [sym, mild_asym, mod_asym, sev_asym], color=['#2ecc71', '#f1c40f', '#e67e22', '#e74c3c'],
       edgecolor='white')
ax.set_ylabel('Prevalence (%)'); ax.set_title('Asymmetry Severity Categories')
ax.grid(True, alpha=0.2, axis='y')
plt.suptitle('Inter-Aural Asymmetry in NHANES Cohort', fontsize=12, fontweight='bold')
plt.tight_layout()
plt.savefig(FIGS_DIR / 'fig_eda_asymmetry.png', dpi=300, bbox_inches='tight')
plt.close()

# ==============================
# FIGURE 6: Missing data
# ==============================
print("Fig EDA-6: Missing data...")
fig, ax = plt.subplots(figsize=(10, 4))
cols_plot = [tc(s, f) for s in SIDES for f in FREQ_KEYS]
labels_plot = []
for s in ['R', 'L']:
    for f in ['500','1k','2k','3k','4k','6k','8k']:
        labels_plot.append(f'{f}{s}')
missing_pct = [audio[c].isna().mean() * 100 for c in cols_plot]
colors_plot = ['#3498db'] * 7 + ['#e74c3c'] * 7
bars = ax.bar(range(len(cols_plot)), missing_pct, color=colors_plot, edgecolor='white')
for bar, pct in zip(bars, missing_pct):
    if pct > 1:
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.3,
                f'{pct:.1f}%', ha='center', fontsize=7)
ax.set_xticks(range(len(cols_plot))); ax.set_xticklabels(labels_plot, fontsize=7)
ax.set_ylabel('Missing (%)'); ax.set_title('Missing Data by Frequency and Side')
ax.grid(True, alpha=0.2, axis='y')
from matplotlib.patches import Patch
ax.legend(handles=[Patch(color='#3498db', label='Right'), Patch(color='#e74c3c', label='Left')])
plt.tight_layout()
plt.savefig(FIGS_DIR / 'fig_eda_missingness.png', dpi=300, bbox_inches='tight')
plt.close()

# ==============================
# FIGURE 7: PTA-4 comparison both ears (boxplot)
# ==============================
print("Fig EDA-7: PTA by ear...")
fig, ax = plt.subplots(figsize=(7, 5))
bp_data = [audio['PTA_right'].dropna(), audio['PTA_left'].dropna()]
bp = ax.boxplot(bp_data, patch_artist=True)
ax.set_xticklabels(['Right', 'Left'])
for patch, color in zip(bp['boxes'], ['#3498db', '#e74c3c']):
    patch.set_facecolor(color); patch.set_alpha(0.6)
ax.set_ylabel('PTA-4 (dB HL)')
ax.set_title('PTA-4 Distribution by Ear')
ax.grid(True, alpha=0.2, axis='y')
plt.tight_layout()
plt.savefig(FIGS_DIR / 'fig_eda_pta_by_ear.png', dpi=300, bbox_inches='tight')
plt.close()

# ==============================
# Narrative
# ==============================
narrative = f"""# Comprehensive EDA: NHANES Audiometry 2017–2020

## Overview
- Participants: {summary['n_participants']}
- Ears with complete data: {summary['n_ears_complete']}
- Paired ears for asymmetry: {summary['n_paired']}

## Hearing Loss Prevalence
Normal (≤25 dB): {summary.get('who_grade_Normal_pct','N/A')}%
Mild (26-40 dB): {summary.get('who_grade_Mild_pct','N/A')}%
Moderate (41-55 dB): {summary.get('who_grade_Moderate_pct','N/A')}%
Mod-Sev (56-70 dB): {summary.get('who_grade_Mod-Sev_pct','N/A')}%
Severe (71-90 dB): {summary.get('who_grade_Severe_pct','N/A')}%
Profound (>90 dB): {summary.get('who_grade_Profound_pct','N/A')}%

Borderline (±5 dB): {summary.get('borderline_pct','N/A')}%

## Asymmetry
Mean: {summary.get('asymmetry_mean','N/A')} dB
>15 dB: {summary.get('asymmetry_pct_gt_15dB','N/A')}%

## Correlation
Adjacent frequencies (mean r): {summary.get('corr_adjacent_mean','N/A')}
Distant (500 Hz vs 8 kHz r): {summary.get('corr_distant','N/A')}
"""
with open(OUT_DIR / 'eda_narrative.md', 'w') as f:
    f.write(narrative)
print("\n✅ EDA complete. All figures and summary saved.")
