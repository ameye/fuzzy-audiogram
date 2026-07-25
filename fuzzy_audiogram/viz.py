"""
viz.py — Visualization module for fuzzy audiogram analysis.

Provides membership function plots, audiogram overlay panels,
FAI-vs-PTA comparison charts, and NHANES distribution plots.
All plots use matplotlib with the Agg (non-interactive) backend.
"""

import matplotlib
matplotlib.use('Agg')

from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt

from .core import (
    create_severity_universe,
    create_slope_universe,
    create_asymmetry_universe,
    SEVERITY_MF_PARAMS,
    SLOPE_MF_PARAMS,
    NOTCH_MF_PARAMS,
    ASYMMETRY_MF_PARAMS,
    classify_audiogram,
    FREQUENCIES_HZ,
)


# =========================================================================
# 1. MEMBERSHIP FUNCTION PLOTS
# =========================================================================


def _plot_mf(universe, mf_params, xlabel, ylabel, title,
             colors, labels, save_path, vline=None, vspan=None):
    """Generic membership function plotter."""
    import skfuzzy as fuzz

    fig, ax = plt.subplots(figsize=(12, 6))

    for i, (key, params) in enumerate(mf_params.items()):
        mf = fuzz.trapmf(universe, params)
        ax.plot(universe, mf, color=colors[i], linewidth=2.5, label=labels[i])
        ax.fill_between(universe, mf, 0, alpha=0.1, color=colors[i])

    if vspan is not None:
        ax.axvspan(vspan[0], vspan[1], alpha=0.15, color='red',
                   label=vspan[2] if len(vspan) > 2 else None)
    if vline is not None:
        ax.axvline(x=vline[0], color='gray', linestyle='--', alpha=0.5,
                   label=vline[1] if len(vline) > 1 else None)

    ax.set_xlabel(xlabel, fontsize=12)
    ax.set_ylabel(ylabel, fontsize=12)
    ax.set_title(title, fontsize=13, fontweight='bold')
    ax.set_ylim(0, 1.05)
    ax.legend(loc='upper right', fontsize=10)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()
    return save_path


def plot_severity_membership(save_path='severity_membership.png'):
    """Plot overlapping trapezoidal membership functions for hearing
    loss severity.

    Parameters
    ----------
    save_path : str or Path
        Output file path.

    Returns
    -------
    str
        Path to the saved figure.
    """
    save_path = str(save_path)
    universe = create_severity_universe()
    colors = ['#2ecc71', '#f1c40f', '#e67e22', '#e74c3c', '#9b59b6', '#2c3e50']
    labels = ['Normal', 'Mild', 'Moderate', 'Mod. Severe', 'Severe', 'Profound']

    return _plot_mf(
        universe, SEVERITY_MF_PARAMS,
        'Hearing Threshold (dB HL)',
        'Membership Degree',
        'Fuzzy Membership Functions for Hearing Loss Severity\n'
        '(Overlapping trapezoidal — the 25 dB boundary is not absolute)',
        colors, labels, save_path,
        vspan=(24, 27, 'Borderline zone (25-26 dB)'),
    )


def plot_slope_membership(save_path='slope_membership.png'):
    """Plot membership functions for audiogram configuration (slope).

    Parameters
    ----------
    save_path : str or Path
        Output file path.

    Returns
    -------
    str
        Path to the saved figure.
    """
    save_path = str(save_path)
    universe = create_slope_universe()
    colors = ['#3498db', '#2ecc71', '#f1c40f', '#e67e22', '#e74c3c']
    labels = ['Rising', 'Flat', 'Gently Sloping', 'Steeply Sloping',
              'Precipitous']

    return _plot_mf(
        universe, SLOPE_MF_PARAMS,
        'Slope (dB change, 500 Hz → 4 kHz)',
        'Membership Degree',
        'Fuzzy Membership Functions for Audiogram Configuration (Slope)',
        colors, labels, save_path,
        vline=(0, 'Zero slope'),
    )


