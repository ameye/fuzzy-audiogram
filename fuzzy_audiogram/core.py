"""
core.py — Main fuzzy inference system for audiogram classification.

Provides the core FIS builder, feature extraction from raw thresholds,
full classification pipeline, fuzzy-vs-crisp comparison, and
demonstration cases.

Severity membership functions
-----------------------------
The six severity memberships are a Ruspini partition: at every threshold in
0-120 dB HL their sum is exactly 1.0, so no threshold is unclassified and none
is double counted (``tests/test_ruspini_continuous.py`` sweeps the axis and
``tests/test_published_classifier.py`` checks the deployed constants against
it). The parameters in :data:`SEVERITY_MF_PARAMS` are the ones the participant
level pipeline fitted on the combined NHANES training set and wrote to
``data/output_participant/metrics_participant.json``; every number in the
manuscript comes from that run.

The set previously deployed here --- ``data/output/params_combined.json`` ---
fitted each trapezoid's feet independently (``P5 - 2`` to ``P95 + 2``) and was
therefore *not* a partition: six memberships summed to 0.558 at 26 dB HL, to
0.175 at the worst point, and to zero at both universe endpoints. It is
retained in ``data/output/params_combined.json`` only as the superseded
configuration, and no reported metric is derived from it.

Unfired consequents
-------------------
scikit-fuzzy evaluates every rule, so a consequent records a membership
value for each of its terms; when no rule has any antecedent truth for
that consequent, every recorded value is 0.0 and the defuzzifier has no
area to integrate. ``ControlSystemSimulation.compute`` runs in lenient
mode and simply omits the key from ``sim.output`` rather than returning a
number, which is why an unconditional ``sim.output['severity']`` raised
``KeyError`` on 20 of 410 OAUTHC ears.

Three states are therefore kept apart explicitly (:data:`OUTPUT_DEFUZZIFIED`,
:data:`OUTPUT_UNFIRED`, :data:`OUTPUT_EMPTY`) instead of being collapsed
into one missing value:

* ``defuzzified``: at least one rule had support and the consequent
  defuzzified to a finite number. Every ear that worked before the fix
  stays on this path with an identical score and label.
* ``unfired``: no rule targeting the consequent had any antecedent truth
  (maximum rule support 0.0). This is a coverage gap in the rule base,
  not a data defect.
* ``empty_membership``: a rule had positive support but the aggregated
  consequent membership function was empty (zero area), so no crisp value
  exists. Kept apart from ``unfired`` because the cause and the remedy
  differ.

Policy for a consequent with no defuzzified value, recorded here and in
``oatuhc_eda/FAI_FIX_REPORT.md``:

* ``severity`` falls back to the crisp WHO/Clark grade for that ear
  (``fai_label_source = 'crisp_who_fallback'``, ``fai_score = None``).
  The observed severity gap is PTA-4 of exactly 120 dB HL, above the
  support of every severity membership function, where the crisp grade is
  unambiguous; an index that refuses to grade a 120 dB loss is not
  deployable. The fallback is flagged so that agreement analyses can
  report with and without it, because against a crisp reference it is
  agreement by construction.
* ``audiogram_shape`` returns ``configuration_label = 'Undetermined'``
  (``configuration_score = None``, ``configuration_source =
  'undetermined'``). The protocol defines no crisp standard for
  configuration, so substituting one would manufacture a label.

Membership functions, rule weights, thresholds and the rule base are
unchanged: the published index is the same index, and no ear that
previously produced a value produces a different one.
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

# Membership function parameters (trapezoidal [a, b, c, d]).
#
# These are the Ruspini-partition parameters fitted on the combined NHANES
# training set by scripts/pipeline_participant.py and committed to
# data/output_participant/metrics_participant.json (mf_params). They are the
# parameters behind every published table: at 26 dB HL they give Normal
# mu = 0.294, Mild mu = 0.706 and an FAI of 24.99.
#
# Construction (fuzzy_audiogram.ruspini): each trapezoid's feet are tied to its
# neighbours' cores (a_i = c_{i-1}, d_i = b_{i+1}), so adjacent shoulders are
# complementary ramps. The six memberships therefore sum to exactly 1.0 at every
# point of 0-120 dB HL, including both endpoints: the bottom left foot and the
# top right foot are padded 0.5 dB beyond the universe so the trapezoid is still
# non-zero at 0 and 120. The minimum transition width was set to 10 dB, so every
# graded band is at least twice the +/-5 dB test-retest variability of pure-tone
# audiometry rather than the 2 dB the superseded independent fit produced.
#
# This is deliberately NOT the same classifier as the superseded set in
# data/output/params_combined.json (independent P5-2/P95+2 feet, six
# memberships summing to 0.558 at 26 dB, 0.175 at the worst point, zero at both
# endpoints). That set reproduced the old Table 4 but was not a partition.
SEVERITY_MF_PARAMS = {
    'normal':            [-0.5, 0.0, 16.4, 30.0],
    'mild':              [16.4, 30.0, 35.4, 45.4],
    'moderate':          [35.4, 45.4, 52.1, 62.1],
    'moderately_severe': [52.1, 62.1, 66.1, 76.1],
    'severe':            [66.1, 76.1, 85.0, 95.9],
    'profound':          [85.0, 95.9, 120.0, 120.5],
}

# FAI-to-label cut points, calibrated on the training set by maximising
# quadratic-weighted kappa against the WHO PTA-4 grade. From the same run
# (metrics_participant.json, label_thresholds). The search starts from these
# values, so the deployed constants and the pipeline's fallback are one
# definition rather than two copies.
SEVERITY_LABEL_THRESHOLDS = [24.6, 48.2, 57.3, 74.0, 85.8]

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

# Referral output: asymmetry drives a medical referral recommendation rather
# than altering the severity grading. Universes are on the same 0-100 scale as
# the other consequents for consistency.
REFERRAL_OUTPUT_PARAMS = {
    'none':      [0, 0, 10, 25],
    'routine':   [15, 25, 45, 55],
    'expedited': [45, 55, 75, 85],
    'urgent':    [75, 88, 100, 100],
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


def build_audiogram_fis(single_ear=False):
    """Build the full Mamdani fuzzy inference system for audiogram
    interpretation.

    Constructs input/output universes, attaches membership functions
    using the parameters defined in module constants, and assembles
    the rule base from :mod:`fuzzy_audiogram.rules`.

    Parameters
    ----------
    single_ear : bool, optional
        If True, omit the ``asymmetry[symmetric] -> severity[normal]``
        anchor rule. In single-ear validation the asymmetry input is always
        0.0, so that rule would fire at full strength for every ear and
        compress the FAI scale (see :func:`rules.get_asymmetry_rules`).

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
    referral_con = ctrl.Consequent(np.arange(0, 101, 1), 'referral')

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

    for cat, params in REFERRAL_OUTPUT_PARAMS.items():
        referral_con[cat] = fuzz.trapmf(referral_con.universe, params)

    # --- Build rules ---
    from .rules import get_all_rules
    rules = get_all_rules(
        threshold_ant, slope_ant, notch_ant, asym_ant,
        severity_con, shape_con,
        referral=referral_con,
        single_ear=single_ear,
    )

    # --- Control system ---
    system = ctrl.ControlSystem(rules)
    simulation = ctrl.ControlSystemSimulation(system)

    return (system, simulation,
            threshold_ant, slope_ant, notch_ant, asym_ant,
            severity_con, shape_con, referral_con)


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
    th = SEVERITY_LABEL_THRESHOLDS
    if score < th[0]:
        return 'Normal'
    elif score < th[1]:
        return 'Mild'
    elif score < th[2]:
        return 'Moderate'
    elif score < th[3]:
        return 'Moderately Severe'
    elif score < th[4]:
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


