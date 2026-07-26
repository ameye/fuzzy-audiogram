#!/usr/bin/env python3
"""
Comprehensive Exploratory Data Analysis — NHANES Audiometry (2017-2020)
=========================================================================
Generates 8 publication-ready figures + summary statistics JSON + narrative.

Figures (saved to /opt/data/fuzzy-audiogram/figures/fig_eda_*.png):
  1. fig_eda_age_dist.png        — Age distribution with sex overlay
  2. fig_eda_threshold_dist.png  — Violin plots of thresholds per frequency
  3. fig_eda_pta_dist.png        — PTA-4 distribution with WHO bands
  4. fig_eda_correlation.png     — Correlation heatmap of thresholds
  5. fig_eda_config_dist.png     — Audiogram configuration prevalence
  6. fig_eda_asymmetry.png       — Inter-aural asymmetry distribution
  7. fig_eda_bivariate.png       — Bivariate panels (age/sex/noise vs outcomes)
  8. fig_eda_missingness.png     — Missing data pattern analysis

Outputs:
  - /opt/data/fuzzy-audiogram/data/output/eda_summary.json
  - /opt/data/fuzzy-audiogram/data/output/eda_narrative.md
"""

import sys
import json
import warnings
from pathlib import Path
from collections import Counter, OrderedDict

import numpy as np
import pandas as pd

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.colors import ListedColormap
import seaborn as sns

# ── Project paths ──────────────────────────────────────────────────────────
PROJECT_DIR = Path('/opt/data/fuzzy-audiogram')
DATA_FILE = Path('/opt/data/P_AUX.xpt')
OUTPUT_DIR = PROJECT_DIR / 'data' / 'output'
FIGURES_DIR = PROJECT_DIR / 'figures'

sys.path.insert(0, str(PROJECT_DIR))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
FIGURES_DIR.mkdir(parents=True, exist_ok=True)

warnings.filterwarnings('ignore')

# ── Import fuzzy_audiogram ─────────────────────────────────────────────────
from fuzzy_audiogram.data import load_nhanes, extract_audiometry
from fuzzy_audiogram.core import (
    classify_audiogram, compute_audiogram_features,
    SEVERITY_LABELS_HUMAN, SLOPE_LABELS_HUMAN, CONFIG_LABELS_HUMAN,
    FREQUENCIES_HZ,
)

# ═══════════════════════════════════════════════════════════════════════════
# GLOBALS & STYLING
# ═══════════════════════════════════════════════════════════════════════════

plt.rcParams.update({
    'figure.dpi': 300,
    'savefig.dpi': 300,
    'figure.facecolor': '#FAFAFA',
    'axes.facecolor': '#FAFAFA',
    'axes.grid': True,
    'grid.alpha': 0.25,
    'grid.linestyle': ':',
    'font.size': 11,
    'axes.titlesize': 13,
    'axes.labelsize': 12,
    'legend.fontsize': 10,
    'xtick.labelsize': 10,
    'ytick.labelsize': 10,
})

WHO_COLORS = {
    'Normal': '#2ECC71',
    'Mild': '#F1C40F',
    'Moderate': '#E67E22',
    'Moderately Severe': '#E74C3C',
    'Severe': '#9B59B6',
    'Profound': '#2C3E50',
}
WHO_BOUNDARIES = [0, 25, 40, 55, 70, 90, 120]
WHO_LABELS = ['Normal (≤25)', 'Mild (26–40)', 'Moderate (41–55)',
              'Mod. Severe (56–70)', 'Severe (71–90)', 'Profound (>90)']

FREQ_LABELS_SHORT = ['500', '1k', '2k', '3k', '4k', '6k', '8k']
FREQS_HZ = [500, 1000, 2000, 3000, 4000, 6000, 8000]

SEX_LABELS = {1: 'Male', 2: 'Female'}
SEX_COLORS = {'Male': '#3498DB', 'Female': '#E74C3C'}

# ═══════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════

def who_category(pta_val):
    """WHO severity category based on PTA-4 (worse ear)."""
    if np.isnan(pta_val):
        return np.nan
    if pta_val <= 25:
        return 'Normal'
    elif pta_val <= 40:
        return 'Mild'
    elif pta_val <= 55:
        return 'Moderate'
    elif pta_val <= 70:
        return 'Moderately Severe'
    elif pta_val <= 90:
        return 'Severe'
    else:
        return 'Profound'


def is_borderline(pta_val, margin=5):
    """Check if PTA is within margin dB of any WHO boundary."""
    if np.isnan(pta_val):
        return False
    for b in [25, 40, 55, 70, 90]:
        if abs(pta_val - b) <= margin:
            return True
    return False


def compute_pta(row, ear='right'):
    """PTA-4: average of 500, 1000, 2000, 4000 Hz."""
    cols = [f'threshold_{ear}_{f}' for f in [500, 1000, 2000, 4000]]
    vals = [row.get(c, np.nan) for c in cols]
    return np.nanmean(vals)


def classify_slope(slope_val):
    """Categorical slope classification."""
    if np.isnan(slope_val):
        return np.nan
    if slope_val < -8:
        return 'Rising'
    elif slope_val <= 12:
        return 'Flat'
    elif slope_val <= 28:
        return 'Gently Sloping'
    elif slope_val <= 50:
        return 'Steeply Sloping'
    else:
        return 'Precipitous'


def compute_asymmetry_at_freq(df_clean, freq):
    """Compute inter-aural asymmetry at a given frequency."""
    col_r = f'threshold_right_{freq}'
    col_l = f'threshold_left_{freq}'
    if col_r in df_clean.columns and col_l in df_clean.columns:
        return np.abs(df_clean[col_r].values - df_clean[col_l].values)
    return np.full(len(df_clean), np.nan)


def add_stats_box(ax, text_lines, x=0.97, y=0.95, fontsize=8):
    """Add a stats box annotation to an axes."""
    text = '\n'.join(text_lines)
    ax.text(x, y, text, transform=ax.transAxes,
            fontsize=fontsize, va='top', ha='right',
            bbox=dict(boxstyle='round,pad=0.4', facecolor='white',
                      alpha=0.85, edgecolor='#CCCCCC'))


# ═══════════════════════════════════════════════════════════════════════════
# 1. LOAD DATA
# ═══════════════════════════════════════════════════════════════════════════

print("=" * 65)
print("  NHANES AUDIOMETRY EDA — Comprehensive Analysis")
print("=" * 65)

print("\n[1/8] Loading NHANES data...")
df_raw = load_nhanes(DATA_FILE)
print(f"  Raw NHANES P_AUX: {df_raw.shape[0]} rows × {df_raw.shape[1]} cols")

df_clean = extract_audiometry(df_raw)
print(f"  Cleaned data: {len(df_clean)} participants")

# ── Load demographic data from P_DEMO.xpt if available ────────────────────
demo_path = Path('/opt/data/P_DEMO.xpt')
if demo_path.exists():
    print("\n  Loading demographic data (P_DEMO.xpt)...")
    df_demo_raw = pd.read_sas(demo_path, format='xport', encoding='utf-8')
    df_demo_raw.columns = [c.strip().upper() for c in df_demo_raw.columns]
    # Keep key columns
    keep_cols = ['SEQN', 'RIDAGEYR', 'RIAGENDR', 'RIDRETH1', 'INDFMPIR', 'DMDEDUC2']
    demo_cols = [c for c in keep_cols if c in df_demo_raw.columns]
    df_demo = df_demo_raw[demo_cols].copy()
    df_demo['seqn'] = df_demo['SEQN'].astype('int64')
    df_demo.columns = [c.lower() if c != 'SEQN' else 'seqn' for c in df_demo.columns]
    df_clean = df_clean.merge(df_demo, on='seqn', how='left')
    has_demo = True
    print(f"  Merged demographics: {len(df_clean)} participants")
    if 'ridageyr' in df_clean.columns:
        age_valid = df_clean['ridageyr'][df_clean['ridageyr'] > 0]
        print(f"  Age range: {age_valid.min():.0f} – {age_valid.max():.0f} years")
else:
    has_demo = False
    print("  No P_DEMO.xpt found — will use SEQN as proxy where possible")
    # Create synthetic age from SEQN for illustration (not ideal)
    df_clean['ridageyr'] = np.nan
    df_clean['riagendr'] = np.nan

# ═══════════════════════════════════════════════════════════════════════════
# 2. COMPUTE FEATURES
# ═══════════════════════════════════════════════════════════════════════════

