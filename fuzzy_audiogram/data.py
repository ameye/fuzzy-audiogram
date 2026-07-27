"""
data.py — NHANES audiometry data loader.

Provides functions to load the NHANES P_AUX examination data file
(SAS XPORT format), extract audiometric threshold columns, clean
missing-value indicators, and compute summary statistics.
"""

from pathlib import Path

import numpy as np
import pandas as pd

# Mapping from NHANES column names to standard frequency labels
# NHANES P_AUX uses AUXU* for unaided air-conduction thresholds.
# AUXU1K1 = 1000 Hz first test (used); AUXU1K2 is a repeat.
COLUMN_MAP_RIGHT = {
    'AUXU500R': 500,
    'AUXU1K1R': 1000,
    'AUXU2KR': 2000,
    'AUXU3KR': 3000,
    'AUXU4KR': 4000,
    'AUXU6KR': 6000,
    'AUXU8KR': 8000,
}

COLUMN_MAP_LEFT = {
    'AUXU500L': 500,
    'AUXU1K1L': 1000,
    'AUXU2KL': 2000,
    'AUXU3KL': 3000,
    'AUXU4KL': 4000,
    'AUXU6KL': 6000,
    'AUXU8KL': 8000,
}

TYMPANOMETRY_COLS = [
    'AUXTMEPR', 'AUXTPVR', 'AUXTWIDR', 'AUXTCOMR',
    'AUXTMEPL', 'AUXTPVL', 'AUXTWIDL', 'AUXTCOML',
]

# SAS stores missing numeric values as denormalized floats near 1e-79.
# We treat any value with absolute < 1e-70 as NaN.
_SUBNORMAL_THRESHOLD = 1e-70

# NHANES sentinel codes for audiometry:
# 666 = No response at maximum output (could not hear at max)
# 888 = Could not obtain test result
NHANES_SENTINELS = {666.0, 888.0}

# Physiologically plausible threshold range for pure-tone audiometry
MIN_PLAUSIBLE_THRESHOLD = -10
MAX_PLAUSIBLE_THRESHOLD = 120


def _clean_subnormal(series):
    """Replace SAS subnormal missing-value indicators with NaN."""
    return series.where(np.abs(series) > _SUBNORMAL_THRESHOLD, np.nan)


def _clean_threshold(series):
    """Clean a threshold series: remove subnormals, sentinels, and out-of-range values.

    Converts to NaN:
    - SAS subnormal values (~1e-79)
    - NHANES sentinel codes (666 = no response, 888 = could not obtain)
    - Values outside plausible range (-10 to 120 dB HL)
    """
    s = _clean_subnormal(series)
    # Remove NHANES sentinel codes
    for sentinel in NHANES_SENTINELS:
        s = s.where(s != sentinel, np.nan)
    # Remove physiologically implausible values
    s = s.where((s >= MIN_PLAUSIBLE_THRESHOLD) & (s <= MAX_PLAUSIBLE_THRESHOLD), np.nan)
    return s