# Status of one consequent after a compute. Exactly one applies per call.
OUTPUT_DEFUZZIFIED = 'defuzzified'
"""A rule had support and the consequent defuzzified to a finite value."""

OUTPUT_UNFIRED = 'unfired'
"""No rule targeting the consequent had any antecedent truth (support 0.0)."""

OUTPUT_EMPTY = 'empty_membership'
"""A rule had support but the aggregated membership function had zero area."""

UNDETERMINED_SHAPE_LABEL = 'Undetermined'
"""Configuration label returned when the shape consequent has no crisp value."""


def _consequent_support(sim, consequent):
    """Maximum antecedent truth over the rules that target ``consequent``.

    scikit-fuzzy runs ``compute_rule`` for every rule, so an antecedent
    aggregate of 0.0 is indistinguishable from "no rule" if only the
    consequent term memberships are inspected: both leave a 0.0 behind.
    The rule firing strength is the quantity that separates them.
    """
    support = 0.0
    for rule in sim.ctrl.rules:
        for weighted in rule.consequent:
            if weighted.term.parent.label == consequent.label:
                firing = rule.aggregate_firing[sim]
                if firing is not None and float(firing) > support:
                    support = float(firing)
    return support


def _consequent_status(sim, consequent):
    """Classify one consequent after ``compute()``.

    Returns
    -------
    tuple
        (status, value, support) with status one of :data:`OUTPUT_DEFUZZIFIED`,
        :data:`OUTPUT_UNFIRED`, :data:`OUTPUT_EMPTY`; value float or None.
    """
    support = _consequent_support(sim, consequent)
    value = sim.output.get(consequent.label)
    if value is not None:
        value = float(value)
        if np.isfinite(value):
            return OUTPUT_DEFUZZIFIED, value, support
    status = OUTPUT_EMPTY if support > 0.0 else OUTPUT_UNFIRED
    return status, None, support


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
        Keys: fai_score, fai_label, fai_label_source, configuration_score,
        configuration_label, configuration_source, unfired_consequents,
        n_unfired_consequents, outputs, pt4a, threshold_memberships,
        slope_memberships, features.

        ``fai_score`` is None when the severity consequent has no crisp
        value; ``fai_label`` is then the crisp WHO/Clark fallback and
        ``fai_label_source`` says so. ``configuration_label`` is
        ``'Undetermined'`` with ``configuration_score`` None when the
        shape consequent has no crisp value. ``unfired_consequents``
        lists every consequent without a defuzzified value, so a caller
        can count how many went unfired without re-running inference.
    """
    import skfuzzy as fuzz

    # Single-ear mode: when only one ear is provided, the asymmetry input is
    # 0.0. Asymmetry feeds the referral consequent only, so the severity and
    # shape outputs are identical either way and the rule count is 42 in both
    # modes. The flag is kept so callers stay explicit about which mode they
    # are in.
    single_ear = thresholds_right is None
    (_, sim, threshold_ant, slope_ant, _notch_ant, _asym_ant,
     severity_con, shape_con, referral_con) = build_audiogram_fis(
        single_ear=single_ear)

    features = compute_audiogram_features(thresholds_left, thresholds_right)

    # Clear any state left on the object before reuse. Each call builds a
    # fresh system, so this is normally a no-op; it makes a caller-supplied
    # or cached simulation safe, because scikit-fuzzy only clears the
    # consequent terms of the first rule it evaluates and would otherwise
    # carry a previous ear's membership values forward.
    sim.reset()

    # Set crisp inputs
    sim.input['threshold'] = np.clip(features['threshold_primary'], 0, 120)
    sim.input['slope'] = np.clip(features['slope'], -40, 80)
    sim.input['notch'] = np.clip(features['notch_depth'], 0, 50)
    sim.input['asymmetry'] = np.clip(features['asymmetry'], 0, 60)

    # Compute FIS
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        sim.compute()

    # A consequent with no rule support is absent from sim.output; read each
    # one through its status rather than indexing the dict.
    outputs = {}
    for consequent in (severity_con, shape_con, referral_con):
        status, value, support = _consequent_status(sim, consequent)
        outputs[consequent.label] = {'status': status, 'value': value,
                                     'rule_support': round(support, 6)}

    severity = outputs['severity']
    if severity['status'] == OUTPUT_DEFUZZIFIED:
        severity_label = _interpret_severity_score(severity['value'])
        severity_source = 'fuzzy'
    else:
        # No rule produced a value: fall back to the crisp WHO/Clark grade.
        from .validate import crisp_classify
        severity_label = crisp_classify(features['pta'])
        severity_source = 'crisp_who_fallback'

    shape = outputs['audiogram_shape']
    if shape['status'] == OUTPUT_DEFUZZIFIED:
        shape_label = _interpret_shape_score(shape['value'])
        shape_source = 'fuzzy'
    else:
        shape_label = UNDETERMINED_SHAPE_LABEL
        shape_source = 'undetermined'

    unfired = [label for label, out in outputs.items()
               if out['status'] != OUTPUT_DEFUZZIFIED]

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
        'fai_score': (round(severity['value'], 2)
                      if severity['value'] is not None else None),
        'fai_label': severity_label,
        'fai_label_source': severity_source,
        'configuration_score': (round(shape['value'], 2)
                                if shape['value'] is not None else None),
        'configuration_label': shape_label,
        'configuration_source': shape_source,
        'unfired_consequents': unfired,
        'n_unfired_consequents': len(unfired),
        'outputs': outputs,
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