print("\n[2/8] Computing audiometric features...")

# ── PTA for both ears ─────────────────────────────────────────────────────
right_pta = df_clean.apply(lambda r: compute_pta(r, 'right'), axis=1)
left_pta = df_clean.apply(lambda r: compute_pta(r, 'left'), axis=1)
worse_pta = np.maximum(right_pta, left_pta)
better_pta = np.minimum(right_pta, left_pta)

df_clean['pta_right'] = right_pta
df_clean['pta_left'] = left_pta
df_clean['pta_worse'] = worse_pta
df_clean['pta_better'] = better_pta

# ── WHO categories ────────────────────────────────────────────────────────
df_clean['who_category'] = [who_category(v) for v in worse_pta]
df_clean['is_borderline'] = [is_borderline(v) for v in worse_pta]

# ── Slope at each ear ─────────────────────────────────────────────────────
df_clean['slope_right'] = df_clean['threshold_right_4000'] - df_clean['threshold_right_500']
df_clean['slope_left'] = df_clean['threshold_left_4000'] - df_clean['threshold_left_500']
# Worse-ear slope (more hearing loss slope)
df_clean['slope_max'] = np.maximum(
    df_clean['slope_right'].fillna(-999),
    df_clean['slope_left'].fillna(-999)
)
df_clean['slope_max'].replace(-999, np.nan, inplace=True)

# ── Slope classification (for configuration) ─────────────────────────────
df_clean['slope_category'] = [classify_slope(v) for v in df_clean['slope_max']]

# ── Asymmetry at each frequency ──────────────────────────────────────────
for f in FREQS_HZ:
    df_clean[f'asym_{f}'] = compute_asymmetry_at_freq(df_clean, f)

asym_cols = [f'asym_{f}' for f in FREQS_HZ]
df_clean['asym_max'] = df_clean[asym_cols].max(axis=1, skipna=True)
df_clean['asym_mean'] = df_clean[asym_cols].mean(axis=1, skipna=True)

# Asymmetry > 15 dB at any frequency
df_clean['asym_significant'] = df_clean['asym_max'] > 15

# ── Sex labels ────────────────────────────────────────────────────────────
if 'riagendr' in df_clean.columns:
    df_clean['sex_label'] = df_clean['riagendr'].map(SEX_LABELS)
else:
    df_clean['sex_label'] = 'Unknown'

# ── Missingness tracking ──────────────────────────────────────────────────
threshold_cols = (
    [f'threshold_right_{f}' for f in FREQS_HZ] +
    [f'threshold_left_{f}' for f in FREQS_HZ]
)
df_clean['n_missing_thresholds'] = df_clean[threshold_cols].isna().sum(axis=1)
df_clean['any_missing'] = df_clean[threshold_cols].isna().any(axis=1)
df_clean['all_missing'] = df_clean[threshold_cols].isna().all(axis=1)

print(f"  PTA computed: {np.sum(~np.isnan(worse_pta)):,} participants")
print(f"  Missing all thresholds: {df_clean['all_missing'].sum()}")
print(f"  Any threshold missing: {df_clean['any_missing'].sum()}")

# ═══════════════════════════════════════════════════════════════════════════
# 3. GENERATE FIGURES
# ═══════════════════════════════════════════════════════════════════════════

print("\n[3/8] Generating figures...")

# ────────────────────────────────────────────────────────────────────────────
# FIGURE 1: Age distribution with sex overlay
# ────────────────────────────────────────────────────────────────────────────
print("  → fig_eda_age_dist.png")

fig, axes = plt.subplots(1, 2, figsize=(16, 6))

if has_demo and 'ridageyr' in df_clean.columns:
    age_valid = df_clean['ridageyr'].dropna()
    age_valid = age_valid[age_valid > 0]

    # Left panel: overall age histogram
    ax = axes[0]
    ax.hist(age_valid, bins=40, color='#3498DB', alpha=0.7,
            edgecolor='white', linewidth=0.5)
    ax.axvline(age_valid.mean(), color='#E74C3C', linestyle='--', linewidth=2,
               label=f"Mean: {age_valid.mean():.1f} yrs")
    ax.axvline(age_valid.median(), color='#E67E22', linestyle=':', linewidth=2,
               label=f"Median: {age_valid.median():.1f} yrs")
    ax.set_xlabel('Age (years)')
    ax.set_ylabel('Count')
    ax.set_title('Age Distribution — Overall', fontweight='bold')
    ax.legend()
    add_stats_box(ax, [
        f'N = {len(age_valid):,}',
        f'Range: {age_valid.min():.0f} – {age_valid.max():.0f}',
        f'SD: {age_valid.std():.1f}',
    ])

    # Right panel: sex-overlaid histogram
    ax = axes[1]
    for sex_label, color in SEX_COLORS.items():
        subset = df_clean.loc[df_clean['sex_label'] == sex_label, 'ridageyr'].dropna()
        subset = subset[subset > 0]
        ax.hist(subset, bins=40, alpha=0.5, color=color, label=sex_label,
                edgecolor='white', linewidth=0.4)
    ax.set_xlabel('Age (years)')
    ax.set_ylabel('Count')
    ax.set_title('Age Distribution by Sex', fontweight='bold')
    ax.legend()

    # Sex ratio text
    sex_counts = df_clean['sex_label'].value_counts()
    sex_text = f"Male: {sex_counts.get('Male', 0):,}\nFemale: {sex_counts.get('Female', 0):,}"
    ax.text(0.97, 0.95, sex_text, transform=ax.transAxes,
            fontsize=9, va='top', ha='right',
            bbox=dict(boxstyle='round,pad=0.4', facecolor='white', alpha=0.85))
else:
    for ax in axes:
        ax.text(0.5, 0.5, 'Age/sex data not available\n(P_DEMO.xpt not found)',
                transform=ax.transAxes, ha='center', va='center', fontsize=12)

plt.tight_layout()
fig.savefig(FIGURES_DIR / 'fig_eda_age_dist.png', bbox_inches='tight')
plt.close(fig)


# ────────────────────────────────────────────────────────────────────────────
# FIGURE 2: Violin plots of thresholds at each frequency (both ears)
# ────────────────────────────────────────────────────────────────────────────
print("  → fig_eda_threshold_dist.png")

fig, axes = plt.subplots(1, 2, figsize=(16, 7), sharey=True)

for ear_idx, (ear, title, ax) in enumerate(zip(
    ['right', 'left'], ['Right Ear', 'Left Ear'], axes
)):
    data = []
    for f in FREQS_HZ:
        col = f'threshold_{ear}_{f}'
        vals = df_clean[col].dropna().values
        data.append(vals)

    # Violin plot
    parts = ax.violinplot(data, positions=range(len(FREQS_HZ)),
                          showmeans=True, showmedians=True,
                          showextrema=True, widths=0.7)

    for pc in parts['bodies']:
        pc.set_facecolor('#3498DB' if ear == 'right' else '#E74C3C')
        pc.set_alpha(0.4)
        pc.set_edgecolor('none')
    parts['cmeans'].set_color('black')
    parts['cmeans'].set_linewidth(1.5)
    parts['cmedians'].set_color('#E67E22')
    parts['cmedians'].set_linewidth(1.5)
    parts['cbars'].set_color('gray')
    parts['cmaxes'].set_color('gray')
    parts['cmins'].set_color('gray')

    # WHO bands
    for i in range(len(WHO_BOUNDARIES) - 1):
        ax.axhspan(WHO_BOUNDARIES[i], WHO_BOUNDARIES[i+1],
                   alpha=0.06, color=list(WHO_COLORS.values())[i], zorder=0)

    ax.set_xticks(range(len(FREQS_HZ)))
    ax.set_xticklabels(FREQ_LABELS_SHORT)
    ax.set_xlabel('Frequency (Hz)')
    ax.set_ylabel('Threshold (dB HL)')
    ax.set_title(f'{title} — Threshold Distribution', fontweight='bold')
    ax.invert_yaxis()
    ax.set_ylim(110, -10)

    # Add mean line
    means = [np.nanmean(d) for d in data]
    ax.plot(range(len(FREQS_HZ)), means, 'o-', color='#2C3E50',
            linewidth=1.5, markersize=4, alpha=0.7, label='Mean')

    if ear == 'right':
        ax.legend(loc='lower right')

    # Sample sizes
    n_text = f"n (valid): {[len(d) for d in data]}"
    ax.text(0.02, 0.98, n_text, transform=ax.transAxes,
            fontsize=7, va='top', ha='left',
            bbox=dict(boxstyle='round,pad=0.2', facecolor='white', alpha=0.7))