def plot_asymmetry_membership(save_path='asymmetry_membership.png'):
    """Plot membership functions for inter-aural asymmetry.

    Parameters
    ----------
    save_path : str or Path
        Output file path.

    Returns
    -------
    str
        Path to the saved figure.
    """
    save_path = str(save_path)
    universe = create_asymmetry_universe()
    colors = ['#2ecc71', '#f1c40f', '#e67e22', '#e74c3c']
    labels = ['Symmetric', 'Mildly Asymmetric', 'Mod. Asymmetric',
              'Severely Asymmetric']

    return _plot_mf(
        universe, ASYMMETRY_MF_PARAMS,
        'Inter-aural Difference (dB)',
        'Membership Degree',
        'Fuzzy Membership Functions for Inter-aural Asymmetry',
        colors, labels, save_path,
        vspan=(14, 16, 'Clinical threshold (15 dB)'),
    )


def plot_notch_membership(save_path='notch_membership.png'):
    """Plot membership functions for Carhart notch detection.

    Parameters
    ----------
    save_path : str or Path
        Output file path.

    Returns
    -------
    str
        Path to the saved figure.
    """
    import skfuzzy as fuzz

    save_path = str(save_path)
    universe = np.arange(0, 51, 1)

    fig, ax = plt.subplots(figsize=(10, 5))

    colors = ['#2ecc71', '#f1c40f', '#e74c3c']
    labels = ['No Notch', 'Shallow Notch', 'Deep Notch']

    for i, (key, params) in enumerate(NOTCH_MF_PARAMS.items()):
        mf = fuzz.trapmf(universe, params)
        ax.plot(universe, mf, color=colors[i], linewidth=2.5, label=labels[i])
        ax.fill_between(universe, mf, 0, alpha=0.1, color=colors[i])

    ax.axvspan(14, 16, alpha=0.15, color='red',
               label='Notch threshold (~15 dB)')

    ax.set_xlabel('Notch Depth (dB dip at 4 kHz)', fontsize=12)
    ax.set_ylabel('Membership Degree', fontsize=12)
    ax.set_title('Fuzzy Membership Functions for Carhart Notch Detection',
                 fontsize=13, fontweight='bold')
    ax.set_ylim(0, 1.05)
    ax.legend(loc='lower right', fontsize=10)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()
    return save_path


# =========================================================================
# 2. AUDIOGRAM WITH FUZZY OVERLAY
# =========================================================================


CRISP_BANDS = [
    (0, 25, '#2ecc71', 'Normal'),
    (26, 40, '#f1c40f', 'Mild'),
    (41, 55, '#e67e22', 'Moderate'),
    (56, 70, '#e74c3c', 'Mod-Sev'),
    (71, 90, '#9b59b6', 'Severe'),
    (91, 120, '#2c3e50', 'Profound'),
]

SEVERITY_COLORS = ['#2ecc71', '#f1c40f', '#e67e22', '#e74c3c', '#9b59b6',
                   '#2c3e50']
SEVERITY_SHORT_LABELS = ['Normal', 'Mild', 'Moderate', 'Mod-Sev', 'Severe',
                         'Profound']

SLOPE_COLORS = ['#3498db', '#2ecc71', '#f1c40f', '#e67e22', '#e74c3c']
SLOPE_SHORT_LABELS = ['Rising', 'Flat', 'Gently-Slope', 'Steep-Slope',
                      'Precipitous']


