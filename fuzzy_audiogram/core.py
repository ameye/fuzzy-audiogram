"""
core.py — Main fuzzy inference system for audiogram classification.

Provides the core FIS builder, feature extraction from raw thresholds,
full classification pipeline, fuzzy-vs-crisp comparison, and
demonstration cases.
"""

import warnings
from pathlib import Path

import numpy as np
import pandas as pd


# =========================================================================
# 1. UNIVERSE CREATION
# =========================================================================

FREQUENCIES_HZ = [250, 500, 1000, 2000, 3000, 4000, 6000, 8000]
"""Standard audiometric frequencies used by the framework."""

SEVERITY_LABELS = ['normal', 'mild', 'moderate', 'moderately_severe',
                   'severe', 'profound']
SLOPE_LABELS = ['rising', 'flat', 'gently_sloping', 'steeply_sloping',
                'precipitous']
NOTCH_LABELS = ['no_notch', 'shallow_notch', 'deep_notch']
ASYMMETRY_LABELS = ['symmetric', 'mildly_asymmetric',
                     'moderately_asymmetric', 'severely_asymmetric']

SEVERITY_LABELS_HUMAN = ['Normal', 'Mild', 'Moderate', 'Moderately Severe',
                         'Severe', 'Profound']
SLOPE_LABELS_HUMAN = ['Rising', 'Flat', 'Gently Sloping', 'Steeply Sloping',
                      'Precipitous']
CONFIG_LABELS_HUMAN = ['Normal', 'Flat', 'Sloping', 'Notched',
                       'Precipitous', 'Rising']

# Membership function parameters (trapezoidal [a, b, c, d])
SEVERITY_MF_PARAMS = {
    'normal':           [0, 0, 20, 30],
    'mild':             [20, 26, 35, 45],
    'moderate':         [35, 41, 50, 60],
    'moderately_severe': [50, 56, 65, 75],
    'severe':           [65, 71, 85, 95],
    'profound':         [85, 91, 120, 120],
}

SLOPE_MF_PARAMS = {
    'rising':           [-40, -40, -15, -3],
    'flat':             [-8, -3, 8, 12],
    'gently_sloping':   [5, 10, 20, 28],
    'steeply_sloping':  [22, 28, 40, 50],
    'precipitous':      [40, 48, 80, 80],
}

NOTCH_MF_PARAMS = {
    'no_notch':         [0, 0, 5, 10],
    'shallow_notch':    [5, 10, 18, 22],
    'deep_notch':       [18, 25, 50, 50],
}

ASYMMETRY_MF_PARAMS = {
    'symmetric':               [0, 0, 10, 18],
    'mildly_asymmetric':       [12, 18, 25, 32],
    'moderately_asymmetric':   [25, 32, 40, 48],
    'severely_asymmetric':     [40, 48, 60, 60],
}

SEVERITY_OUTPUT_PARAMS = {
    'normal':           [0, 0, 10, 25],
    'mild':             [15, 25, 35, 45],
    'moderate':         [35, 45, 55, 65],
    'moderately_severe': [55, 60, 70, 78],
    'severe':           [70, 78, 88, 95],
    'profound':         [88, 95, 100, 100],
}

SHAPE_OUTPUT_PARAMS = {
    'normal':           [0, 0, 10, 20],
    'flat':             [10, 18, 30, 40],
    'sloping':          [30, 40, 55, 65],
    'notched':          [55, 62, 72, 80],
    'precipitous':      [75, 82, 90, 95],
    'rising':           [88, 93, 100, 100],
}


def create_severity_universe():
    """Create the universe of discourse for hearing threshold (0-120 dB HL).

    Returns
    -------
    np.ndarray
        Array from 0 to 120 inclusive (step 1).
    """
    return np.arange(0, 121, 1)


def create_slope_universe():
    """Create the universe of discourse for audiogram slope.

    Returns
    -------
    np.ndarray
        Array from -40 to 80 inclusive (step 1).
    """
    return np.arange(-40, 81, 1)


def create_asymmetry_universe():
    """Create the universe of discourse for inter-aural asymmetry.

    Returns
    -------
    np.ndarray
        Array from 0 to 60 inclusive (step 1).
    """
    return np.arange(0, 61, 1)


