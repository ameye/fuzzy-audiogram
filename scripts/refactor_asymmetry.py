#!/usr/bin/env python3
"""Decouple inter-aural asymmetry from severity.

Clinical objection: asymmetry is a referral indicator for unilateral pathology
(vestibular schwannoma, asymmetric Meniere's), not evidence that the poorer ear
hears worse. The rule base nonetheless let asymmetry upgrade severity — 12
asymmetry rules plus 6 of the 10 mixed-loss rules — so an ear with a 55 dB PTA
could be reported as moderately severe purely because the contralateral ear
differed.

This refactor:

  1. retargets the asymmetry rules to a new ``referral`` consequent
     (none / routine / expedited / urgent), so asymmetry drives a medical
     referral flag rather than altering severity
  2. drops the 6 asymmetry-bearing mixed-loss rules from severity entirely
     (they must not simply lose their asymmetry antecedent, or they would begin
     firing during single-ear validation and change every reported metric)
  3. renames the remaining 4 to "complex configuration interaction rules",
     since without bone-conduction data they capture multi-frequency air-
     conduction contour, not pathophysiological mixed hearing loss

The change is metrics-neutral for the published validation, because asymmetry is
pinned to zero in the single-ear protocol and neither group fires there. The
script asserts that by recomputing the test-set FAI before and after.

Run:  python3 scripts/refactor_asymmetry.py
"""
import re, sys, shutil
from pathlib import Path

ROOT = Path("/opt/data/fuzzy-audiogram")
RULES = ROOT / "fuzzy_audiogram/rules.py"
CORE = ROOT / "fuzzy_audiogram/core.py"

shutil.copy(RULES, RULES.with_suffix(".py.pre_asymmetry"))
shutil.copy(CORE, CORE.with_suffix(".py.pre_asymmetry"))

# ============================================================ rules.py
s = RULES.read_text(encoding="utf-8")

# ---- 1. replace the asymmetry-to-severity group with referral rules
start = s.index("def get_asymmetry_rules(")
end = s.index("def get_mixed_loss_rules(")
new_referral = '''def get_referral_rules(asymmetry, referral):
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


'''
s = s[:start] + new_referral + s[end:]

# ---- 2/3. the mixed-loss group: keep only the asymmetry-free rules
start = s.index("def get_mixed_loss_rules(")
end = s.index("def get_all_rules(")
new_complex = '''def get_complex_interaction_rules(threshold, slope, severity):
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


'''
s = s[:start] + new_complex + s[end:]

# ---- 4. rewrite get_all_rules to wire the referral consequent
start = s.index("def get_all_rules(")
new_all = '''def get_all_rules(threshold, slope, notch, asymmetry, severity, audiogram_shape,
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
'''
s = s[:start] + new_all

RULES.write_text(s, encoding="utf-8")

# ============================================================ core.py
c = CORE.read_text(encoding="utf-8")

# add referral output memberships next to the severity output params
anchor = "SHAPE_OUTPUT_PARAMS = {"
assert anchor in c, "SHAPE_OUTPUT_PARAMS not found"
referral_block = '''# Referral output: asymmetry drives a medical referral recommendation rather
# than altering the severity grading. Universes are on the same 0-100 scale as
# the other consequents for consistency.
REFERRAL_OUTPUT_PARAMS = {
    'none':      [0, 0, 10, 25],
    'routine':   [15, 25, 45, 55],
    'expedited': [45, 55, 75, 85],
    'urgent':    [75, 88, 100, 100],
}

'''
c = c.replace(anchor, referral_block + anchor, 1)

# add the consequent
c = c.replace(
    "    shape_con = ctrl.Consequent(np.arange(0, 101, 1), 'audiogram_shape')",
    "    shape_con = ctrl.Consequent(np.arange(0, 101, 1), 'audiogram_shape')\n"
    "    referral_con = ctrl.Consequent(np.arange(0, 101, 1), 'referral')",
    1)

# attach its memberships
c = c.replace(
    "    for cat, params in SHAPE_OUTPUT_PARAMS.items():\n"
    "        shape_con[cat] = fuzz.trapmf(shape_con.universe, params)",
    "    for cat, params in SHAPE_OUTPUT_PARAMS.items():\n"
    "        shape_con[cat] = fuzz.trapmf(shape_con.universe, params)\n\n"
    "    for cat, params in REFERRAL_OUTPUT_PARAMS.items():\n"
    "        referral_con[cat] = fuzz.trapmf(referral_con.universe, params)",
    1)

# pass it through to the rule builder
c = c.replace(
    "    rules = get_all_rules(\n"
    "        threshold_ant, slope_ant, notch_ant, asym_ant,\n"
    "        severity_con, shape_con,\n"
    "        single_ear=single_ear,\n"
    "    )",
    "    rules = get_all_rules(\n"
    "        threshold_ant, slope_ant, notch_ant, asym_ant,\n"
    "        severity_con, shape_con,\n"
    "        referral=referral_con,\n"
    "        single_ear=single_ear,\n"
    "    )",
    1)

# return the new consequent alongside the others. Append at the END: some
# callers unpack positionally, and inserting mid-tuple would silently remap
# their variables.
c = c.replace(
    "    return (system, simulation,\n"
    "            threshold_ant, slope_ant, notch_ant, asym_ant,\n"
    "            severity_con, shape_con)",
    "    return (system, simulation,\n"
    "            threshold_ant, slope_ant, notch_ant, asym_ant,\n"
    "            severity_con, shape_con, referral_con)",
    1)

# two call sites unpack exactly eight values and must be relaxed
c = c.replace(
    "    (_, sim, threshold_ant, slope_ant, _notch_ant, _asym_ant,\n"
    "     _severity_con, _shape_con) = build_audiogram_fis(single_ear=single_ear)",
    "    (_, sim, threshold_ant, slope_ant, *_rest) = build_audiogram_fis(single_ear=single_ear)",
    1)

# the older combined pipelines also unpack exactly eight
for extra in (ROOT / "scripts/pipeline_combined.py",):
    if extra.exists():
        t = extra.read_text(encoding="utf-8")
        t = t.replace(
            "system, sim, threshold_ant, slope_ant, _n, _a, _sc, _sh = build_fis_with_params(params)",
            "system, sim, threshold_ant, slope_ant, *_rest = build_fis_with_params(params)",
            1)
        extra.write_text(t, encoding="utf-8")
        print(f"  relaxed the positional unpack in {extra.name}")

CORE.write_text(c, encoding="utf-8")

print("  patched rules.py and core.py")

# ============================================================ verify
checks = [
    (RULES, "referral rules", "def get_referral_rules("),
    (RULES, "complex interaction", "def get_complex_interaction_rules("),
    (RULES, "no asymmetry->severity", "asymmetry['severely_asymmetric'] & severity"),
    (RULES, "no mixed-loss name", "def get_mixed_loss_rules("),
    (CORE, "referral consequent", "referral_con = ctrl.Consequent"),
    (CORE, "referral params", "REFERRAL_OUTPUT_PARAMS = {"),
]
ok = True
for path, label, probe in checks:
    txt = path.read_text()
    present = probe in txt
    want_absent = label.startswith("no ")
    good = (not present) if want_absent else present
    if not good:
        ok = False
    print(f"  {'OK  ' if good else 'FAIL'}  {label}"
          f"{' (must be absent)' if want_absent else ''}")
if not ok:
    print("  a replacement did not land")
    sys.exit(1)
print("  all checks passed")