def plot_audiogram_with_fuzzy(thresholds_left, thresholds_right=None,
                              title='', save_path='output.png'):
    """Plot a clinical audiogram with fuzzy classification overlay.

    The left panel shows the traditional pure-tone audiogram with
    crisp severity bands.  The right panel displays the fuzzy
    membership degrees for severity and configuration, plus key
    metrics.

    Parameters
    ----------
    thresholds_left : array-like
        8 values for [250, 500, 1k, 2k, 3k, 4k, 6k, 8k] Hz.
    thresholds_right : array-like, optional
        Right ear thresholds (same order).
    title : str
        Plot title.
    save_path : str or Path
        Output file path.

    Returns
    -------
    str
        Path to the saved figure.
    """
    save_path = str(save_path)
    freq_labels = ['250', '500', '1k', '2k', '3k', '4k', '6k', '8k']
    freq_ticks = range(len(FREQUENCIES_HZ))

    result = classify_audiogram(thresholds_left, thresholds_right)
    left = np.array(thresholds_left, dtype=float)
    has_right = thresholds_right is not None

    fig, (ax1, ax2) = plt.subplots(
        1, 2, figsize=(16, 7),
        gridspec_kw={'width_ratios': [1, 1]},
    )

    # --- Left panel: Traditional audiogram ---
    ax1.invert_yaxis()
    ax1.set_ylim(120, -10)
    ax1.set_xlim(-0.5, 7.5)

    ax1.plot(freq_ticks, left, 'o-', color='#e74c3c', linewidth=2.5,
             markersize=8, label='Left Ear')
    for x, y in zip(freq_ticks, left):
        if not np.isnan(y):
            ax1.annotate(f'{int(y)}', (x, y), textcoords="offset points",
                         xytext=(0, -12), ha='center', fontsize=8,
                         color='#e74c3c')

    if has_right:
        right = np.array(thresholds_right, dtype=float)
        ax1.plot(freq_ticks, right, 's-', color='#3498db', linewidth=2.5,
                 markersize=8, label='Right Ear')
        for x, y in zip(freq_ticks, right):
            if not np.isnan(y):
                ax1.annotate(f'{int(y)}', (x, y), textcoords="offset points",
                             xytext=(0, 10), ha='center', fontsize=8,
                             color='#3498db')

    ax1.set_xticks(freq_ticks)
    ax1.set_xticklabels(freq_labels)
    ax1.set_xlabel('Frequency (Hz)', fontsize=11)
    ax1.set_ylabel('Hearing Level (dB HL)', fontsize=11)
    ax1.set_title('Pure Tone Audiogram', fontsize=12, fontweight='bold')
    ax1.legend(fontsize=10)
    ax1.grid(True, alpha=0.3)

    for low, high, color, _ in CRISP_BANDS:
        ax1.axhspan(low, high, alpha=0.08, color=color)

    # --- Right panel: Fuzzy classification bar ---
    ax2.axis('off')

    # Severity memberships
    memberships = list(result['threshold_memberships'].values())
    y_offset = 0.85
    ax2.text(0.1, y_offset + 0.08, 'Fuzzy Severity Membership',
             fontsize=12, fontweight='bold', transform=ax2.transAxes)

    for i, (val, label, color) in enumerate(
            zip(memberships, SEVERITY_SHORT_LABELS, SEVERITY_COLORS)):
        y = y_offset - 0.05 - i * 0.045
        ax2.barh(y, val, height=0.03, color=color, alpha=0.8,
                 transform=ax2.transAxes)
        ax2.text(0.1, y, f'{label}: {val:.2f}', fontsize=9,
                 transform=ax2.transAxes, verticalalignment='center')

    # Slope memberships
    slope_mems = list(result['slope_memberships'].values())
    y_offset_slope = 0.48
    ax2.text(0.1, y_offset_slope + 0.08, 'Fuzzy Configuration Membership',
             fontsize=12, fontweight='bold', transform=ax2.transAxes)

    for i, (val, label, color) in enumerate(
            zip(slope_mems, SLOPE_SHORT_LABELS, SLOPE_COLORS)):
        y = y_offset_slope - 0.05 - i * 0.045
        ax2.barh(y, val, height=0.03, color=color, alpha=0.8,
                 transform=ax2.transAxes)
        ax2.text(0.1, y, f'{label}: {val:.2f}', fontsize=9,
                 transform=ax2.transAxes, verticalalignment='center')

    # Key metrics
    y_metrics = 0.15
    ax2.text(0.1, y_metrics + 0.10, 'Key Metrics',
             fontsize=12, fontweight='bold', transform=ax2.transAxes)
    metrics = [
        f'PTA-4: {result["pt4a"]:.1f} dB',
        f'FAI Score: {result["fai_score"]}',
        f'FAI Label: {result["fai_label"]}',
        f'Configuration: {result["configuration_label"]}',
        f'Slope: {result["features"]["slope"]:.1f} dB',
        f'Notch Depth: {result["features"]["notch_depth"]:.1f} dB',
    ]
    for i, m in enumerate(metrics):
        ax2.text(0.1, y_metrics - 0.03 - i * 0.035, m, fontsize=10,
                 transform=ax2.transAxes, verticalalignment='center',
                 bbox=dict(boxstyle='round,pad=0.3', facecolor='lightgray',
                           alpha=0.3))

    if title:
        plt.suptitle(title, fontsize=14, fontweight='bold', y=0.98)

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()
    return save_path