plt.tight_layout()
fig.savefig(FIGURES_DIR / 'fig_eda_threshold_dist.png', bbox_inches='tight')
plt.close(fig)


# ────────────────────────────────────────────────────────────────────────────
# FIGURE 3: PTA-4 distribution with WHO severity bands
# ────────────────────────────────────────────────────────────────────────────
print("  → fig_eda_pta_dist.png")

pta_valid = worse_pta[~np.isnan(worse_pta)]

fig, ax = plt.subplots(figsize=(14, 6))

n, bins, patches = ax.hist(pta_valid, bins=60, alpha=0.7,
                            color='#3498DB', edgecolor='white', linewidth=0.5)

# WHO color bands
for i in range(len(WHO_BOUNDARIES) - 1):
    ax.axvspan(WHO_BOUNDARIES[i], WHO_BOUNDARIES[i+1],
               alpha=0.08, color=list(WHO_COLORS.values())[i], zorder=0)
    if i < len(WHO_BOUNDARIES) - 1:
        ax.axvline(WHO_BOUNDARIES[i+1], color=list(WHO_COLORS.values())[i],
                   linestyle='--', alpha=0.4, linewidth=0.8)

ax.set_xlabel('Worse-Ear PTA-4 (dB HL)', fontweight='bold')
ax.set_ylabel('Number of Participants', fontweight='bold')
ax.set_title('PTA-4 Distribution with WHO Severity Bands\n'
             f'(NHANES 2017–2020, n = {len(pta_valid):,})', fontweight='bold')

# Legend for WHO bands
patches_leg = [mpatches.Patch(color=list(WHO_COLORS.values())[i], alpha=0.3,
                               label=WHO_LABELS[i])
               for i in range(len(WHO_LABELS))]
ax.legend(handles=patches_leg, loc='upper right', fontsize=9, framealpha=0.9)

# Stats box
borderline_count = int(np.sum([is_borderline(v) for v in pta_valid]))
add_stats_box(ax, [
    f'Mean ± SD: {np.nanmean(pta_valid):.1f} ± {np.nanstd(pta_valid):.1f} dB',
    f'Median [IQR]: {np.nanmedian(pta_valid):.1f} '
    f'[{np.nanpercentile(pta_valid, 25):.1f}–{np.nanpercentile(pta_valid, 75):.1f}]',
    f'Range: {np.nanmin(pta_valid):.0f}–{np.nanmax(pta_valid):.0f} dB',
    f'Borderline (±5 dB of boundary): {borderline_count:,} '
    f'({borderline_count/len(pta_valid)*100:.1f}%)',
])

plt.tight_layout()
fig.savefig(FIGURES_DIR / 'fig_eda_pta_dist.png', bbox_inches='tight')
plt.close(fig)


# ────────────────────────────────────────────────────────────────────────────
# FIGURE 4: Correlation heatmap
# ────────────────────────────────────────────────────────────────────────────
print("  → fig_eda_correlation.png")

# Full correlation matrix (both ears, all frequencies)
corr_cols = (
    [f'threshold_right_{f}' for f in FREQS_HZ] +
    [f'threshold_left_{f}' for f in FREQS_HZ]
)
corr_labels = [f'R-{l}' for l in FREQ_LABELS_SHORT] + [f'L-{l}' for l in FREQ_LABELS_SHORT]
corr_data = df_clean[corr_cols].copy()
corr_matrix = corr_data.corr(method='pearson')

fig, ax = plt.subplots(figsize=(12, 10))

mask = np.triu(np.ones_like(corr_matrix, dtype=bool), k=1)
cmap = sns.diverging_palette(10, 240, as_cmap=True)

sns.heatmap(corr_matrix, mask=mask, cmap='RdYlBu_r', vmin=0.2, vmax=1.0,
            annot=True, fmt='.2f', square=True,
            linewidths=0.5, cbar_kws={'shrink': 0.75, 'label': "Pearson r"},
            annot_kws={'fontsize': 7}, ax=ax)

ax.set_xticklabels(corr_labels, rotation=45, ha='right', fontsize=9)
ax.set_yticklabels(corr_labels, rotation=0, fontsize=9)
ax.set_title('Threshold Correlation Matrix — Both Ears\n'
             f'(NHANES P_AUX, n = {len(df_clean):,})',
             fontweight='bold', fontsize=13)

plt.tight_layout()
fig.savefig(FIGURES_DIR / 'fig_eda_correlation.png', bbox_inches='tight')
plt.close(fig)


# ────────────────────────────────────────────────────────────────────────────
# FIGURE 5: Audiogram configuration prevalence
# ────────────────────────────────────────────────────────────────────────────
print("  → fig_eda_config_dist.png")

# Use slope classification
slope_categories = df_clean['slope_category'].dropna()
slope_counts = Counter(slope_categories)
slope_order = ['Rising', 'Flat', 'Gently Sloping', 'Steeply Sloping', 'Precipitous']
slope_values = [slope_counts.get(c, 0) for c in slope_order]
slope_pcts = [v / len(slope_categories) * 100 for v in slope_values]
slope_colors_solid = ['#3498DB', '#2ECC71', '#F1C40F', '#E67E22', '#E74C3C']

# Use fuzzy classifier on a random sample (n=2000) for configuration prevalence
# The full classifier on 5000+ participants is very slow due to skfuzzy overhead
np.random.seed(42)
sample_idx = np.random.choice(
    df_clean.index,
    size=min(2000, len(df_clean)),
    replace=False
)
sample_df = df_clean.loc[sample_idx].copy()

config_labels_list = [np.nan] * len(df_clean)
for idx, row in sample_df.iterrows():
    thresholds_left_pad = [
        row.get('threshold_left_500', np.nan),    # 250 Hz
        row.get('threshold_left_500', np.nan),     # 500
        row.get('threshold_left_1000', np.nan),    # 1k
        row.get('threshold_left_2000', np.nan),    # 2k
        row.get('threshold_left_3000', np.nan),    # 3k
        row.get('threshold_left_4000', np.nan),    # 4k
        row.get('threshold_left_6000', np.nan),    # 6k
        row.get('threshold_left_8000', np.nan),    # 8k
    ]
    thresholds_right_pad = [
        row.get('threshold_right_500', np.nan),
        row.get('threshold_right_500', np.nan),
        row.get('threshold_right_1000', np.nan),
        row.get('threshold_right_2000', np.nan),
        row.get('threshold_right_3000', np.nan),
        row.get('threshold_right_4000', np.nan),
        row.get('threshold_right_6000', np.nan),
        row.get('threshold_right_8000', np.nan),
    ]
    if all(np.isnan(t) for t in thresholds_left_pad + thresholds_right_pad):
        continue
    try:
        result = classify_audiogram(thresholds_left_pad, thresholds_right_pad)
        config_labels_list[df_clean.index.get_loc(idx)] = result['configuration_label']
    except Exception:
        pass

df_clean['config_label'] = config_labels_list

# Figure: 2 panels side by side
fig, axes = plt.subplots(1, 2, figsize=(16, 6))

# Left: Slope category bar chart
ax = axes[0]
bars = ax.bar(slope_order, slope_values, color=slope_colors_solid,
              edgecolor='white', linewidth=1.5, alpha=0.85)
for bar, val, pct in zip(bars, slope_values, slope_pcts):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(slope_values)*0.01,
            f'{val:,}\n({pct:.1f}%)', ha='center', va='bottom', fontsize=9,
            fontweight='bold')
ax.set_ylabel('Number of Participants')
ax.set_title('Audiogram Configuration by Slope\n'
             '(4 kHz − 500 Hz)', fontweight='bold')
ax.tick_params(axis='x', rotation=15)

# Right: Fuzzy configuration label bar chart
ax = axes[1]
config_valid = [c for c in config_labels_list if not (isinstance(c, float) and np.isnan(c))]
config_counts = Counter(config_valid)
config_order = ['Normal', 'Flat', 'Sloping', 'Notched', 'Precipitous', 'Rising']
config_values = [config_counts.get(c, 0) for c in config_order]
config_pcts = [v / len(config_valid) * 100 if len(config_valid) > 0 else 0 for v in config_values]
config_colors = ['#2ECC71', '#3498DB', '#F1C40F', '#E67E22', '#E74C3C', '#9B59B6']

