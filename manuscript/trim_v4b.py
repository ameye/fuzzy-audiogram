#!/usr/bin/env python3
"""Second v4 trim: fold three sections into the supplement and the table."""
import sys
from pathlib import Path

P = Path("/opt/data/fuzzy-audiogram/cmbp_v2/manuscript_v4.qmd")
s = P.read_text(encoding="utf-8")

CUTS = [
# ---- Results: 2021 section reduced to the essentials; Table 4 carries the rest
("""Under the 2021 schema the framework performed better on every metric except raw overall agreement (Table 4): kappa 0.959 against 0.946, mean absolute error 3.74 dB against 4.35, and rho 0.844 against 0.812. Borderline agreement was 88.0% and clear-case agreement 99.4%, with the borderline figure measured over the harder population, since the 2021 boundaries place 29.5% of ears within ±5 dB of one against 18.7%. Scoring the six-category system against the 2021 reference returned kappa 0.875, so the categories must be fitted to the boundaries being claimed.""",
 """Under the 2021 schema the framework performed better on every metric except raw overall agreement (Table 4): kappa 0.959 against 0.946, mean absolute error 3.74 dB against 4.35, and rho 0.844 against 0.812. Borderline agreement was 88.0%, measured over the harder population, since the 2021 boundaries place 29.5% of ears within ±5 dB of one against 18.7%. Scoring the six-category system against the 2021 reference returned kappa 0.875."""),

# ---- Results: normal-mild transition to the supplement
("""## The Normal–Mild Transition

At the classic 25 dB cut-off the system preserved a graded transition (Supplementary Table S3). A PTA-4 of 24 dB mapped to FAI 22.4 with Normal membership 0.44 and Mild 0.56, rising smoothly to FAI 26.3 with Normal 0.22 and Mild 0.78 at 27 dB. The crisp rule flips the label between 26 and 27 dB with no graded information, whereas the fuzzy system returns a smooth rise across the 24 to 27 dB zone, preserving the information that a 25 dB threshold is closer to normal than a 27 dB one. The shoulders cross at 0.5 near 23 dB.

""",
 """## The Normal–Mild Transition

At the classic 25 dB cut-off the system preserved a graded transition (Supplementary Table S4): a PTA-4 of 24 dB mapped to FAI 22.4 with Normal membership 0.44 and Mild 0.56, rising to FAI 26.3 with Normal 0.22 at 27 dB. The crisp rule flips the label between 26 and 27 dB with no graded information, whereas the fuzzy system returns a smooth rise across the zone.

"""),

# ---- Discussion: schema section folded into two sentences
("""## The Classification Schema Is a Parameter

Rebuilding under the WHO 2021 schema improved every metric except raw overall agreement, which matters for how the framework should be described. The construction is not tied to the 25/40/55/70/90 boundaries, which trace to Clark rather than to WHO; the same cores, partition and calibration applied to the 2021 boundaries produced a better-calibrated system with lower absolute error. The framework is therefore schema-agnostic, and agreement figures are interpretable only alongside the schema they were computed against, since the six-category system scored 0.875 against the 2021 reference. A change to WHO's grade table would require recalibration, not redesign.

""",
 """## The Classification Schema Is a Parameter

The construction is not tied to the 25/40/55/70/90 boundaries, which trace to Clark rather than to WHO. The same cores, partition and calibration applied to the 2021 boundaries produced a better-calibrated system with lower absolute error, so the framework is schema-agnostic and agreement figures are interpretable only alongside the schema they were computed against. A change to WHO's grade table would require recalibration, not redesign.

"""),

# ---- Discussion: asymmetry section folded to its Conclusion
("""## Asymmetry as a Referral Flag

Inter-aural asymmetry was decoupled from severity during this work. The rule base previously allowed asymmetry to upgrade severity, so an ear with a pure-tone average of 55 dB could be reported as moderately severe because the contralateral ear differed; asymmetry is a referral indicator, not an amplifier of peripheral loss. The change is neutral for every figure reported here, since the single-ear protocol pins the asymmetry input to zero, but it aligns the validated rule base with the deployed one and removes a discrepancy in which the deployed system ran 48 rules against the 47 validated.

""",
 ""),

# ---- Discussion: fold the asymmetry point into limitations
("""The reference standard is the classification itself, and the severity rules share its frequency band, so agreement is partly by construction.""",
 """Inter-aural asymmetry was decoupled from severity during this work and now drives a referral recommendation instead. The rule base previously allowed asymmetry to upgrade severity, so an ear with a pure-tone average of 55 dB could be reported as moderately severe because the contralateral ear differed; asymmetry is a referral indicator rather than an amplifier of peripheral loss. The change is neutral for the figures reported here, since the single-ear protocol pins the asymmetry input to zero, but it aligns the validated rule base with the deployed one.

The reference standard is the classification itself, and the severity rules share its frequency band, so agreement is partly by construction."""),

# ---- Methods: study design and sample compressed
("""This was a cross-sectional secondary analysis of publicly available audiometric data from the National Health and Nutrition Examination Survey (NHANES). Three cycles administering air-conduction pure-tone audiometry to adults aged 20 to 69 years were combined: 1999–2000 (AUX1), 2011–2012 (AUX_G) and 2015–2016 (AUX_I). Thresholds were recorded at 500, 1000, 2000, 3000, 4000, 6000 and 8000 Hz in each ear, with age and sex from the corresponding DEMO files.""",
 """This was a cross-sectional secondary analysis of audiometric data from three National Health and Nutrition Examination Survey (NHANES) cycles that administered air-conduction pure-tone audiometry to adults aged 20 to 69 years: 1999–2000 (AUX1), 2011–2012 (AUX_G) and 2015–2016 (AUX_I). Thresholds were recorded at 500, 1000, 2000, 3000, 4000, 6000 and 8000 Hz in each ear."""),

# ---- Decision curve compressed
("""FAI-based referral maintained net benefit comparable to PTA-4-based referral across the whole threshold-probability range for both outcomes, and both exceeded treat-all at every threshold (Figure 3). For any hearing loss at a 10% referral threshold, net benefit was 0.126 for the FAI against 0.131 for PTA-4 and 0.034 for treating all. The small differences favour the crisp markers, which are defined on the outcome itself; the substantive finding is that adopting the graded index does not sacrifice decision utility.""",
 """FAI-based referral maintained net benefit comparable to PTA-4-based referral across the threshold-probability range for both outcomes, and both exceeded treat-all at every threshold (Figure 3); for any hearing loss at a 10% threshold, net benefit was 0.126 against 0.131 and 0.034 for treating all. The small differences favour the crisp markers, which are defined on the outcome itself, so the substantive finding is that the graded index does not sacrifice decision utility."""),
]

applied, missed = 0, []
for old, new in CUTS:
    if old in s:
        s = s.replace(old, new, 1); applied += 1
    else:
        missed.append(old[:70].replace("\n", " "))

P.write_text(s, encoding="utf-8")
print(f"  applied {applied}/{len(CUTS)} cuts")
for m in missed:
    print(f"    MISSED: {m}...")
sys.exit(0 if not missed else 1)