def load_nhanes(path):
    """Load the NHANES P_AUX examination data file.

    Parameters
    ----------
    path : str or Path
        Path to the P_AUX.xpt SAS XPORT file.

    Returns
    -------
    pd.DataFrame
        Raw DataFrame with all 90 columns from the NHANES
        audiometry examination file.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"NHANES data file not found: {path}")

    df = pd.read_sas(path, format='xport', encoding='utf-8')
    # Clean up column names just in case
    df.columns = [c.strip().upper() if isinstance(c, str) else c
                  for c in df.columns]
    return df


def extract_audiometry(df):
    """Extract and clean audiometric threshold data from a raw NHANES
    DataFrame.

    Cleans subnormal missing-value indicators, creates standard
    threshold columns for left and right ears at each frequency,
    and keeps participant metadata (SEQN, tympanometry).

    Parameters
    ----------
    df : pd.DataFrame
        Raw NHANES P_AUX DataFrame from load_nhanes().

    Returns
    -------
    pd.DataFrame
        Clean DataFrame with columns:
        - seqn : participant ID (int)
        - threshold_<ear>_<freq_hz> : thresholds in dB HL
        - tymp_<ear>_<measure> : tympanometry values
        - exam_status, exam_mode, etc.
        Missing thresholds (SAS subnormal values) are set to NaN.
    """
    result = pd.DataFrame()
    result['seqn'] = df['SEQN'].astype('int64')

    # Extract and clean right-ear thresholds
    for col, freq in COLUMN_MAP_RIGHT.items():
        if col in df.columns:
            result[f'threshold_right_{freq}'] = _clean_threshold(
                df[col].astype(float)
            )
        else:
            result[f'threshold_right_{freq}'] = np.nan

    # Extract and clean left-ear thresholds
    for col, freq in COLUMN_MAP_LEFT.items():
        if col in df.columns:
            result[f'threshold_left_{freq}'] = _clean_threshold(
                df[col].astype(float)
            )
        else:
            result[f'threshold_left_{freq}'] = np.nan

    # Tympanometry
    for col in TYMPANOMETRY_COLS:
        if col in df.columns:
            result[f'tymp_{col.lower()}'] = df[col].astype(float)

    # Metadata
    if 'AUAEXSTS' in df.columns:
        result['exam_status'] = df['AUAEXSTS'].astype(float)
    if 'AUAMODE' in df.columns:
        result['exam_mode'] = df['AUAMODE'].astype(float)
    if 'AUAEAR' in df.columns:
        result['exam_ear'] = df['AUAEAR'].astype(float)
    if 'AUAFMANL' in df.columns:
        result['air_mask_left'] = df['AUAFMANL'].astype(float)
    if 'AUAFMANR' in df.columns:
        result['air_mask_right'] = df['AUAFMANR'].astype(float)

    return result


def _compute_pta(row, ear='right'):
    """Compute PTA-4 (average of 500, 1000, 2000, 4000 Hz) for one ear."""
    cols = [f'threshold_{ear}_500', f'threshold_{ear}_1000',
            f'threshold_{ear}_2000', f'threshold_{ear}_4000']
    vals = [row.get(c, np.nan) for c in cols]
    return np.nanmean(vals)


def nhanes_demo(df_clean=None, path=None):
    """Compute and print quick summary statistics for NHANES audiometry
    data.

    Parameters
    ----------
    df_clean : pd.DataFrame, optional
        Pre-cleaned DataFrame from extract_audiometry().
    path : str or Path, optional
        If df_clean is None, load from this path first.

    Returns
    -------
    dict
        Summary statistics dict with keys:
        n_subjects, n_with_pta, pta_mean, pta_std, pta_quartiles,
        who_categories, etc.
    """
    if df_clean is None:
        if path is None:
            raise ValueError("Either df_clean or path must be provided.")
        df_clean = extract_audiometry(load_nhanes(path))

    # Compute PTA-4 for both ears
    right_pta = df_clean.apply(
        lambda r: _compute_pta(r, 'right'), axis=1)
    left_pta = df_clean.apply(
        lambda r: _compute_pta(r, 'left'), axis=1)

    # Use worse-ear PTA for overall classification
    worse_pta = np.maximum(right_pta, left_pta)

    n_total = len(df_clean)
    n_with_data = int(np.sum(~np.isnan(worse_pta)))

    # WHO categories
    def who_category(pta_val):
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

    categories = [who_category(v) for v in worse_pta]
    cat_counts = pd.Series(categories).value_counts()

    # Slope (4kHz - 500Hz) for right ear
    slope_right = (df_clean['threshold_right_4000']
                   - df_clean['threshold_right_500'])
    slope_left = (df_clean['threshold_left_4000']
                  - df_clean['threshold_left_500'])

    # Asymmetry
    freq_cols = [500, 1000, 2000, 3000, 4000, 6000, 8000]
    asym = pd.DataFrame()
    for f in freq_cols:
        col_r = f'threshold_right_{f}'
        col_l = f'threshold_left_{f}'
        if col_r in df_clean.columns and col_l in df_clean.columns:
            asym[f'asym_{f}'] = np.abs(
                df_clean[col_r] - df_clean[col_l])
    max_asym = asym.max(axis=1, skipna=True)

    result = {
        'n_subjects': n_total,
        'n_with_pta': n_with_data,
        'n_missing_pta': n_total - n_with_data,
        'right_pta_mean': float(np.nanmean(right_pta)),
        'right_pta_std': float(np.nanstd(right_pta)),
        'left_pta_mean': float(np.nanmean(left_pta)),
        'left_pta_std': float(np.nanstd(left_pta)),
        'worse_pta_mean': float(np.nanmean(worse_pta)),
        'worse_pta_std': float(np.nanstd(worse_pta)),
        'worse_pta_quartiles': [
            float(np.nanpercentile(worse_pta, 25)),
            float(np.nanpercentile(worse_pta, 50)),
            float(np.nanpercentile(worse_pta, 75)),
        ],
        'worse_pta_min': float(np.nanmin(worse_pta)),
        'worse_pta_max': float(np.nanmax(worse_pta)),
        'who_categories': cat_counts.to_dict(),
        'slope_right_mean': float(np.nanmean(slope_right)),
        'slope_left_mean': float(np.nanmean(slope_left)),
        'asymmetry_mean': float(np.nanmean(max_asym)),
        'asymmetry_max': float(np.nanmax(max_asym)),
        'asymmetry_p95': float(np.nanpercentile(max_asym, 95)),
    }

    return result
