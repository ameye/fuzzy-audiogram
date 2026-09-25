#!/usr/bin/env python3
"""Final v4 trim: compress the six longest sections."""
import sys
from pathlib import Path

P = Path("/opt/data/fuzzy-audiogram/cmbp_v2/manuscript_v4.qmd")
s = P.read_text(encoding="utf-8")

CUTS = [
# ---- Methods: FIS (256 -> ~185)
("""A Mamdani-type fuzzy inference system [@mamdani1975] was constructed with 42 expert-derived rules in three functional groups: 12 severity rules mapping fuzzified thresholds to the severity output, 14 configuration rules classifying audiogram shape from slope and notch, and 4 complex-interaction rules for contour presentations the severity group does not capture. A further 12 rules map inter-aural asymmetry to a separate referral output rather than to severity.

Decoupling asymmetry from severity is a deliberate design choice. Asymmetry between ears is an indication to investigate unilateral pathology, not evidence that the poorer ear hears less well, so it produces a referral recommendation (none, routine, expedited or urgent) while each ear is graded on its own thresholds. The 42-rule base is used for both single-ear and bilateral input, so the validated configuration and the deployed one coincide. All validation metrics were computed on individual ears under a single-ear protocol, in which the asymmetry input is zero and the referral output is correspondingly inert.

Inference used max–min composition with minimum clipping implication; rule outputs were aggregated by fuzzy union (max) and defuzzified by centroid of area to obtain a continuous Fuzzy Audiometric Index (FAI) on a 0 to 100 scale. The severity rules take the PTA-4 speech-frequency average (0.5 to 4 kHz) as their primary threshold input, matching the WHO reference [@who1997]; this keeps the FAI comparable to the standard against which it is validated, but means that agreement with PTA-4 is partly by construction.""",
 """A Mamdani-type fuzzy inference system [@mamdani1975] was constructed with 42 expert-derived rules in three functional groups: 12 severity rules mapping fuzzified thresholds to the severity output, 14 configuration rules classifying audiogram shape, and 4 complex-interaction rules for contour presentations the severity group does not capture. A further 12 rules map inter-aural asymmetry to a separate referral output rather than to severity, since asymmetry indicates unilateral pathology rather than a poorer-hearing ear. The 42-rule base serves both single-ear and bilateral input, so the validated configuration and the deployed one coincide; under the single-ear protocol the asymmetry input is zero and the referral output is inert.

Inference used max–min composition with minimum clipping implication, fuzzy union aggregation and centroid defuzzification to obtain a continuous Fuzzy Audiometric Index (FAI) on a 0 to 100 scale. The severity rules take the PTA-4 speech-frequency average as their primary threshold input, matching the reference standard; this keeps the FAI comparable to the standard against which it is validated, but means agreement with PTA-4 is partly by construction."""),

# ---- Methods: membership construction (233 -> ~180)
("""The six trapezoids were arranged as a formal Ruspini partition, so their memberships sum to exactly 1 at every point of the 0 to 120 dB universe and no threshold is unclassified. Retaining the percentile-derived cores, each trapezoid's left foot was set to the previous category's core end and its right foot to the next category's core start, making adjacent shoulders complementary linear ramps that cross at 0.5 at the midpoint of the core gap. The construction guarantees complete, non-redundant coverage without any gap-filling heuristic.

A partition's transition width equals its core gap, which a data-driven fit can leave narrower than the ±5 dB test-retest variability the graded region represents. The construction therefore accepts a minimum transition width, set to 10 dB by widening the core gaps while preserving the partition property, and the effect of this floor was evaluated by ablation.""",
 """The six trapezoids were arranged as a formal Ruspini partition, so their memberships sum to exactly 1 at every point of the 0 to 120 dB universe and no threshold is unclassified. Retaining the percentile cores, each trapezoid's left foot was set to the previous category's core end and its right foot to the next category's core start, making adjacent shoulders complementary linear ramps that cross at 0.5 at the midpoint of the core gap.

A partition's transition width equals its core gap, which a data-driven fit can leave narrower than the ±5 dB test-retest variability the graded region represents. The construction therefore accepts a minimum transition width, set to 10 dB by widening the gaps while preserving the partition property; this floor was evaluated by ablation."""),

# ---- Methods: configuration and asymmetry (175 -> ~130)
("""Audiogram slope, the dB change from 500 Hz to 4 kHz, was fuzzified into five categories: Rising (< −5 dB), Flat (−5 to 12 dB), Gently Sloping (12–28 dB), Steeply Sloping (28–45 dB) and Precipitous (>45 dB). The 0.5 to 4 kHz window is the conventional anchor for both severity grading [@clark1981; @who1997] and configuration typing. A notch module quantifies the 4 kHz dip relative to the mean of the 2 kHz and 8 kHz thresholds, fuzzified into No Notch, Shallow Notch (<15 dB) and Deep Notch (≥15 dB). A high-frequency PTA (2 to 8 kHz) was computed as an additional feature.

Inter-aural asymmetry was fuzzified into Symmetric (≤15 dB), Mildly Asymmetric (16–30 dB), Moderately Asymmetric (31–45 dB) and Severely Asymmetric (>45 dB). The operational criterion is the maximum absolute difference across frequencies, which is more sensitive than either definition applied by Suen et al., who used a pure-tone-average difference above 15 dB and a contiguous-frequency criterion [@suen2021]; no standard audiometric criterion for asymmetry exists, and prevalence estimates vary several-fold with the definition chosen.""",
 """Audiogram slope, the decibel change from 500 Hz to 4 kHz, was fuzzified into five categories: Rising (< −5 dB), Flat (−5 to 12 dB), Gently Sloping (12–28 dB), Steeply Sloping (28–45 dB) and Precipitous (>45 dB). A notch module quantifies the 4 kHz dip relative to the mean of the 2 kHz and 8 kHz thresholds, fuzzified into No Notch, Shallow Notch (<15 dB) and Deep Notch (≥15 dB).

Inter-aural asymmetry was fuzzified into Symmetric (≤15 dB), Mildly (16–30 dB), Moderately (31–45 dB) and Severely Asymmetric (>45 dB). The operational criterion is the maximum absolute difference across frequencies, which is more sensitive than either definition used by Suen et al., who applied a pure-tone-average difference above 15 dB and a contiguous-frequency criterion [@suen2021]; no standard criterion for asymmetry exists."""),

# ---- Methods: evaluation metrics (138 -> ~108)
("""Primary metrics were weighted Cohen's κ (quadratic weights), mean absolute error (MAE), and agreement stratified by borderline (±5 dB of a WHO boundary) versus clear-case (≥6 dB) status. Spearman's rank correlation assessed monotonic association and Bland-Altman analysis with 95% limits of agreement compared FAI with PTA-4. Agreement was also characterised by distance from the nearest boundary, with subgroup analyses by age decade, configuration and degree of loss. Per-class sensitivity, specificity and precision were reported to expose the contribution of the majority class to the aggregate figures.""",
 """Primary metrics were weighted Cohen's κ (quadratic weights), mean absolute error, and agreement stratified by borderline (±5 dB of a boundary) versus clear-case (≥6 dB) status. Bland-Altman analysis compared FAI with PTA-4 after a linear transfer fitted on the training partition mapped the index onto the decibel scale. Agreement was also characterised by distance from the nearest boundary, and per-class sensitivity, specificity and precision were reported to expose the contribution of the majority class to the aggregate figures."""),

# ---- Results: probabilistic comparison (207 -> ~160)
("""Table 2 reports the probabilistic benchmark. A proportional-odds ordinal logistic regression on the primary threshold alone reproduced the WHO grade exactly in every one of the 3,912 test ears, with a Brier score and log loss of 0.0000, and the same model on all seven frequencies performed identically. Multinomial logistic regression reached kappa 0.9941 with a Brier score of 0.0158.

These results establish that the reference label is not a prediction target but a deterministic thresholding of the pure-tone average, so agreement metrics cannot discriminate between models on this task. Any model able to represent monotone thresholds recovers the label exactly, and residual differences measure how well each approximation fits a step function rather than how well it predicts anything.

Among the models that do not saturate, the FAI membership vector returned a Brier score of 0.0474, log loss 0.0805 and expected calibration error 0.0300, against 0.0479, 0.2771 and 0.0304 for gradient boosting on the richer seven-frequency input. The memberships were therefore as well calibrated as gradient boosting and substantially better on log loss, from less input. Their arg-max recovered the reference grade at kappa 0.9564, exceeding the 0.946 obtained from the separately calibrated thresholds.""",
 """Table 2 reports the probabilistic benchmark. A proportional-odds ordinal logistic regression on the primary threshold alone reproduced the reference grade exactly in all 3,912 test ears, with a Brier score and log loss of 0.0000, and the same model on all seven frequencies performed identically. The reference label is therefore not a prediction target but a deterministic thresholding of the pure-tone average, so agreement metrics cannot discriminate between models here: any model able to represent monotone thresholds recovers the label exactly, and residual differences measure how well each approximation fits a step function.

Among the models that do not saturate, the FAI membership vector returned a Brier score of 0.0474, log loss 0.0805 and expected calibration error 0.0300, against 0.0479, 0.2771 and 0.0304 for gradient boosting on the richer seven-frequency input. The memberships were as well calibrated as gradient boosting and substantially better on log loss from less input, and their arg-max recovered the reference grade at kappa 0.9564, exceeding the 0.946 from the separately calibrated thresholds."""),

# ---- Discussion: limitations (253 -> ~185)
("""Only air-conduction thresholds were used, so the framework grades combined air-conduction loss and cannot separate sensorineural from conductive or mixed components; the four complex-interaction rules therefore capture air-conduction contour rather than pathophysiological mixed loss. The 48-rule base, though derived from audiology expertise, has not undergone formal Delphi consensus. The three cycles analysed covered adults aged 20 to 69 years, so children and older adults are not represented, some configurations remain underrepresented, and extended high-frequency audiometry was not covered.""",
 """Only air-conduction thresholds were used, so the framework grades combined air-conduction loss and cannot separate sensorineural from conductive or mixed components; the complex-interaction rules therefore capture air-conduction contour rather than pathophysiological mixed loss. The rule base, though derived from audiology expertise, has not undergone formal Delphi consensus. The three cycles covered adults aged 20 to 69 years, so children and older adults are not represented, some configurations remain underrepresented, and extended high-frequency audiometry was not covered."""),

# ---- Results: classification agreement (172 -> ~140)
("""Per-class performance is given in Table 1. Sensitivity was 0.980 for normal ears and 0.950 for mild, but fell to 0.621 for moderate and 0.500 for moderately severe loss, the two smallest classes. Macro-averaged sensitivity was 0.786 against the 96.5% overall figure, which the 87% normal majority largely determines. Of 138 disagreements, 104 moved upward by one grade and 34 downward, so the graded output can resolve toward less severe categories as well as more severe ones.""",
 """Per-class performance is given in Table 1. Sensitivity was 0.980 for normal ears and 0.950 for mild, but fell to 0.621 for moderate and 0.500 for moderately severe loss, the two smallest classes. Macro-averaged sensitivity was 0.786 against the 96.5% overall figure, which the normal majority largely determines. Of 138 disagreements, 104 moved upward by one grade and 34 downward, a predominantly upward error structure that would increase false-positive referrals at the graded boundary."""),
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