# =========================================================================
# 2. FUZZY INFERENCE SYSTEM BUILDER
# =========================================================================


def build_audiogram_fis():
    """Build the full Mamdani fuzzy inference system for audiogram
    interpretation.

    Constructs input/output universes, attaches membership functions
    using the parameters defined in module constants, and assembles
    the rule base from :mod:`fuzzy_audiogram.rules`.

    Returns
    -------
    tuple
        (system, simulation, threshold_ant, slope_ant, notch_ant,
         asym_ant, severity_con, shape_con)
        - system : ctrl.ControlSystem
        - simulation : ctrl.ControlSystemSimulation
        - threshold_ant : ctrl.Antecedent
        - slope_ant : ctrl.Antecedent
        - notch_ant : ctrl.Antecedent
        - asym_ant : ctrl.Antecedent
        - severity_con : ctrl.Consequent
        - shape_con : ctrl.Consequent
    """
    import skfuzzy as fuzz
    from skfuzzy import control as ctrl

    # --- Input universes ---
    threshold_ant = ctrl.Antecedent(np.arange(0, 121, 1), 'threshold')
    slope_ant = ctrl.Antecedent(np.arange(-40, 81, 1), 'slope')
    notch_ant = ctrl.Antecedent(np.arange(0, 51, 1), 'notch')
    asym_ant = ctrl.Antecedent(np.arange(0, 61, 1), 'asymmetry')

    # --- Output universes ---
    severity_con = ctrl.Consequent(np.arange(0, 101, 1), 'severity')
    shape_con = ctrl.Consequent(np.arange(0, 101, 1), 'audiogram_shape')

    # --- Attach membership functions (input) ---
    for cat, params in SEVERITY_MF_PARAMS.items():
        threshold_ant[cat] = fuzz.trapmf(threshold_ant.universe, params)

    for cat, params in SLOPE_MF_PARAMS.items():
        slope_ant[cat] = fuzz.trapmf(slope_ant.universe, params)

    for cat, params in NOTCH_MF_PARAMS.items():
        notch_ant[cat] = fuzz.trapmf(notch_ant.universe, params)

    for cat, params in ASYMMETRY_MF_PARAMS.items():
        asym_ant[cat] = fuzz.trapmf(asym_ant.universe, params)

    # --- Attach membership functions (output) ---
    for cat, params in SEVERITY_OUTPUT_PARAMS.items():
        severity_con[cat] = fuzz.trapmf(severity_con.universe, params)

    for cat, params in SHAPE_OUTPUT_PARAMS.items():
        shape_con[cat] = fuzz.trapmf(shape_con.universe, params)

    # --- Build rules ---
    from .rules import get_all_rules
    rules = get_all_rules(
        threshold_ant, slope_ant, notch_ant, asym_ant,
        severity_con, shape_con,
    )

    # --- Control system ---
    system = ctrl.ControlSystem(rules)
    simulation = ctrl.ControlSystemSimulation(system)

    return (system, simulation,
            threshold_ant, slope_ant, notch_ant, asym_ant,
            severity_con, shape_con)


# =========================================================================
# 3. FEATURE EXTRACTION
# =========================================================================