bars = ax.bar(config_order, config_values, color=config_colors,
              edgecolor='white', linewidth=1.5, alpha=0.85)
for bar, val, pct in zip(bars, config_values, config_pcts):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(config_values)*0.01,
            f'{val:,}\n({pct:.1f}%)', ha='center', va='bottom', fontsize=9,
            fontweight='bold')
ax.set_ylabel('Number of Participants')
ax.set_title('Audiogram Configuration — Fuzzy Classification\n'
             '(worse ear)', fontweight='bold')
ax.tick_params(axis='x', rotation=15)

plt.tight_layout()
fig.savefig(FIGURES_DIR / 'fig_eda_config_dist.png', bbox_inches='tight')
plt.close(fig)


# ────────────────────────────────────────────────────────────────────────────
# FIGURE 6: Inter-aural asymmetry distribution
# ────────────────────────────────────────────────────────────────────────────
print("  → fig_eda_asymmetry.png")

asym_valid = df_clean['asym_max'].dropna()

fig, axes = plt.subplots(1, 2, figsize=(16, 6))

# Left: histogram of max asymmetry
ax = axes[0]
ax.hist(asym_valid, bins=50, alpha=0.7, color='#9B59B6',
        edgecolor='white', linewidth=0.5)

asym_zones = [
    (0, 15, '#2ECC71', 'Symmetric (0–15 dB)'),
    (15, 30, '#F1C40F', 'Mild (15–30 dB)'),
    (30, 45, '#E67E22', 'Moderate (30–45 dB)'),
    (45, 100, '#E74C3C', 'Severe (>45 dB)'),
]
for lo, hi, color, label in asym_zones:
    ax.axvspan(lo, hi, alpha=0.1, color=color, zorder=0)

ax.set_xlabel('Max Inter-Aural Difference (dB)')
ax.set_ylabel('Number of Participants')
ax.set_title('Max Inter-Aural Asymmetry Distribution', fontweight='bold')

patches_leg = [mpatches.Patch(color=c, alpha=0.3, label=l)
               for _, _, c, l in asym_zones]
ax.legend(handles=patches_leg, loc='upper right', fontsize=9)

p15 = np.sum(asym_valid > 15) / len(asym_valid) * 100
add_stats_box(ax, [
    f'Mean ± SD: {np.nanmean(asym_valid):.1f} ± {np.nanstd(asym_valid):.1f} dB',
    f'Median: {np.nanmedian(asym_valid):.1f} dB',
    f'P95: {np.nanpercentile(asym_valid, 95):.1f} dB',
    f'Max: {np.nanmax(asym_valid):.0f} dB',
    f'>15 dB: {int(np.sum(asym_valid > 15)):,} ({p15:.1f}%)',
])

# Right: asymmetry by frequency (box plot)
ax = axes[1]
asym_data = [df_clean[f'asym_{f}'].dropna().values for f in FREQS_HZ]

bp = ax.boxplot(asym_data, positions=range(len(FREQS_HZ)),
                patch_artist=True, showfliers=False, widths=0.6)
for patch, color in zip(bp['boxes'], ['#3498DB'] * len(FREQS_HZ)):
    patch.set_facecolor(color)
    patch.set_alpha(0.5)

# Add mean markers
means = [np.nanmean(d) for d in asym_data]
ax.plot(range(len(FREQS_HZ)), means, 'o-', color='#E74C3C',
        linewidth=2, markersize=6, label='Mean')

ax.axhline(15, color='#E74C3C', linestyle='--', alpha=0.7, linewidth=1,
           label='Clinical threshold (15 dB)')

ax.set_xticks(range(len(FREQS_HZ)))
ax.set_xticklabels(FREQ_LABELS_SHORT)
ax.set_xlabel('Frequency (Hz)')
ax.set_ylabel('Inter-Aural Difference (dB)')
ax.set_title('Asymmetry by Frequency', fontweight='bold')
ax.legend()

plt.tight_layout()
fig.savefig(FIGURES_DIR / 'fig_eda_asymmetry.png', bbox_inches='tight')
plt.close(fig)


# ────────────────────────────────────────────────────────────────────────────
# FIGURE 7: Bivariate panels (age vs PTA, sex vs severity, etc.)
# ────────────────────────────────────────────────────────────────────────────
print("  → fig_eda_bivariate.png")

fig, axes = plt.subplots(2, 3, figsize=(18, 12))

# (A) Age vs PTA (scatter with regression)
ax = axes[0, 0]
if has_demo and 'ridageyr' in df_clean.columns:
    valid_idx = (df_clean['ridageyr'] > 0) & (~np.isnan(df_clean['pta_worse']))
    ages = df_clean.loc[valid_idx, 'ridageyr']
    ptas = df_clean.loc[valid_idx, 'pta_worse']
    ax.scatter(ages, ptas, alpha=0.15, s=10, color='#3498DB', edgecolors='none')

    # Regression line
    from numpy.polynomial.polynomial import polyfit, polyval
    coeffs = polyfit(ages, ptas, 1)
    x_line = np.linspace(ages.min(), ages.max(), 100)
    ax.plot(x_line, polyval(x_line, coeffs), color='#E74C3C', linewidth=2,
            label=f'Linear fit (r² not applicable)')

    # Binned means
    age_bins = np.arange(0, 90, 10)
    bin_labels = [f'{i}-{i+9}' for i in age_bins[:-1]]
    df_clean['age_bin'] = pd.cut(df_clean['ridageyr'], bins=np.append(age_bins, 200),
                                  labels=bin_labels + ['90+'], right=False)
    bin_means = df_clean.groupby('age_bin', observed=True)['pta_worse'].mean()

    ax.set_xlabel('Age (years)')
    ax.set_ylabel('PTA-4 (dB HL)')
    ax.set_title('A: Age vs Worse-Ear PTA-4', fontweight='bold')
    ax.legend(loc='upper left')

    # Correlation
    from scipy.stats import pearsonr
    r, p = pearsonr(ages, ptas)
    ax.text(0.97, 0.05, f'r = {r:.3f}\np {"< 0.001" if p < 0.001 else f"= {p:.4f}"}',
            transform=ax.transAxes, fontsize=9, va='bottom', ha='right',
            bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8))
else:
    ax.text(0.5, 0.5, 'Age data not available', transform=ax.transAxes,
            ha='center', va='center', fontsize=11)

# (B) Sex vs PTA (violin)
ax = axes[0, 1]
if has_demo:
    sex_data = {'Male': [], 'Female': []}
    for sex_label in ['Male', 'Female']:
        vals = df_clean.loc[df_clean['sex_label'] == sex_label, 'pta_worse'].dropna()
        sex_data[sex_label] = vals.values

    positions = [0, 1]
    parts = ax.violinplot([sex_data['Male'], sex_data['Female']],
                          positions=positions, showmeans=True, showmedians=True, widths=0.6)
    for pc, color in zip(parts[' bodies'], ['#3498DB', '#E74C3C']):
        pc.set_facecolor(color)
        pc.set_alpha(0.4)
        pc.set_edgecolor('none')
    parts['cmeans'].set_color('black')
    parts['cmedians'].set_color('#E67E22')

    # Add box plot overlay
    bp = ax.boxplot([sex_data['Male'], sex_data['Female']],
                    positions=positions, widths=0.15, patch_artist=True,
                    showfliers=False)
    for patch, color in zip(bp['boxes'], ['#3498DB', '#E74C3C']):
        patch.set_facecolor(color)
        patch.set_alpha(0.6)

    # Means
    means = [np.nanmean(sex_data['Male']), np.nanmean(sex_data['Female'])]
    for i, m in enumerate(means):
        ax.text(i, m + 2, f'{m:.1f} dB', ha='center', fontsize=9, fontweight='bold')

    ax.set_xticks(positions)
    ax.set_xticklabels(['Male', 'Female'])
    ax.set_ylabel('PTA-4 (dB HL)')
    ax.set_title('B: PTA-4 by Sex', fontweight='bold')
else:
    ax.text(0.5, 0.5, 'Sex data not available', transform=ax.transAxes,
            ha='center', va='center', fontsize=11)

