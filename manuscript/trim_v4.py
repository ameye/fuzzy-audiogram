#!/usr/bin/env python3
"""Trim v4 back under the 3,500-word ceiling.

The companion analysis and the attribution corrections added roughly 790 words.
These cuts move illustrative material to the supplement and compress passages
that Table 4 now carries numerically.
"""
import sys
from pathlib import Path

P = Path("/opt/data/fuzzy-audiogram/cmbp_v2/manuscript_v4.qmd")
s = P.read_text(encoding="utf-8")

CUTS = [
# ---- Methods: comparator schemas compressed
("""The framework is schema-agnostic: the categories are a labelling convention, and the same construction applies to any of them. To separate the method from the convention, the entire pipeline was rebuilt under the WHO 2021 schema (seven categories, boundaries at 20, 35, 50, 65, 80 and 95 dB HL) using the same cohort, split, percentile-core fitting, Ruspini construction and calibration procedure, so the two arms differ only in their classification schema. Both were evaluated on the same held-out ears. The six-category system was additionally scored against the 2021 reference, which quantifies the cost of a mismatch between the fitted categories and the boundaries being claimed.""",
 """The categories are a labelling convention rather than part of the method, so the pipeline was rebuilt under the WHO 2021 schema (seven categories at 20, 35, 50, 65, 80 and 95 dB HL) using the same cohort, split, core fitting, construction and calibration. The two arms therefore differ only in schema. The six-category system was additionally scored against the 2021 reference, which quantifies the cost of a mismatch between fitted categories and the boundaries claimed."""),

# ---- Results: 2021 section compressed (Table 4 carries the numbers)
("""Rebuilt under the 2021 schema, the framework performed better on every metric except raw overall agreement (Table 4). Weighted kappa was 0.959 against 0.946, mean absolute error 3.74 dB against 4.35 dB, and Spearman's rho 0.844 against 0.812. Borderline agreement was 88.0%, and that figure is measured over a harder population: the 2021 boundaries place 29.5% of test ears within ±5 dB of a boundary, against 18.7% under the six-category scheme. Clear-case agreement was 99.4%.

Scoring the six-category system against the 2021 reference returned kappa 0.875, so construction and schema must match. The performance difference between the arms reflects the uniformity of the 2021 boundaries rather than any change to the inference method, since the cores, the partition and the calibration procedure were identical.""",
 """Under the 2021 schema the framework performed better on every metric except raw overall agreement (Table 4): kappa 0.959 against 0.946, mean absolute error 3.74 dB against 4.35, and rho 0.844 against 0.812. Borderline agreement was 88.0% and clear-case agreement 99.4%, with the borderline figure measured over the harder population, since the 2021 boundaries place 29.5% of ears within ±5 dB of one against 18.7%. Scoring the six-category system against the 2021 reference returned kappa 0.875, so the categories must be fitted to the boundaries being claimed."""),

# ---- Results: case studies to the supplement
("""## Clinical Case Studies

Four synthetic archetypes illustrate the framework (Figure 4, Supplementary Table S5). Case B is the most informative: a noise-induced notch with a normal PTA-4 of 22.5 dB returned FAI 21.2, while its configuration output identified a precipitous notched profile from a 30 dB notch, flagging high-frequency pathology the severity grade alone misses. Case D, an asymmetric loss with a PTA-4 of 55.0 dB, was upgraded by the asymmetry input from the WHO grade of moderate to Moderately Severe.

""",
 """## Clinical Case Studies

Four synthetic archetypes illustrate the framework (Figure 4, Supplementary Table S6). Case B is the most informative: a noise-induced notch with a normal PTA-4 of 22.5 dB returned FAI 21.2, while its configuration output identified a precipitous notched profile, flagging high-frequency pathology the severity grade alone misses.

"""),

# ---- Discussion: schema section folded down
("""## The Classification Schema Is a Parameter

Rebuilding the pipeline under the WHO 2021 schema improved every metric except raw overall agreement. That result matters for how the framework should be described. The fuzzy construction is not tied to the 25/40/55/70/90 boundaries, which trace to Clark and ANSI rather than to WHO; the same cores, partition and calibration applied to the 2021 boundaries at 20/35/50/65/80/95 dB produced a better-calibrated system with a lower absolute error.

Two consequences follow. First, the framework should be presented as schema-agnostic, with the classification convention treated as a parameter rather than a premise. Second, agreement figures are only interpretable alongside the schema they were computed against: scoring the six-category system against the 2021 reference returned kappa 0.875, a penalty paid purely for a mismatch between the fitted categories and the boundaries being claimed. Any future change to WHO's grade table would require recalibration but not redesign, which is a property of the architecture rather than of these particular parameters.""",
 """## The Classification Schema Is a Parameter

Rebuilding under the WHO 2021 schema improved every metric except raw overall agreement, which matters for how the framework should be described. The construction is not tied to the 25/40/55/70/90 boundaries, which trace to Clark rather than to WHO; the same cores, partition and calibration applied to the 2021 boundaries produced a better-calibrated system with lower absolute error. The framework is therefore schema-agnostic, and agreement figures are interpretable only alongside the schema they were computed against, since the six-category system scored 0.875 against the 2021 reference. A change to WHO's grade table would require recalibration, not redesign."""),

# ---- Discussion: asymmetry section folded down
("""## Asymmetry as a Referral Flag

Inter-aural asymmetry was decoupled from the severity output during this work. The rule base previously allowed asymmetry to upgrade severity, so an ear with a pure-tone average of 55 dB could be reported as moderately severe because the contralateral ear differed. Asymmetry is a referral indicator, not an amplifier of peripheral loss, and the revised rule base now emits a referral recommendation instead.

This change is neutral for every figure reported here, because the single-ear protocol pins the asymmetry input to zero and the referral output is correspondingly inert; the test-set index is unchanged. It does change the deployed bilateral behaviour, and it removes a discrepancy that previously existed between the validated configuration and the deployed one, which ran 48 rules against the 47 validated.""",
 """## Asymmetry as a Referral Flag

Inter-aural asymmetry was decoupled from severity during this work. The rule base previously allowed asymmetry to upgrade severity, so an ear with a pure-tone average of 55 dB could be reported as moderately severe because the contralateral ear differed; asymmetry is a referral indicator, not an amplifier of peripheral loss. The change is neutral for every figure reported here, since the single-ear protocol pins the asymmetry input to zero, but it aligns the validated rule base with the deployed one and removes a discrepancy in which the deployed system ran 48 rules against the 47 validated."""),

# ---- Discussion: circularity section compressed
("""The probabilistic benchmark produced the study's most consequential result. A proportional-odds ordinal logistic regression recovered the WHO grade exactly in all 3,912 test ears with a Brier score of zero. That is not a strong model but a proof that the reference label is a deterministic monotone function of the pure-tone average. Because the label is a thresholding, any model able to represent monotone thresholds recovers it exactly and agreement metrics saturate, so a graded representation cannot be shown to be better by kappa. This applies equally to the machine-learning comparators in earlier reports of this work, whose near-perfect scores reflected the structure of the target rather than predictive skill.

What survives is discrimination among approximations. Gradient boosting, on seven-frequency input and with more capacity, scored kappa 0.9177 against 0.9564 for the fuzzy memberships. A label defined by thresholds on a single continuous quantity is precisely the structure trapezoidal membership functions express natively, since the partition's breakpoints are thresholds in decibels, whereas a tree ensemble must approximate the same step function through axis-aligned splits on noisy inputs. The comparison therefore evidences an appropriate inductive bias rather than superior prediction. It is the probabilistic properties that discriminate, and there the FAI memberships matched gradient boosting on Brier score and calibration error and halved its log loss, from the primary threshold alone rather than seven frequencies.""",
 """The probabilistic benchmark produced the study's most consequential result. A proportional-odds ordinal logistic regression recovered the reference grade exactly in all 3,912 test ears with a Brier score of zero, which is not a strong model but a proof that the label is a deterministic monotone function of the pure-tone average. Because the label is a thresholding, any model able to represent monotone thresholds recovers it exactly and agreement metrics saturate, so a graded representation cannot be shown to be better by kappa. This applies equally to the machine-learning comparators in earlier reports of this work, whose near-perfect scores reflected the structure of the target.

What survives is discrimination among approximations. Gradient boosting, on seven-frequency input with more capacity, scored kappa 0.9177 against 0.9564. A label defined by thresholds on one continuous quantity is what trapezoidal membership functions express natively, since the breakpoints are thresholds in decibels, whereas a tree ensemble must approximate the same step function through axis-aligned splits on noisy inputs. It is the probabilistic properties that discriminate, and there the memberships matched gradient boosting on Brier score and calibration error and halved its log loss, from the primary threshold alone."""),

# ---- Introduction: tighter objective
("""This study develops such a framework and validates it on a large nationally representative cohort. The objectives were to construct severity membership functions forming a formal Ruspini partition, so every threshold receives a complete and non-redundant set of memberships; to validate the index against the WHO PTA-4 reference on a held-out test set with a participant-level split; to benchmark its graded output against probabilistic multi-class models using proper scoring rules; and to determine empirically how the width of the graded region affects agreement with the crisp reference.""",
 """This study develops such a framework and validates it on a large nationally representative cohort. The objectives were to construct severity membership functions forming a formal Ruspini partition; to validate the index on a held-out test set with a participant-level split; to benchmark its graded output against probabilistic multi-class models using proper scoring rules; to determine empirically how the width of the graded region affects agreement; and to establish how far the results depend on the classification schema rather than on the method."""),

# ---- Discussion: limitations compressed
("""The reference standard is the WHO PTA-4 classification itself, and the severity rules share its frequency band, so agreement is partly by construction. The benchmark quantifies that dependence rather than removing it, since the ordinal logistic's exact reconstruction shows the ceiling is definitional. This limits what any agreement figure for this task can mean, and is why the graded outputs and probabilistic metrics carry the argument. The case studies are synthetic archetypes rather than patient records, and the ablation compared two settings rather than optimising the floor, so 10 dB is a defensible default rather than a demonstrated optimum. Whether the FAI predicts hearing-aid outcomes, patient-reported benefit or surgical candidacy has not been assessed.""",
 """The reference standard is the classification itself, and the severity rules share its frequency band, so agreement is partly by construction. The benchmark quantifies that dependence rather than removing it, since the exact reconstruction shows the ceiling is definitional. This limits what any agreement figure can mean for this task, and is why the graded outputs and probabilistic metrics carry the argument. The case studies are synthetic archetypes rather than patient records. Whether the FAI predicts hearing-aid outcomes, patient-reported benefit or surgical candidacy has not been assessed."""),
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