def compute_audiogram_features(thresholds_left, thresholds_right=None):
    """Compute features from raw audiogram thresholds for the fuzzy system.

    Extracts PTA, slope, notch depth, Carhart notch depth, and
    inter-aural asymmetry from threshold arrays.

    Parameters
    ----------
    thresholds_left : array-like
        Left ear thresholds at [250, 500, 1000, 2000, 3000, 4000,
        6000, 8000] Hz.
    thresholds_right : array-like, optional
        Right ear thresholds (same order).

    Returns
    -------
    dict
        Keys: pta, pta_low, pta_high, slope, notch_depth,
        carhart_depth, asymmetry, threshold_primary.
    """
    left = np.array(thresholds_left, dtype=float)

    # Pure Tone Average (PTA-4: 500, 1k, 2k, 4k) — indices 1, 2, 3, 5
    pta = np.nanmean([left[1], left[2], left[3], left[5]])

    # High-frequency PTA (2k, 4k, 6k, 8k)
    pta_high = np.nanmean([left[3], left[5], left[6], left[7]])

    # Low-frequency PTA (250, 500, 1k)
    pta_low = np.nanmean([left[0], left[1], left[2]])

    # Slope: dB change from 500 Hz to 4 kHz
    slope_raw = left[5] - left[1]

    # Notch depth at 4 kHz: dip relative to surrounding (2k & 8k)
    if not np.isnan(left[5]) and not np.isnan(left[3]) and not np.isnan(left[7]):
        expected = np.mean([left[3], left[7]])
        notch_depth = max(0, left[5] - expected)
    elif not np.isnan(left[5]) and not np.isnan(left[3]):
        expected = (left[3] + left[5]) / 2
        notch_depth = max(0, left[5] - expected) * 2
    else:
        notch_depth = 0.0

    # Carhart notch at 2 kHz (otosclerosis indicator)
    if (not np.isnan(left[2]) and not np.isnan(left[1])
            and not np.isnan(left[3])):
        carhart_depth = max(0, left[2] - np.mean([left[1], left[3]]))
    else:
        carhart_depth = 0.0

    # Asymmetry (max inter-aural difference)
    asymmetry_val = 0.0
    if thresholds_right is not None:
        right = np.array(thresholds_right, dtype=float)
        asymmetry_val = float(np.nanmax(np.abs(left - right)))

    return {
        'pta': float(pta),
        'pta_low': float(pta_low),
        'pta_high': float(pta_high),
        'slope': float(slope_raw),
        'notch_depth': float(notch_depth),
        'carhart_depth': float(carhart_depth),
        'asymmetry': float(asymmetry_val),
        'threshold_primary': float(pta),
    }


# =========================================================================
# 4. CLASSIFICATION
# =========================================================================


def _interpret_severity_score(score):
    """Map a continuous severity score (0-100) to a human label."""
    if score < 20:
        return 'Normal'
    elif score < 35:
        return 'Mild'
    elif score < 50:
        return 'Moderate'
    elif score < 65:
        return 'Moderately Severe'
    elif score < 85:
        return 'Severe'
    else:
        return 'Profound'


def _interpret_shape_score(score):
    """Map a continuous shape score (0-100) to a human label."""
    if score < 15:
        return 'Normal'
    elif score < 35:
        return 'Flat'
    elif score < 50:
        return 'Sloping'
    elif score < 65:
        return 'Notched'
    elif score < 82:
        return 'Precipitous'
    else:
        return 'Rising'


def classify_audiogram(thresholds_left, thresholds_right=None):
    """Run the full fuzzy classification pipeline on an audiogram.

    Parameters
    ----------
    thresholds_left : array-like
        8 values for [250, 500, 1k, 2k, 3k, 4k, 6k, 8k] Hz.
    thresholds_right : array-like, optional
        Right ear thresholds (same order).

    Returns
    -------
    dict
        Keys: fai_score, fai_label, configuration_score,
        configuration_label, pt4a, threshold_memberships,
        slope_memberships, features.
    """
    import skfuzzy as fuzz

    (_, sim, threshold_ant, slope_ant, _notch_ant, _asym_ant,
     _severity_con, _shape_con) = build_audiogram_fis()

    features = compute_audiogram_features(thresholds_left, thresholds_right)

    # Set crisp inputs
    sim.input['threshold'] = np.clip(features['threshold_primary'], 0, 120)
    sim.input['slope'] = np.clip(features['slope'], -40, 80)
    sim.input['notch'] = np.clip(features['notch_depth'], 0, 50)
    sim.input['asymmetry'] = np.clip(features['asymmetry'], 0, 60)

    # Compute FIS
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        sim.compute()

    severity_score = float(sim.output['severity'])
    shape_score = float(sim.output['audiogram_shape'])

    severity_label = _interpret_severity_score(severity_score)
    shape_label = _interpret_shape_score(shape_score)

    # Get membership degrees at the input point
    threshold_memberships = {}
    for cat in SEVERITY_LABELS:
        threshold_memberships[cat] = float(fuzz.interp_membership(
            threshold_ant.universe, threshold_ant[cat].mf,
            np.clip(features['threshold_primary'], 0, 120),
        ))

    slope_memberships = {}
    for cat in SLOPE_LABELS:
        slope_memberships[cat] = float(fuzz.interp_membership(
            slope_ant.universe, slope_ant[cat].mf,
            np.clip(features['slope'], -40, 80),
        ))

    return {
        'fai_score': round(severity_score, 2),
        'fai_label': severity_label,
        'configuration_score': round(shape_score, 2),
        'configuration_label': shape_label,
        'pt4a': round(features['pta'], 1),
        'threshold_memberships': threshold_memberships,
        'slope_memberships': slope_memberships,
        'features': features,
    }