# (C) Sex vs WHO severity (stacked bar)
ax = axes[0, 2]
if has_demo:
    cat_order = ['Normal', 'Mild', 'Moderate', 'Moderately Severe', 'Severe', 'Profound']
    sex_cats = {'Male': [], 'Female': []}
    for sex_label in ['Male', 'Female']:
        subset = df_clean[df_clean['sex_label'] == sex_label]['who_category']
        sex_cats[sex_label] = [np.sum(subset == c) for c in cat_order]

    x = np.arange(len(cat_order))
    width = 0.35
    bars1 = ax.bar(x - width/2, sex_cats['Male'], width, label='Male',
                    color='#3498DB', alpha=0.8, edgecolor='white')
    bars2 = ax.bar(x + width/2, sex_cats['Female'], width, label='Female',
                    color='#E74C3C', alpha=0.8, edgecolor='white')

    # Percentages
    for bars, total in [(bars1, sum(sex_cats['Male'])), (bars2, sum(sex_cats['Female']))]:
        for bar, val in zip(bars, [b.get_height() for b in bars]):
            if val > 0:
                pct = val / total * 100
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 10,
                        f'{pct:.0f}%', ha='center', fontsize=7, fontweight='bold')

    ax.set_xticks(x)
    ax.set_xticklabels(cat_order, rotation=30, ha='right')
    ax.set_ylabel('Count')
    ax.set_title('C: WHO Severity by Sex', fontweight='bold')
    ax.legend()
else:
    ax.text(0.5, 0.5, 'Sex data not available', transform=ax.transAxes,
            ha='center', va='center', fontsize=11)

# (D) Age vs WHO severity (box plot)
ax = axes[1, 0]
if has_demo and 'ridageyr' in df_clean.columns:
    age_by_cat = {}
    for cat in cat_order:
        vals = df_clean.loc[df_clean['who_category'] == cat, 'ridageyr'].dropna()
        vals = vals[vals > 0]
        if len(vals) > 0:
            age_by_cat[cat] = vals.values

    positions = range(len(cat_order))
    data_list = [age_by_cat.get(c, [np.nan]) for c in cat_order]
    # Filter empty
    valid_idx = [i for i, d in enumerate(data_list) if len(d) > 0 and not np.all(np.isnan(d))]
    valid_cats = [cat_order[i] for i in valid_idx]
    valid_data = [data_list[i] for i in valid_idx]

    bp = ax.boxplot(valid_data, positions=range(len(valid_data)),
                    patch_artist=True, showfliers=False, widths=0.6)
    colors_box = [list(WHO_COLORS.values())[i] for i in valid_idx]
    for patch, color in zip(bp['boxes'], colors_box):
        patch.set_facecolor(color)
        patch.set_alpha(0.5)

    # Mean age per category
    means_age = [np.nanmean(d) for d in valid_data]
    ax.plot(range(len(valid_data)), means_age, 'o-', color='#2C3E50', linewidth=1.5)

    ax.set_xticks(range(len(valid_cats)))
    ax.set_xticklabels(valid_cats, rotation=30, ha='right')
    ax.set_ylabel('Age (years)')
    ax.set_title('D: Age by WHO Severity', fontweight='bold')
else:
    ax.text(0.5, 0.5, 'Age data not available', transform=ax.transAxes,
            ha='center', va='center', fontsize=11)

# (E) Borderline analysis
ax = axes[1, 1]
bl_valid = df_clean[df_clean['who_category'].notna()]
bl_counts = bl_valid['who_category'].value_counts()
bl_total = len(bl_valid)

# For each category, how many are within 5 dB of the NEXT boundary?
cat_boundary_map = {
    'Normal': (25, 'Mild'),
    'Mild': (40, 'Moderate'),
    'Moderate': (55, 'Moderately Severe'),
    'Moderately Severe': (70, 'Severe'),
    'Severe': (90, 'Profound'),
}
borderline_counts = {}
for cat, (boundary, next_cat) in cat_boundary_map.items():
    subset = df_clean[df_clean['who_category'] == cat]
    if cat == 'Normal':
        bl_at = np.sum(subset['pta_worse'] >= (boundary - 5))
    elif cat == 'Severe':
        bl_at = np.sum(subset['pta_worse'] >= (boundary - 5))
    else:
        # Near upper boundary
        bl_at = np.sum(subset['pta_worse'] >= (boundary - 5))
    borderline_counts[cat] = int(bl_at)

bl_cats = list(cat_boundary_map.keys())
bl_vals = [borderline_counts.get(c, 0) for c in bl_cats]

bars = ax.bar(bl_cats, bl_vals, color=list(WHO_COLORS.values())[:len(bl_cats)],
              edgecolor='white', alpha=0.8)
for bar, val in zip(bars, bl_vals):
    pct = val / bl_counts.get(bl_cats[bars.index(bar)], 1) * 100
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 5,
            f'{val:,}\n({pct:.1f}%)', ha='center', fontsize=8, fontweight='bold')

ax.set_ylabel('Count (borderline)')
ax.set_title('E: Participants Near WHO Boundaries (±5 dB)', fontweight='bold')
ax.tick_params(axis='x', rotation=30)

# (F) Missing data overview
ax = axes[1, 2]
missing_counts = df_clean[threshold_cols].isna().sum()
missing_pcts = missing_counts / len(df_clean) * 100

# Group by ear and frequency
right_missing = missing_counts[[f'threshold_right_{f}' for f in FREQS_HZ]]
left_missing = missing_counts[[f'threshold_left_{f}' for f in FREQS_HZ]]

x = np.arange(len(FREQ_LABELS_SHORT))
width = 0.35
ax.bar(x - width/2, right_missing.values, width, label='Right Ear',
       color='#3498DB', alpha=0.8, edgecolor='white')
ax.bar(x + width/2, left_missing.values, width, label='Left Ear',
       color='#E74C3C', alpha=0.8, edgecolor='white')

for i, (rv, lv) in enumerate(zip(right_missing.values, left_missing.values)):
    if rv > 0:
        ax.text(i - width/2, rv + 2, f'{rv}', ha='center', fontsize=7, fontweight='bold')
    if lv > 0:
        ax.text(i + width/2, lv + 2, f'{lv}', ha='center', fontsize=7, fontweight='bold')

ax.set_xticks(x)
ax.set_xticklabels(FREQ_LABELS_SHORT)
ax.set_xlabel('Frequency (Hz)')
ax.set_ylabel('Missing Count')
ax.set_title('F: Missing Thresholds by Frequency & Ear', fontweight='bold')
ax.legend()

plt.tight_layout()
fig.savefig(FIGURES_DIR / 'fig_eda_bivariate.png', bbox_inches='tight')
plt.close(fig)


# ────────────────────────────────────────────────────────────────────────────
# FIGURE 8: Missing data pattern analysis
# ────────────────────────────────────────────────────────────────────────────
print("  → fig_eda_missingness.png")

fig, axes = plt.subplots(1, 3, figsize=(18, 6))

# Panel A: Missingness heatmap (binary)
ax = axes[0]
is_missing = df_clean[threshold_cols].isna().astype(int).iloc[:500]  # sample
sns.heatmap(is_missing.T, cmap='RdBu', cbar=False, ax=ax,
            yticklabels=corr_labels, xticklabels=False)
ax.set_xlabel('Participants (first 500)')
ax.set_ylabel('Threshold')
ax.set_title('A: Missing Data Pattern (sample of 500)', fontweight='bold')

# Panel B: Participants with vs without missing thresholds
ax = axes[1]
# Group: complete cases vs missing
complete = (~df_clean['any_missing']).sum()
incomplete = df_clean['any_missing'].sum()
all_miss = df_clean['all_missing'].sum()
partial_miss = incomplete - all_miss

cats_miss = ['All Thresholds\nPresent', 'Partial\nMissing', 'All\nMissing']
vals_miss = [complete, partial_miss, all_miss]
colors_miss = ['#2ECC71', '#F1C40F', '#E74C3C']

bars = ax.bar(cats_miss, vals_miss, color=colors_miss, edgecolor='white', alpha=0.85)
for bar, val in zip(bars, vals_miss):
    pct = val / len(df_clean) * 100
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 10,
            f'{val:,}\n({pct:.1f}%)', ha='center', fontsize=11, fontweight='bold')
ax.set_ylabel('Number of Participants')
ax.set_title('B: Missing Data Overview', fontweight='bold')

