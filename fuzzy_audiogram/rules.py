"""
rules.py — Expanded fuzzy rule base for audiogram classification.

Provides factory functions that build Mamdani-type fuzzy rules
for severity, configuration, asymmetry, and mixed-loss presentations.
Each function returns a list of skfuzzy.control.Rule objects ready
to be added to a ControlSystem.

Rule count target: ~48 rules (12 severity, 14 configuration,
12 asymmetry, 10 mixed-loss).
"""

from skfuzzy import control as ctrl


def get_severity_rules(threshold, severity):
    """
    Build severity classification rules based on threshold category.

    Parameters
    ----------
    threshold : ctrl.Antecedent
        Antecedent with membership functions: normal, mild, moderate,
        moderately_severe, severe, profound.
    severity : ctrl.Consequent
        Consequent with matching membership functions.

    Returns
    -------
    list[ctrl.Rule]
        12 rules covering:
        - 6 direct / primary severity assignments
        - 6 blended / overlap-zone rules
    """
    rules = []

    # --- Primary severity rules (6) ---
    rules.append(ctrl.Rule(threshold['normal'], severity['normal']))
    rules.append(ctrl.Rule(threshold['mild'], severity['mild']))
    rules.append(ctrl.Rule(threshold['moderate'], severity['moderate']))
    rules.append(ctrl.Rule(threshold['moderately_severe'], severity['moderately_severe']))
    rules.append(ctrl.Rule(threshold['severe'], severity['severe']))
    rules.append(ctrl.Rule(threshold['profound'], severity['profound']))

    # --- Blended / overlap-zone rules (6) ---
    # When both normal and mild fire, the result sits between them
    rules.append(ctrl.Rule(
        threshold['normal'] & threshold['mild'],
        severity['mild'],
    ))
    rules.append(ctrl.Rule(
        threshold['mild'] & threshold['moderate'],
        severity['moderate'],
    ))
    rules.append(ctrl.Rule(
        threshold['moderate'] & threshold['moderately_severe'],
        severity['moderately_severe'],
    ))
    rules.append(ctrl.Rule(
        threshold['moderately_severe'] & threshold['severe'],
        severity['severe'],
    ))
    rules.append(ctrl.Rule(
        threshold['severe'] & threshold['profound'],
        severity['severe'],
    ))
    rules.append(ctrl.Rule(
        threshold['normal'] & threshold['mild'] & threshold['moderate'],
        severity['moderate'],
    ))

    return rules


def get_configuration_rules(slope, notch, audiogram_shape, severity=None):
    """
    Build configuration / shape classification rules.

    Parameters
    ----------
    slope : ctrl.Antecedent
        Antecedent with memberships: rising, flat, gently_sloping,
        steeply_sloping, precipitous.
    notch : ctrl.Antecedent
        Antecedent with memberships: no_notch, shallow_notch, deep_notch.
    audiogram_shape : ctrl.Consequent
        Consequent with memberships: normal, flat, sloping, notched,
        precipitous, rising.
    severity : ctrl.Consequent, optional
        Required for the normal-shape rule that also references severity.

    Returns
    -------
    list[ctrl.Rule]
        14 rules covering all major configuration patterns.
    """
    rules = []

    # --- Sloping patterns (6) ---
    rules.append(ctrl.Rule(
        slope['flat'] & notch['no_notch'],
        audiogram_shape['flat'],
    ))
    rules.append(ctrl.Rule(
        slope['gently_sloping'] & notch['no_notch'],
        audiogram_shape['sloping'],
    ))
    rules.append(ctrl.Rule(
        slope['steeply_sloping'] & notch['no_notch'],
        audiogram_shape['sloping'],
    ))
    rules.append(ctrl.Rule(
        slope['precipitous'] & notch['no_notch'],
        audiogram_shape['precipitous'],
    ))
    rules.append(ctrl.Rule(
        slope['rising'] & notch['no_notch'],
        audiogram_shape['rising'],
    ))
    # --- Normal pattern: flat + not notched + normal thresholds ---
    if severity is not None:
        rules.append(ctrl.Rule(
            slope['flat'] & notch['no_notch'] & severity['normal'],
            audiogram_shape['normal'],
        ))
    else:
        rules.append(ctrl.Rule(
            slope['flat'] & notch['no_notch'],
            audiogram_shape['normal'],
        ))

    # --- Notch patterns (4) ---
    rules.append(ctrl.Rule(
        notch['shallow_notch'] & slope['flat'],
        audiogram_shape['notched'],
    ))
    rules.append(ctrl.Rule(
        notch['deep_notch'] & slope['flat'],
        audiogram_shape['notched'],
    ))
    rules.append(ctrl.Rule(
        notch['shallow_notch'] & slope['gently_sloping'],
        audiogram_shape['notched'],
    ))
    rules.append(ctrl.Rule(
        notch['deep_notch'] & slope['steeply_sloping'],
        audiogram_shape['notched'],
    ))

    # --- Mixed / edge patterns (4) ---
    rules.append(ctrl.Rule(
        slope['rising'] & notch['deep_notch'],
        audiogram_shape['rising'],
    ))
    rules.append(ctrl.Rule(
        slope['precipitous'] & notch['shallow_notch'],
        audiogram_shape['precipitous'],
    ))
    rules.append(ctrl.Rule(
        slope['gently_sloping'] & notch['deep_notch'],
        audiogram_shape['notched'],
    ))
    rules.append(ctrl.Rule(
        slope['steeply_sloping'] & notch['deep_notch'],
        audiogram_shape['precipitous'],
    ))

    return rules