# =========================================================================
# 3. FAI vs PTA COMPARISON
# =========================================================================


def plot_fai_vs_pta_comparison(fuzzy_crisp_df, save_path='fai_vs_pta.png'):
    """Plot the comparison between fuzzy FAI scores and crisp
    classification boundaries across PTA values.

    Parameters
    ----------
    fuzzy_crisp_df : pd.DataFrame
        DataFrame from compare_fuzzy_vs_crisp() with columns
        pta, crisp_label, fai_score, *normal_mu, *mild_mu, etc.
    save_path : str or Path
        Output file path.

    Returns
    -------
    str
        Path to the saved figure.
    """
    save_path = str(save_path)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7))

    # --- Left: FAI vs PTA with crisp boundaries ---
    ax1.plot(fuzzy_crisp_df['pta'], fuzzy_crisp_df['fai_score'],
             'o-', color='#2c3e50', linewidth=2, markersize=6,
             label='Fuzzy FAI Score')

    # Crisp boundary lines
    boundaries = [25, 40, 55, 70, 90]
    boundary_labels = ['Normal|Mild (25)', 'Mild|Mod (40)',
                       'Mod|Mod-Sev (55)', 'Mod-Sev|Sev (70)',
                       'Sev|Profound (90)']
    for b, bl in zip(boundaries, boundary_labels):
        ax1.axvline(x=b, color='gray', linestyle='--', alpha=0.5)
        ax1.annotate(bl, (b, 5), rotation=90, fontsize=7,
                     color='gray', alpha=0.7)

    ax1.set_xlabel('PTA-4 (dB HL)', fontsize=12)
    ax1.set_ylabel('Fuzzy Audiometric Index (FAI)', fontsize=12)
    ax1.set_title('FAI vs PTA: Fuzzy vs Crisp Classification',
                  fontsize=13, fontweight='bold')
    ax1.set_xlim(0, 125)
    ax1.set_ylim(0, 100)
    ax1.legend(fontsize=10)
    ax1.grid(True, alpha=0.3)

    # --- Right: Membership degrees across PTA range ---
    colors = ['#2ecc71', '#f1c40f', '#e67e22', '#e74c3c', '#9b59b6', '#2c3e50']
    labels = ['Normal', 'Mild', 'Moderate', 'Mod-Sev', 'Severe', 'Profound']
    mu_cols = ['normal_mu', 'mild_mu', 'moderate_mu',
               'moderately_severe_mu', 'severe_mu', 'profound_mu']

    for i, (col, label, color) in enumerate(
            zip(mu_cols, labels, colors)):
        ax2.plot(fuzzy_crisp_df['pta'], fuzzy_crisp_df[col],
                 color=color, linewidth=2, label=label)

    ax2.set_xlabel('PTA-4 (dB HL)', fontsize=12)
    ax2.set_ylabel('Membership Degree', fontsize=12)
    ax2.set_title('Fuzzy Membership Degrees vs PTA',
                  fontsize=13, fontweight='bold')
    ax2.set_xlim(0, 125)
    ax2.set_ylim(0, 1.05)
    ax2.legend(fontsize=10)
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()
    return save_path


