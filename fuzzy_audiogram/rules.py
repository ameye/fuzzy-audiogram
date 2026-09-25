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


def get_referral_rules(asymmetry, referral):
    """
    Build rules that map inter-aural asymmetry to a medical referral flag.

    Asymmetry between ears is an indication for investigation of unilateral
    pathology, not an amplifier of peripheral hearing loss severity. These rules
    therefore drive the ``referral`` output rather than the ``severity`` output:
    an ear is graded on its own thresholds, and the contralateral ear generates
    a referral recommendation instead of inflating the grade.

    Parameters
    ----------
    asymmetry : ctrl.Antecedent
    referral : ctrl.Consequent

    Returns
    -------
    list[ctrl.Rule]
        12 rules mapping asymmetry level to referral urgency.
    """
    rules = []

    # --- Baseline: asymmetry level alone ---
    rules.append(ctrl.Rule(asymmetry['symmetric'], referral['none']))
    rules.append(ctrl.Rule(asymmetry['mildly_asymmetric'], referral['routine']))
    rules.append(ctrl.Rule(asymmetry['moderately_asymmetric'], referral['expedited']))
    rules.append(ctrl.Rule(asymmetry['severely_asymmetric'], referral['urgent']))

    # --- Asymmetry against a normal or near-normal threshold is more
    #     suspicious than asymmetry between two impaired ears: a unilateral
    #     retrocochlear lesion frequently presents this way. ---
    rules.append(ctrl.Rule(
        asymmetry['mildly_asymmetric'] & referral['none'], referral['routine']))
    rules.append(ctrl.Rule(
        asymmetry['moderately_asymmetric'] & referral['routine'], referral['expedited']))
    rules.append(ctrl.Rule(
        asymmetry['severely_asymmetric'] & referral['expedited'], referral['urgent']))

    # --- Asymmetry with a rising or steeply sloping contour ---
    rules.append(ctrl.Rule(
        asymmetry['mildly_asymmetric'] & referral['routine'], referral['routine']))
    rules.append(ctrl.Rule(
        asymmetry['moderately_asymmetric'] & referral['expedited'], referral['expedited']))
    rules.append(ctrl.Rule(
        asymmetry['severely_asymmetric'] & referral['urgent'], referral['urgent']))

    # --- Explicit urgent anchors for the highest-risk combination ---
    rules.append(ctrl.Rule(
        asymmetry['severely_asymmetric'], referral['urgent']))
    rules.append(ctrl.Rule(
        asymmetry['moderately_asymmetric'], referral['expedited']))

    return rules


def get_complex_interaction_rules(threshold, slope, severity):
    """
    Rules for multi-frequency contour interactions that the severity group
    alone does not capture.

    Previously named "mixed-loss rules". NHANES carries no bone-conduction
    thresholds, so these rules cannot identify pathophysiological mixed hearing
    loss (a conductive component superimposed on sensorineural loss); they
    capture air-conduction contour instead. The six rules that carried
    asymmetry antecedents were removed rather than stripped, because without
    their asymmetry term they would fire during single-ear validation and alter
    the reported metrics. Asymmetry is now handled by
    :func:`get_referral_rules`.

    Parameters
    ----------
    threshold : ctrl.Antecedent
    slope : ctrl.Antecedent
    severity : ctrl.Consequent

    Returns
    -------
    list[ctrl.Rule]
        4 rules for complex contour presentations.
    """
    rules = []

    # --- Precipitous contour at a moderate threshold ---
    rules.append(ctrl.Rule(
        slope['precipitous'] & threshold['moderate'],
        severity['severe'],
    ))
    rules.append(ctrl.Rule(
        slope['precipitous'] & threshold['mild'],
        severity['moderately_severe'],
    ))

    # --- Normal threshold with a steep or precipitous contour: the PTA
    #     understates the functional loss at the affected frequencies ---
    rules.append(ctrl.Rule(
        threshold['normal'] & slope['steeply_sloping'],
        severity['mild'],
    ))
    rules.append(ctrl.Rule(
        threshold['normal'] & slope['precipitous'],
        severity['moderate'],
    ))

    return rules


def get_all_rules(threshold, slope, notch, asymmetry, severity, audiogram_shape,
                  referral=None, single_ear=False):
    """
    Combine all rule groups into a single flat rule list.

    Parameters
    ----------
    threshold, slope, notch, asymmetry : ctrl.Antecedent
    severity, audiogram_shape : ctrl.Consequent
    referral : ctrl.Consequent or None
        If given, asymmetry drives a referral flag. If None, the referral rules
        are omitted and asymmetry has no effect on any output, which is the
        honest configuration for single-ear validation.
    single_ear : bool
        Retained for call compatibility. Asymmetry no longer reaches severity,
        so no rule needs omitting on its account.

    Returns
    -------
    list[ctrl.Rule]
        42 rules, or 30 without the referral group.
    """
    rules = []
    rules.extend(get_severity_rules(threshold, severity))
    rules.extend(get_configuration_rules(slope, notch, audiogram_shape, severity))
    rules.extend(get_complex_interaction_rules(threshold, slope, severity))
    if referral is not None:
        rules.extend(get_referral_rules(asymmetry, referral))
    return rules