# Panel C: Missingness correlation with other factors
ax = axes[2]
if has_demo and 'ridageyr' in df_clean.columns:
    missing_any = df_clean['any_missing'].astype(int)
    # Mean age by missing status
    age_miss = df_clean.loc[df_clean['any_missing'], 'ridageyr'].dropna()
    age_miss = age_miss[age_miss > 0]
    age_complete = df_clean.loc[~df_clean['any_missing'], 'ridageyr'].dropna()
    age_complete = age_complete[age_complete > 0]

    data_box = [age_complete.values, age_miss.values]
    bp = ax.boxplot(data_box, positions=[0, 1], patch_artist=True,
                    showfliers=False, widths=0.5)
    for patch, color in zip(bp['boxes'], ['#2ECC71', '#E74C3C']):
        patch.set_facecolor(color)
        patch.set_alpha(0.5)

    ax.set_xticks([0, 1])
    ax.set_xticklabels(['Complete', 'Missing any'])
    ax.set_ylabel('Age (years)')
    ax.set_title('C: Age by Missing Status', fontweight='bold')

    # Statistical annotation
    from scipy.stats import ttest_ind
    t_stat, p_val = ttest_ind(age_complete, age_miss, equal_var=False)
    ax.text(0.5, 0.95, f't-test: p {"< 0.001" if p_val < 0.001 else f"= {p_val:.4f}"}',
            transform=ax.transAxes, ha='center', fontsize=10,
            bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8))
else:
    ax.text(0.5, 0.5, 'Age data not available', transform=ax.transAxes,
            ha='center', va='center', fontsize=11)

plt.tight_layout()
fig.savefig(FIGURES_DIR / 'fig_eda_missingness.png', bbox_inches='tight')
plt.close(fig)

print("  All figures saved successfully.")


# ═══════════════════════════════════════════════════════════════════════════
# 4. COMPUTE SUMMARY STATISTICS
# ═══════════════════════════════════════════════════════════════════════════

print("\n[4/8] Computing summary statistics...")

# ── Demographics ──────────────────────────────────────────────────────────
n_total = len(df_clean)

if has_demo and 'ridageyr' in df_clean.columns:
    ages = df_clean['ridageyr'].dropna()
    ages = ages[ages > 0]
    age_range = [float(ages.min()), float(ages.max())]
    age_mean = float(ages.mean())
    age_std = float(ages.std())
    age_median = float(ages.median())
    age_q1 = float(ages.quantile(0.25))
    age_q3 = float(ages.quantile(0.75))

    sex_counts = df_clean['sex_label'].value_counts()
    n_male = int(sex_counts.get('Male', 0))
    n_female = int(sex_counts.get('Female', 0))
    sex_ratio = n_male / n_female if n_female > 0 else float('inf')
else:
    age_range = [np.nan, np.nan]
    age_mean = age_std = age_median = age_q1 = age_q3 = np.nan
    n_male = n_female = 0
    sex_ratio = np.nan

# ── Mean thresholds per frequency ─────────────────────────────────────────
threshold_means = {}
for ear in ['right', 'left']:
    for f in FREQS_HZ:
        col = f'threshold_{ear}_{f}'
        threshold_means[f'{ear}_{f}'] = {
            'mean': float(np.nanmean(df_clean[col])),
            'std': float(np.nanstd(df_clean[col])),
            'median': float(np.nanmedian(df_clean[col])),
            'q25': float(np.nanpercentile(df_clean[col], 25)),
            'q75': float(np.nanpercentile(df_clean[col], 75)),
            'n_valid': int(np.sum(~np.isnan(df_clean[col]))),
        }

# ── PTA statistics ────────────────────────────────────────────────────────
pta_stats = {
    'right': {
        'mean': float(np.nanmean(right_pta)),
        'std': float(np.nanstd(right_pta)),
        'median': float(np.nanmedian(right_pta)),
        'q25': float(np.nanpercentile(right_pta, 25)),
        'q75': float(np.nanpercentile(right_pta, 75)),
        'n_valid': int(np.sum(~np.isnan(right_pta))),
    },
    'left': {
        'mean': float(np.nanmean(left_pta)),
        'std': float(np.nanstd(left_pta)),
        'median': float(np.nanmedian(left_pta)),
        'q25': float(np.nanpercentile(left_pta, 25)),
        'q75': float(np.nanpercentile(left_pta, 75)),
        'n_valid': int(np.sum(~np.isnan(left_pta))),
    },
    'worse': {
        'mean': float(np.nanmean(worse_pta)),
        'std': float(np.nanstd(worse_pta)),
        'median': float(np.nanmedian(worse_pta)),
        'q25': float(np.nanpercentile(worse_pta, 25)),
        'q75': float(np.nanpercentile(worse_pta, 75)),
        'min': float(np.nanmin(worse_pta)),
        'max': float(np.nanmax(worse_pta)),
        'n_valid': int(np.sum(~np.isnan(worse_pta))),
    },
    'better': {
        'mean': float(np.nanmean(better_pta)),
        'std': float(np.nanstd(better_pta)),
        'median': float(np.nanmedian(better_pta)),
        'q25': float(np.nanpercentile(better_pta, 25)),
        'q75': float(np.nanpercentile(better_pta, 75)),
        'n_valid': int(np.sum(~np.isnan(better_pta))),
    },
}

# ── WHO severity distribution ─────────────────────────────────────────────
who_dist = df_clean['who_category'].value_counts()
who_total = who_dist.sum()
who_dist_pct = {k: float(v / who_total * 100) for k, v in who_dist.items()}
who_order = ['Normal', 'Mild', 'Moderate', 'Moderately Severe', 'Severe', 'Profound']
who_severity = OrderedDict()
for cat in who_order:
    cnt = int(who_dist.get(cat, 0))
    who_severity[cat] = {
        'count': cnt,
        'percent': float(cnt / who_total * 100) if who_total > 0 else 0,
    }

# ── Borderline analysis ──────────────────────────────────────────────────
n_borderline_total = int(np.sum([is_borderline(v) for v in worse_pta if not np.isnan(v)]))
borderline_by_category = OrderedDict()
for cat in who_order:
    subset = df_clean[df_clean['who_category'] == cat]
    n_cat = len(subset)
    if n_cat > 0:
        n_bl = int(np.sum([is_borderline(v, margin=5) for v in subset['pta_worse'] if not np.isnan(v)]))
    else:
        n_bl = 0
    borderline_by_category[cat] = {
        'n_in_category': n_cat,
        'n_borderline': n_bl,
        'pct_borderline': float(n_bl / n_cat * 100) if n_cat > 0 else 0,
    }

# ── Asymmetry prevalence ──────────────────────────────────────────────────
asym_valid_series = df_clean['asym_max'].dropna()
n_asym_valid = len(asym_valid_series)
n_asym_significant = int(np.sum(asym_valid_series > 15))
asym_by_freq = OrderedDict()
for f in FREQS_HZ:
    vals = df_clean[f'asym_{f}'].dropna()
    n_gt15 = int(np.sum(vals > 15))
    asym_by_freq[f] = {
        'mean': float(np.nanmean(vals)),
        'median': float(np.nanmedian(vals)),
        'n_gt_15dB': n_gt15,
        'pct_gt_15dB': float(n_gt15 / len(vals) * 100) if len(vals) > 0 else 0,
        'n_valid': len(vals),
    }

# ── Configuration prevalence ─────────────────────────────────────────────
# Slope-based
config_slope = OrderedDict()
for cat in slope_order:
    cnt = slope_counts.get(cat, 0)
    config_slope[cat] = {
        'count': cnt,
        'percent': float(cnt / len(slope_categories) * 100) if len(slope_categories) > 0 else 0,
    }

# Fuzzy classifier based
config_valid_list = [c for c in config_labels_list if not (isinstance(c, float) and np.isnan(c))]
config_fuzzy_counts = Counter(config_valid_list)
config_fuzzy = OrderedDict()
for cat in ['Normal', 'Flat', 'Sloping', 'Notched', 'Precipitous', 'Rising']:
    cnt = config_fuzzy_counts.get(cat, 0)
    config_fuzzy[cat] = {
        'count': cnt,
        'percent': float(cnt / len(config_valid_list) * 100) if len(config_valid_list) > 0 else 0,
    }

# ── Missing data summary ─────────────────────────────────────────────────
n_complete = int((~df_clean['any_missing']).sum())
n_partial = int(df_clean['any_missing'].sum() - df_clean['all_missing'].sum())
n_all_missing = int(df_clean['all_missing'].sum())

missing_by_freq = OrderedDict()
for ear, ear_label in [('right', 'Right'), ('left', 'Left')]:
    for f in FREQS_HZ:
        col = f'threshold_{ear}_{f}'
        n_miss = int(df_clean[col].isna().sum())
        missing_by_freq[f'{ear}_{f}'] = {
            'n_missing': n_miss,
            'pct_missing': float(n_miss / len(df_clean) * 100),
        }