# =========================================================================
# 4. NHANES DISTRIBUTION
# =========================================================================


def plot_nhanes_distribution(nhanes_df, save_path='nhanes_distribution.png'):
    """Plot the distribution of PTA values and WHO categories from
    NHANES audiometry data.

    Parameters
    ----------
    nhanes_df : pd.DataFrame
        Cleaned DataFrame from extract_audiometry().
    save_path : str or Path
        Output file path.

    Returns
    -------
    str
        Path to the saved figure.
    """
    save_path = str(save_path)

    # Compute PTA for both ears
    right_pta = nhanes_df[[c for c in nhanes_df.columns
                           if c.startswith('threshold_right_')
                           and c.split('_')[-1] in ['500', '1000', '2000',
                                                     '4000']]].mean(axis=1,
                                                                    skipna=True)
    left_pta = nhanes_df[[c for c in nhanes_df.columns
                          if c.startswith('threshold_left_')
                          and c.split('_')[-1] in ['500', '1000', '2000',
                                                    '4000']]].mean(axis=1,
                                                                   skipna=True)
    worse_pta = np.maximum(right_pta, left_pta)

    # WHO categories
    def who_cat(v):
        if np.isnan(v):
            return 'Missing'
        if v <= 25:
            return 'Normal'
        elif v <= 40:
            return 'Mild'
        elif v <= 55:
            return 'Moderate'
        elif v <= 70:
            return 'Mod-Sev'
        elif v <= 90:
            return 'Severe'
        else:
            return 'Profound'

    categories = [who_cat(v) for v in worse_pta]
    cat_order = ['Normal', 'Mild', 'Moderate', 'Mod-Sev', 'Severe',
                 'Profound', 'Missing']

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7))

    # --- Histogram of worse-ear PTA ---
    valid_pta = worse_pta[~np.isnan(worse_pta)]
    ax1.hist(valid_pta, bins=40, color='#3498db', alpha=0.7,
             edgecolor='white', linewidth=0.5)
    ax1.axvline(x=np.nanmean(worse_pta), color='#e74c3c', linestyle='--',
                linewidth=2,
                label=f'Mean: {np.nanmean(worse_pta):.1f} dB')
    ax1.axvline(x=np.nanmedian(worse_pta), color='#e67e22', linestyle=':',
                linewidth=2,
                label=f'Median: {np.nanmedian(worse_pta):.1f} dB')

    ax1.set_xlabel('Worse-Ear PTA-4 (dB HL)', fontsize=12)
    ax1.set_ylabel('Count', fontsize=12)
    ax1.set_title('NHANES P_AUX: Distribution of PTA-4 Values',
                  fontsize=13, fontweight='bold')
    ax1.legend(fontsize=10)
    ax1.grid(True, alpha=0.3)

    # --- Bar chart of WHO categories ---
    from collections import Counter
    counts = Counter(categories)
    counts_ordered = [counts.get(c, 0) for c in cat_order]

    bar_colors = ['#2ecc71', '#f1c40f', '#e67e22', '#e74c3c', '#9b59b6',
                  '#2c3e50', '#95a5a6']
    bars = ax2.bar(cat_order, counts_ordered, color=bar_colors, alpha=0.8,
                   edgecolor='white')
    for bar, count in zip(bars, counts_ordered):
        ax2.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 10,
                 str(count), ha='center', fontsize=10, fontweight='bold')

    ax2.set_xlabel('WHO Severity Category', fontsize=12)
    ax2.set_ylabel('Number of Participants', fontsize=12)
    ax2.set_title('NHANES P_AUX: WHO Hearing Loss Categories',
                  fontsize=13, fontweight='bold')
    ax2.grid(True, alpha=0.3, axis='y')

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()
    return save_path