# =========================================================================
# 5. FUZZY vs CRISP COMPARISON
# =========================================================================


def compare_fuzzy_vs_crisp(pta_values=None):
    """Systematically compare fuzzy vs crisp classification across a
    range of PTA values.

    Parameters
    ----------
    pta_values : list of float, optional
        PTA values to test. Defaults to a representative range
        around critical boundaries.

    Returns
    -------
    pd.DataFrame
        Columns: pta, crisp_label, fuzzy_label, fai_score,
        normal_mu, mild_mu, moderate_mu, mod_sev_mu, severe_mu,
        profound_mu.
    """
    from .validate import crisp_classify

    if pta_values is None:
        pta_values = [0, 10, 15, 20, 24, 25, 26, 27, 30, 35,
                      40, 41, 45, 50, 55, 56, 60, 65, 70, 71,
                      80, 85, 90, 91, 95, 100, 110, 120]

    rows = []
    for pta in pta_values:
        thresholds = [float(pta)] * 8
        result = classify_audiogram(thresholds)
        crisp = crisp_classify(pta)

        row = {
            'pta': pta,
            'crisp_label': crisp,
            'fuzzy_label': result['fai_label'],
            'fai_score': result['fai_score'],
        }
        for cat in SEVERITY_LABELS:
            row[f'{cat}_mu'] = result['threshold_memberships'][cat]
        rows.append(row)

    return pd.DataFrame(rows)


# =========================================================================
# 6. DEMONSTRATION CASES
# =========================================================================


def demo_cases():
    """Run the fuzzy classifier on 5 standard clinical cases and return
    the results as a dict.

    Cases
    -----
    1. Borderline Normal-Mild (PTA 26 dB)
    2. Noise-Induced Hearing Loss (4 kHz notch)
    3. Presbycusis (high-frequency sloping loss)
    4. Asymmetric sensorineural loss
    5. Otosclerosis (Carhart notch at 2 kHz)

    Returns
    -------
    dict
        Keys: 'borderline', 'noise_notch', 'presbycusis',
        'asymmetric', 'otosclerosis'.
        Each value is the dict returned by classify_audiogram.
    """
    # Case 1: Borderline Normal-Mild
    borderline = [20, 22, 25, 28, 30, 35, 28, 22]
    result1 = classify_audiogram(borderline)

    # Case 2: Noise-Induced Hearing Loss (Carhart notch at 4 kHz)
    noise_notch = [10, 10, 12, 20, 35, 50, 45, 30]
    result2 = classify_audiogram(noise_notch)

    # Case 3: Presbycusis (high-frequency sloping)
    presbycusis = [15, 20, 25, 35, 45, 55, 65, 70]
    result3 = classify_audiogram(presbycusis)

    # Case 4: Asymmetric loss
    left_ear = [15, 20, 25, 30, 35, 40, 35, 30]
    right_ear = [25, 35, 50, 60, 65, 70, 65, 55]
    result4 = classify_audiogram(left_ear, right_ear)

    # Case 5: Otosclerosis (Carhart notch at 2 kHz)
    otosclerosis = [30, 35, 50, 40, 45, 50, 55, 55]
    result5 = classify_audiogram(otosclerosis)

    return {
        'borderline': result1,
        'noise_notch': result2,
        'presbycusis': result3,
        'asymmetric': result4,
        'otosclerosis': result5,
    }
