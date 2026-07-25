"""
temporal.py — Temporal tracking and drift detection for serial
audiograms.

Provides functions to track the Fuzzy Audiometric Index (FAI) over
time, detect clinically significant drift, and monitor for
ototoxicity-related threshold shifts in fuzzy space.
"""

import warnings
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd


def FAI_trajectory(audiogram_series):
    """Compute FAI scores over time for a series of audiograms.

    Each audiogram is classified via the fuzzy system, and the
    resulting FAI (severity score) is recorded alongside sub-scores
    per frequency band.

    Parameters
    ----------
    audiogram_series : list of dict
        Serial audiogram data. Each dict must have keys:
        - 'date' : str or datetime
        - 'thresholds_left' : list of 8 floats [250..8000 Hz]
        - 'thresholds_right' : list of 8 floats, optional

    Returns
    -------
    pd.DataFrame
        Columns: date, fai_score, configuration_score, pt4a, slope,
        notch_depth, asymmetry.
        One row per audiogram in the series.
    """
    from .core import classify_audiogram, compute_audiogram_features

    records = []
    for entry in audiogram_series:
        date = entry.get('date', 'unknown')
        tl = entry['thresholds_left']
        tr = entry.get('thresholds_right')

        result = classify_audiogram(tl, tr)
        features = result['features']

        records.append({
            'date': date,
            'fai_score': result['fai_score'],
            'configuration_score': result['configuration_score'],
            'fai_label': result['fai_label'],
            'configuration_label': result['configuration_label'],
            'pt4a': result['pt4a'],
            'slope': features['slope'],
            'notch_depth': features['notch_depth'],
            'carhart_depth': features['carhart_depth'],
            'asymmetry': features['asymmetry'],
        })

    df = pd.DataFrame(records)
    if 'date' in df.columns:
        try:
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date').reset_index(drop=True)
        except (ValueError, TypeError):
            pass

    return df


def detect_fai_drift(fai_series, threshold=5.0):
    """Detect clinically significant drift in FAI scores over time.

    Compares each FAI score to a rolling baseline (first 2 values or
    running median of first 3).  Flags points where the absolute
    change exceeds the threshold.

    Parameters
    ----------
    fai_series : pd.Series or list of float
        FAI scores over time (chronological).
    threshold : float
        Minimum absolute change in FAI points to trigger an alert
        (default 5.0).

    Returns
    -------
    list of dict
        Alert records: each has keys index, fai, baseline, delta,
        direction ('worsening' or 'improving'), and severity.
        Empty list if no drift detected.
    """
    fai = np.array(fai_series, dtype=float)

    if len(fai) < 3:
        return []

    # Baseline = median of first 3 values
    baseline = float(np.median(fai[:3]))
    alerts = []

    for i in range(3, len(fai)):
        delta = fai[i] - baseline
        if abs(delta) >= threshold:
            direction = 'worsening' if delta > 0 else 'improving'
            pct_change = (delta / baseline * 100) if baseline != 0 else float('inf')

            # Severity of drift
            if abs(delta) >= 2 * threshold:
                drift_severity = 'critical'
            elif abs(delta) >= 1.5 * threshold:
                drift_severity = 'significant'
            else:
                drift_severity = 'notable'

            alerts.append({
                'index': int(i),
                'fai': float(fai[i]),
                'baseline': round(baseline, 2),
                'delta': round(delta, 2),
                'pct_change': round(pct_change, 1),
                'direction': direction,
                'severity': drift_severity,
            })

    return alerts


def ototoxicity_monitor(serial_audiograms, baseline_idx=0):
    """Monitor serial audiograms for ototoxicity-related threshold
    shifts using fuzzy classification.

    Implements a fuzzy adaptation of the ASHA ototoxicity monitoring
    criteria: flags significant threshold shifts when the fuzzy
    membership for severity categories changes materially.

    Parameters
    ----------
    serial_audiograms : list of dict
        Each dict has keys: date, thresholds_left, thresholds_right
        (optional).
    baseline_idx : int
        Index into serial_audiograms to use as baseline (default 0).

    Returns
    -------
    pd.DataFrame
        For each post-baseline audiogram, columns: date, fai_change,
        slope_change, notch_change, asymmetry_change, membership_shift,
        ototoxicity_flag (bool), asha_criteria summary.
    """
    from .core import classify_audiogram, compute_audiogram_features

    if len(serial_audiograms) < 2:
        return pd.DataFrame()

    # Baseline classification
    baseline = serial_audiograms[baseline_idx]
    tl_b = baseline['thresholds_left']
    tr_b = baseline.get('thresholds_right')
    base_result = classify_audiogram(tl_b, tr_b)
    base_features = base_result['features']
    base_memberships = base_result['threshold_memberships']

    records = []
    for i, entry in enumerate(serial_audiograms):
        if i == baseline_idx:
            continue

        date = entry.get('date', f'timepoint_{i}')
        tl = entry['thresholds_left']
        tr = entry.get('thresholds_right')

        result = classify_audiogram(tl, tr)
        features = result['features']
        memberships = result['threshold_memberships']

        # Compute changes
        fai_change = result['fai_score'] - base_result['fai_score']
        slope_change = features['slope'] - base_features['slope']
        notch_change = features['notch_depth'] - base_features['notch_depth']
        asym_change = features['asymmetry'] - base_features['asymmetry']

        # Membership shift: max absolute change in membership degree
        membership_shift = max(
            abs(memberships.get(c, 0) - base_memberships.get(c, 0))
            for c in base_memberships
        )

        # ASHA ototoxicity criteria (fuzzy-adapted):
        # - ≥20 dB decrease at any test frequency
        # - ≥10 dB decrease at adjacent frequencies
        # - Loss of response at 3 consecutive frequencies
        tl_now = np.array(tl, dtype=float)
        tl_base = np.array(tl_b, dtype=float)
        threshold_drops = tl_now - tl_base  # positive = worse

        freq_drop_20 = np.any(threshold_drops >= 20)
        freq_drop_10_adj = False
        for j in range(len(threshold_drops) - 1):
            if threshold_drops[j] >= 10 and threshold_drops[j + 1] >= 10:
                freq_drop_10_adj = True
                break

        asha_positive = freq_drop_20 or freq_drop_10_adj

        # Fuzzy ototoxicity: significant membership category shift
        # combined with FAI change
        fuzzy_positive = (
            membership_shift > 0.3
            and abs(fai_change) >= 5
        )

        ototoxicity_flag = asha_positive or fuzzy_positive

        records.append({
            'date': date,
            'index': i,
            'fai_change': round(fai_change, 2),
            'fai_current': result['fai_score'],
            'fai_baseline': base_result['fai_score'],
            'slope_change': round(slope_change, 2),
            'notch_change': round(notch_change, 2),
            'asymmetry_change': round(asym_change, 2),
            'membership_shift': round(membership_shift, 3),
            'asha_criteria_20db_drop': freq_drop_20,
            'asha_criteria_10db_adjacent': freq_drop_10_adj,
            'fuzzy_criteria_met': fuzzy_positive,
            'ototoxicity_flag': ototoxicity_flag,
        })

    df_result = pd.DataFrame(records)
    if 'date' in df_result.columns:
        try:
            df_result['date'] = pd.to_datetime(df_result['date'])
            df_result = df_result.sort_values('date').reset_index(drop=True)
        except (ValueError, TypeError):
            pass

    return df_result