def get_asymmetry_rules(asymmetry, severity):
    """
    Build rules that upgrade severity based on inter-aural asymmetry.

    Parameters
    ----------
    asymmetry : ctrl.Antecedent
        Antecedent with memberships: symmetric, mildly_asymmetric,
        moderately_asymmetric, severely_asymmetric.
    severity : ctrl.Consequent
        Consequent severity output.

    Returns
    -------
    list[ctrl.Rule]
        12 rules: symmetric → no upgrade, increasing asymmetry
        shifts severity upward.
    """
    rules = []

    # --- Symmetric: no effect on severity ---
    rules.append(ctrl.Rule(
        asymmetry['symmetric'],
        severity['normal'],
    ))

    # --- Mild asymmetry: mild effect ---
    rules.append(ctrl.Rule(
        asymmetry['mildly_asymmetric'] & severity['normal'],
        severity['mild'],
    ))
    rules.append(ctrl.Rule(
        asymmetry['mildly_asymmetric'] & severity['mild'],
        severity['moderate'],
    ))

    # --- Moderate asymmetry: moderate upgrade ---
    rules.append(ctrl.Rule(
        asymmetry['moderately_asymmetric'] & severity['normal'],
        severity['moderate'],
    ))
    rules.append(ctrl.Rule(
        asymmetry['moderately_asymmetric'] & severity['mild'],
        severity['moderately_severe'],
    ))
    rules.append(ctrl.Rule(
        asymmetry['moderately_asymmetric'] & severity['moderate'],
        severity['severe'],
    ))
    rules.append(ctrl.Rule(
        asymmetry['moderately_asymmetric'] & severity['moderately_severe'],
        severity['severe'],
    ))

    # --- Severe asymmetry: significant upgrade ---
    rules.append(ctrl.Rule(
        asymmetry['severely_asymmetric'] & severity['normal'],
        severity['moderately_severe'],
    ))
    rules.append(ctrl.Rule(
        asymmetry['severely_asymmetric'] & severity['mild'],
        severity['severe'],
    ))
    rules.append(ctrl.Rule(
        asymmetry['severely_asymmetric'] & severity['moderate'],
        severity['severe'],
    ))
    rules.append(ctrl.Rule(
        asymmetry['severely_asymmetric'] & severity['moderately_severe'],
        severity['profound'],
    ))
    rules.append(ctrl.Rule(
        asymmetry['severely_asymmetric'] & severity['severe'],
        severity['profound'],
    ))

    return rules


def get_mixed_loss_rules(threshold, slope, asymmetry, severity):
    """
    Build rules for mixed / complex loss presentations where multiple
    inputs interact non-additively.

    Parameters
    ----------
    threshold : ctrl.Antecedent
    slope : ctrl.Antecedent
    asymmetry : ctrl.Antecedent
    severity : ctrl.Consequent

    Returns
    -------
    list[ctrl.Rule]
        10 rules for mixed presentations.
    """
    rules = []

    # --- Steep slope + moderate threshold → upgrade ---
    rules.append(ctrl.Rule(
        slope['precipitous'] & threshold['moderate'],
        severity['severe'],
    ))
    rules.append(ctrl.Rule(
        slope['precipitous'] & threshold['mild'],
        severity['moderately_severe'],
    ))

    # --- Steep slope + severe asymmetry → profound ---
    rules.append(ctrl.Rule(
        slope['steeply_sloping'] & asymmetry['severely_asymmetric'] & threshold['moderate'],
        severity['severe'],
    ))
    rules.append(ctrl.Rule(
        slope['precipitous'] & asymmetry['severely_asymmetric'],
        severity['profound'],
    ))

    # --- Normal thresholds + steep slope → mild (configuration-driven) ---
    rules.append(ctrl.Rule(
        threshold['normal'] & slope['steeply_sloping'],
        severity['mild'],
    ))
    rules.append(ctrl.Rule(
        threshold['normal'] & slope['precipitous'],
        severity['moderate'],
    ))

    # --- Normal threshold + moderate asymmetry → upgrade ---
    rules.append(ctrl.Rule(
        threshold['normal'] & asymmetry['moderately_asymmetric'],
        severity['mild'],
    ))

    # --- Rising slope + asymmetry ---
    rules.append(ctrl.Rule(
        slope['rising'] & asymmetry['moderately_asymmetric'],
        severity['moderate'],
    ))
    rules.append(ctrl.Rule(
        slope['rising'] & asymmetry['severely_asymmetric'],
        severity['moderately_severe'],
    ))

    # --- Flat slope + severe asymmetry ---
    rules.append(ctrl.Rule(
        slope['flat'] & asymmetry['severely_asymmetric'] & threshold['mild'],
        severity['moderate'],
    ))

    return rules


def get_all_rules(threshold, slope, notch, asymmetry, severity, audiogram_shape):
    """
    Combine all rule groups into a single flat rule list.

    Parameters
    ----------
    threshold : ctrl.Antecedent
    slope : ctrl.Antecedent
    notch : ctrl.Antecedent
    asymmetry : ctrl.Antecedent
    severity : ctrl.Consequent
    audiogram_shape : ctrl.Consequent

    Returns
    -------
    list[ctrl.Rule]
        All ~48 rules combined.
    """
    rules = []
    rules.extend(get_severity_rules(threshold, severity))
    rules.extend(get_configuration_rules(slope, notch, audiogram_shape, severity))
    rules.extend(get_asymmetry_rules(asymmetry, severity))
    rules.extend(get_mixed_loss_rules(threshold, slope, asymmetry, severity))
    return rules