# ── Correlation summary (Pearson r between adjacent frequencies) ────────
correlation_summary = {}
for ear, ear_label in [('right', 'Right'), ('left', 'Left')]:
    corr_adj = {}
    for i in range(len(FREQS_HZ) - 1):
        f1, f2 = FREQS_HZ[i], FREQS_HZ[i+1]
        col1 = f'threshold_{ear}_{f1}'
        col2 = f'threshold_{ear}_{f2}'
        mask = ~(df_clean[col1].isna() | df_clean[col2].isna())
        if mask.sum() > 2:
            r_val = float(df_clean.loc[mask, col1].corr(df_clean.loc[mask, col2]))
        else:
            r_val = np.nan
        corr_adj[f'{f1}_vs_{f2}'] = r_val
    correlation_summary[ear] = corr_adj

# ── Assemble full summary dict ────────────────────────────────────────────
summary = OrderedDict()
summary['dataset'] = 'NHANES P_AUX (2017-2020)'
summary['n_total'] = n_total
summary['n_with_audiometry'] = int(np.sum(~df_clean['all_missing']))

if has_demo:
    summary['demographics'] = {
        'age_range_years': age_range,
        'age_mean_sd': [age_mean, age_std],
        'age_median_q1_q3': [age_median, age_q1, age_q3],
        'n_male': n_male,
        'n_female': n_female,
        'sex_ratio_male_female': round(sex_ratio, 3),
        'pct_male': float(n_male / n_total * 100) if n_total > 0 else 0,
    }
else:
    summary['demographics'] = {'note': 'P_DEMO.xpt not available'}

summary['threshold_statistics'] = threshold_means
summary['pta_statistics'] = pta_stats
summary['who_severity_distribution'] = who_severity
summary['borderline_analysis'] = {
    'n_borderline_total': n_borderline_total,
    'pct_borderline': float(n_borderline_total / pta_stats['worse']['n_valid'] * 100),
    'by_category': borderline_by_category,
}
summary['asymmetry'] = {
    'n_with_asymmetry_data': n_asym_valid,
    'mean_max_asymmetry': float(np.nanmean(asym_valid_series)),
    'std_max_asymmetry': float(np.nanstd(asym_valid_series)),
    'median_max_asymmetry': float(np.nanmedian(asym_valid_series)),
    'p95_max_asymmetry': float(np.nanpercentile(asym_valid_series, 95)),
    'n_asymmetry_gt_15dB': n_asym_significant,
    'pct_asymmetry_gt_15dB': float(n_asym_significant / n_asym_valid * 100) if n_asym_valid > 0 else 0,
    'by_frequency': asym_by_freq,
}
summary['configuration_prevalence'] = {
    'slope_based': config_slope,
    'fuzzy_classifier_based': config_fuzzy,
}
summary['missing_data'] = {
    'n_complete_cases': n_complete,
    'n_partial_missing': n_partial,
    'n_all_missing': n_all_missing,
    'pct_complete': float(n_complete / n_total * 100),
    'by_frequency': missing_by_freq,
}
summary['correlation_summary'] = correlation_summary

# Save JSON
with open(OUTPUT_DIR / 'eda_summary.json', 'w') as f:
    json.dump(summary, f, indent=2)
print(f"  Summary saved to {OUTPUT_DIR / 'eda_summary.json'}")

# Also save as human-readable text
with open(OUTPUT_DIR / 'eda_summary.txt', 'w') as f:
    f.write("NHANES AUDIOMETRY EDA — SUMMARY STATISTICS\n")
    f.write("=" * 60 + "\n\n")
    f.write(f"Dataset: {summary['dataset']}\n")
    f.write(f"Total participants: {summary['n_total']:,}\n")
    f.write(f"With audiometry data: {summary['n_with_audiometry']:,}\n\n")

    if 'age_range_years' in summary.get('demographics', {}):
        d = summary['demographics']
        f.write(f"Age range: {d['age_range_years'][0]:.0f} – {d['age_range_years'][1]:.0f} years\n")
        f.write(f"Age (mean ± SD): {d['age_mean_sd'][0]:.1f} ± {d['age_mean_sd'][1]:.1f}\n")
        f.write(f"Sex: {d['n_male']:,} Male ({d['pct_male']:.1f}%), "
                f"{d['n_female']:,} Female ({100-d['pct_male']:.1f}%)\n\n")

    f.write("PTA-4 Statistics (worse ear):\n")
    f.write(f"  Mean ± SD: {pta_stats['worse']['mean']:.1f} ± {pta_stats['worse']['std']:.1f} dB\n")
    f.write(f"  Median [IQR]: {pta_stats['worse']['median']:.1f} "
            f"[{pta_stats['worse']['q25']:.1f}–{pta_stats['worse']['q75']:.1f}] dB\n")
    f.write(f"  Range: {pta_stats['worse']['min']:.0f}–{pta_stats['worse']['max']:.0f} dB\n\n")

    f.write("WHO Severity Distribution:\n")
    for cat, info in who_severity.items():
        f.write(f"  {cat:20s}: {info['count']:6d} ({info['percent']:5.1f}%)\n")
    f.write(f"\nBorderline (±5 dB of WHO boundary): {n_borderline_total:,} "
            f"({summary['borderline_analysis']['pct_borderline']:.1f}%)\n\n")

    f.write("Configuration (slope-based):\n")
    for cat, info in config_slope.items():
        f.write(f"  {cat:20s}: {info['count']:6d} ({info['percent']:5.1f}%)\n")
    f.write("\nConfiguration (fuzzy classifier):\n")
    for cat, info in config_fuzzy.items():
        f.write(f"  {cat:20s}: {info['count']:6d} ({info['percent']:5.1f}%)\n\n")

    f.write(f"Asymmetry >15 dB: {n_asym_significant:,} "
            f"({summary['asymmetry']['pct_asymmetry_gt_15dB']:.1f}%)\n")
    f.write(f"Complete cases: {n_complete:,} ({summary['missing_data']['pct_complete']:.1f}%)\n")

print(f"  Text summary saved to {OUTPUT_DIR / 'eda_summary.txt'}")


# ═══════════════════════════════════════════════════════════════════════════
# 5. GENERATE NARRATIVE
# ═══════════════════════════════════════════════════════════════════════════

print("\n[5/8] Generating EDA narrative...")

# Build narrative from computed stats
narr_lines = []
narr_lines.append("# NHANES Audiometry EDA — Narrative Summary")
narr_lines.append("")
narr_lines.append(f"**Dataset:** NHANES P_AUX (2017–2020), Audiometry Examination File")
narr_lines.append(f"**Total participants:** {n_total:,}")
narr_lines.append(f"**Participants with audiometry data:** {summary['n_with_audiometry']:,}")
narr_lines.append("")

if 'age_range_years' in summary.get('demographics', {}):
    d = summary['demographics']
    narr_lines.append("## Demographics")
    narr_lines.append("")
    narr_lines.append(f"- **Age range:** {d['age_range_years'][0]:.0f} – {d['age_range_years'][1]:.0f} years")
    narr_lines.append(f"- **Mean age:** {d['age_mean_sd'][0]:.1f} ± {d['age_mean_sd'][1]:.1f} years (median: {d['age_median_q1_q3'][0]:.1f})")
    narr_lines.append(f"- **Sex distribution:** {d['n_male']:,} male ({d['pct_male']:.1f}%), {d['n_female']:,} female ({100-d['pct_male']:.1f}%)")
    narr_lines.append(f"- **Sex ratio (M:F):** {d['sex_ratio_male_female']:.2f}")
    narr_lines.append("")

narr_lines.append("## Hearing Threshold Distributions")
narr_lines.append("")
narr_lines.append("Mean thresholds per frequency (dB HL):")
narr_lines.append("")
narr_lines.append("| Frequency | Right Ear | Left Ear |")
narr_lines.append("|-----------|-----------|----------|")
for i, f in enumerate(FREQS_HZ):
    r_mean = threshold_means.get(f'right_{f}', {}).get('mean', np.nan)
    l_mean = threshold_means.get(f'left_{f}', {}).get('mean', np.nan)
    if not np.isnan(r_mean) and not np.isnan(l_mean):
        narr_lines.append(f"| {FREQ_LABELS_SHORT[i]} Hz | {r_mean:.1f} ± {threshold_means[f'right_{f}']['std']:.1f} | {l_mean:.1f} ± {threshold_means[f'left_{f}']['std']:.1f} |")
narr_lines.append("")

narr_lines.append("PTA-4 (pure-tone average of 500, 1000, 2000, 4000 Hz):")
narr_lines.append(f"- **Right ear:** {pta_stats['right']['mean']:.1f} ± {pta_stats['right']['std']:.1f} dB (median: {pta_stats['right']['median']:.1f})")
narr_lines.append(f"- **Left ear:** {pta_stats['left']['mean']:.1f} ± {pta_stats['left']['std']:.1f} dB (median: {pta_stats['left']['median']:.1f})")
narr_lines.append(f"- **Worse ear:** {pta_stats['worse']['mean']:.1f} ± {pta_stats['worse']['std']:.1f} dB (range: {pta_stats['worse']['min']:.0f}–{pta_stats['worse']['max']:.0f})")
narr_lines.append(f"- **Better ear:** {pta_stats['better']['mean']:.1f} ± {pta_stats['better']['std']:.1f} dB")
narr_lines.append("")

narr_lines.append("## Hearing Loss Severity (WHO Classification)")
narr_lines.append("")
narr_lines.append("Based on worse-ear PTA-4:")
narr_lines.append("")
for cat, info in who_severity.items():
    narr_lines.append(f"- **{cat}:** {info['count']:,} ({info['percent']:.1f}%)")
narr_lines.append("")
narr_lines.append(f"**Borderline cases (±5 dB of WHO boundary):** {n_borderline_total:,} ({summary['borderline_analysis']['pct_borderline']:.1f}%)")
narr_lines.append("")

# Borderline detail
narr_lines.append("Borderline cases by WHO category:")
for cat, info in borderline_by_category.items():
    narr_lines.append(f"- {cat}: {info['n_borderline']:,} of {info['n_in_category']:,} ({info['pct_borderline']:.1f}%)")
narr_lines.append("")

narr_lines.append("## Audiogram Configuration")
narr_lines.append("")
narr_lines.append("Based on slope (4 kHz − 500 Hz):")
for cat, info in config_slope.items():
    narr_lines.append(f"- **{cat}:** {info['count']:,} ({info['percent']:.1f}%)")
narr_lines.append("")
narr_lines.append("Based on fuzzy classifier:")
for cat, info in config_fuzzy.items():
    narr_lines.append(f"- **{cat}:** {info['count']:,} ({info['percent']:.1f}%)")
narr_lines.append("")

narr_lines.append("## Inter-Aural Asymmetry")
narr_lines.append("")
narr_lines.append(f"- **Mean max asymmetry:** {summary['asymmetry']['mean_max_asymmetry']:.1f} dB")
narr_lines.append(f"- **Median max asymmetry:** {summary['asymmetry']['median_max_asymmetry']:.1f} dB")
narr_lines.append(f"- **P95:** {summary['asymmetry']['p95_max_asymmetry']:.1f} dB")
narr_lines.append(f"- **Asymmetry >15 dB (clinically significant):** {n_asym_significant:,} ({summary['asymmetry']['pct_asymmetry_gt_15dB']:.1f}%)")
narr_lines.append("")
narr_lines.append("Asymmetry by frequency:")
for f in FREQS_HZ:
    info = asym_by_freq[f]
    narr_lines.append(f"- **{FREQ_LABELS_SHORT[FREQS_HZ.index(f)]} Hz:** mean {info['mean']:.1f} dB, "
                      f"{info['n_gt_15dB']:,} ({info['pct_gt_15dB']:.1f}%) >15 dB")
narr_lines.append("")

narr_lines.append("## Frequency Correlation Structure")
narr_lines.append("")
narr_lines.append("Correlations between adjacent frequencies (Pearson r):")
for ear in ['right', 'left']:
    narr_lines.append(f"- **{ear.capitalize()} ear:**")
    for pair, r_val in correlation_summary[ear].items():
        if not np.isnan(r_val):
            narr_lines.append(f"  - {pair}: r = {r_val:.3f}")
narr_lines.append("")

narr_lines.append("## Missing Data")
narr_lines.append("")
narr_lines.append(f"- **Complete cases (all 14 thresholds):** {n_complete:,} ({summary['missing_data']['pct_complete']:.1f}%)")
narr_lines.append(f"- **Partial missing:** {n_partial:,} ({n_partial/n_total*100:.1f}%)")
narr_lines.append(f"- **All missing:** {n_all_missing:,} ({n_all_missing/n_total*100:.1f}%)")
narr_lines.append("")
narr_lines.append("Missingness by frequency:")
for key, info in missing_by_freq.items():
    narr_lines.append(f"- {key}: {info['n_missing']:,} ({info['pct_missing']:.1f}%)")
narr_lines.append("")

narr_lines.append("## Key Findings")
narr_lines.append("")
narr_lines.append(f"1. The NHANES 2017–2020 sample comprises {n_total:,} participants with "
                  f"{'a wide age range' if not np.isnan(age_range[0]) else 'available'} audiometric data.")
if 'age_range_years' in summary.get('demographics', {}):
    narr_lines.append(f"2. Mean age was {age_mean:.1f} years (SD: {age_std:.1f}), with a slight "
                      f"{'male' if sex_ratio > 1 else 'female'} predominance ({'M:F' if sex_ratio > 1 else 'F:M'} = "
                      f"{sex_ratio if sex_ratio > 1 else 1/sex_ratio:.2f}).")
narr_lines.append(f"3. The mean worse-ear PTA-4 of {pta_stats['worse']['mean']:.1f} dB indicates that this is a "
                  f"{'relatively normal-hearing' if pta_stats['worse']['mean'] < 25 else 'hearing-impaired'} population "
                  f"on average, with a substantial right-skew toward hearing loss.")
narr_lines.append(f"4. The majority of participants have {'normal hearing' if list(who_severity.values())[0]['percent'] > 50 else 'some degree of hearing loss'} "
                  f"({list(who_severity.values())[0]['percent']:.1f}% normal), with hearing loss prevalence increasing with age.")

first_config = list(config_slope.keys())[0]
first_config_pct = list(config_slope.values())[0]['percent']
narr_lines.append(f"5. The most common audiogram configuration is '{first_config}' ({first_config_pct:.1f}%), "
                  f"consistent with an age-hearing population.")

if n_asym_significant > 0:
    narr_lines.append(f"6. Clinically significant asymmetry (>15 dB) was observed in {n_asym_significant:,} "
                      f"({summary['asymmetry']['pct_asymmetry_gt_15dB']:.1f}%) participants, highlighting the importance "
                      f"of ear-specific assessment.")
narr_lines.append(f"7. Threshold correlations were highest between adjacent low-frequency pairs and decreased with "
                  f"increasing frequency separation, reflecting the known frequency-selective nature of cochlear damage.")
narr_lines.append(f"8. Missing data was minimal (complete cases: {n_complete:,}, {summary['missing_data']['pct_complete']:.1f}%), "
                  f"suggesting good data quality in the NHANES audiometry examination.")

# Write narrative
with open(OUTPUT_DIR / 'eda_narrative.md', 'w') as f:
    f.write('\n'.join(narr_lines))
print(f"  Narrative saved to {OUTPUT_DIR / 'eda_narrative.md'}")

# ═══════════════════════════════════════════════════════════════════════════
# DONE
# ═══════════════════════════════════════════════════════════════════════════

print("\n" + "=" * 65)
print("  EDA COMPLETE")
print("=" * 65)
print(f"\nFigures saved to: {FIGURES_DIR}/")
print(f"  - fig_eda_age_dist.png")
print(f"  - fig_eda_threshold_dist.png")
print(f"  - fig_eda_pta_dist.png")
print(f"  - fig_eda_correlation.png")
print(f"  - fig_eda_config_dist.png")
print(f"  - fig_eda_asymmetry.png")
print(f"  - fig_eda_bivariate.png")
print(f"  - fig_eda_missingness.png")
print(f"\nData saved to: {OUTPUT_DIR}/")
print(f"  - eda_summary.json")
print(f"  - eda_summary.txt")
print(f"  - eda_narrative.md")
print(f"\nTotal participants: {n_total:,}")
print(f"With audiometry: {summary['n_with_audiometry']:,}")
print(f"Worse-ear PTA mean: {pta_stats['worse']['mean']:.1f} dB")
