#!/usr/bin/env python3
"""v4: correct the attributions and add the WHO 2021 companion analysis.

Content edits
  1. the six-category scheme is attributed to Clark/ANSI, not WHO; WHO's own
     five-grade table (1991, 1997) and the 2021 seven-category revision are both
     named explicitly
  2. Ceriani removed from the human-audiogram classifier claim (it is a murine
     ABR study)
  3. Suen's actual criteria recorded; 15 dB stated as an operational boundary
  4. the asymmetry redesign and the 42-rule base documented
  5. the WHO 2021 companion arm added to Methods, Results and Discussion
  6. the Bland-Altman figures replaced with the scale-corrected values
  7. Table 2's baseline split into uniform and majority-class rows

Compensating cuts keep the main text under the 3,500-word ceiling.
"""
import sys
from pathlib import Path

P = Path("/opt/data/fuzzy-audiogram/cmbp_v2/manuscript_v3.qmd")
out = Path("/opt/data/fuzzy-audiogram/cmbp_v2/manuscript_v4.qmd")
s = P.read_text(encoding="utf-8")

EDITS = [
# ---------------------------------------------------------------- attribution
("""Thresholds were assigned to the six WHO severity categories under the WHO PTA-4 classification [@who1997], and a trapezoidal membership function [a, b, c, d] was fitted per category on percentile criteria, with cores at b = P25 and c = P75 across all training-set thresholds.""",
 """Thresholds were assigned to six severity categories and a trapezoidal membership function [a, b, c, d] was fitted per category on percentile criteria, with cores at b = P25 and c = P75 across all training-set thresholds. The categories follow the Clark scheme at 25, 40, 55, 70 and 90 dB HL [@clark1981], the convention in most clinical reporting. WHO's own grade tables use five categories at 20 dB steps [@who1991; @who1997] and its 2021 revision uses seven at 15 dB steps [@who2021]; the 2021 schema was validated alongside and is reported as a companion analysis."""),

# ---------------------------------------------------------------- Ceriani
("""Machine-learning classifiers predict the severity grade directly but predict the same crisp categories, and their internal representations are not inspectable [@achakulvisut2025; @ceriani2025].""",
 """Machine-learning classifiers predict the severity grade directly but predict the same crisp categories, and their internal representations are not inspectable [@achakulvisut2025]. Preclinical work in the same vein detects cochlear synaptopathy in mice from auditory brainstem responses [@ceriani2025], which is a different task from grading a human audiogram."""),

# ---------------------------------------------------------------- Suen
("""Inter-aural asymmetry, the maximum absolute threshold difference across frequencies, was fuzzified into Symmetric (≤15 dB), Mildly Asymmetric (16–30 dB), Moderately Asymmetric (31–45 dB) and Severely Asymmetric (>45 dB), with the 15 dB threshold of clinical significance as a boundary [@suen2021].""",
 """Inter-aural asymmetry was fuzzified into Symmetric (≤15 dB), Mildly Asymmetric (16–30 dB), Moderately Asymmetric (31–45 dB) and Severely Asymmetric (>45 dB). The operational criterion is the maximum absolute difference across frequencies, which is more sensitive than either definition applied by Suen et al., who used a pure-tone-average difference above 15 dB and a contiguous-frequency criterion [@suen2021]; no standard audiometric criterion for asymmetry exists, and prevalence estimates vary several-fold with the definition chosen."""),

# ---------------------------------------------------------------- FIS / asymmetry redesign
("""A Mamdani-type fuzzy inference system [@mamdani1975] was constructed with 48 expert-derived rules in four functional groups: 12 severity rules mapping fuzzified thresholds to the severity output, 14 configuration rules classifying audiogram shape from slope and notch, 12 asymmetry rules, and 10 mixed-loss rules for complex multi-factor presentations.

All validation metrics were computed on individual ears under a single-ear protocol. Only the ear under test was supplied to the system, so the inter-aural asymmetry input was zero; the asymmetry-anchor rule presumes bilateral input and was therefore omitted, leaving a 47-rule base. The deployed web application supplies both ears and retains the full 48-rule base.""",
 """A Mamdani-type fuzzy inference system [@mamdani1975] was constructed with 42 expert-derived rules in three functional groups: 12 severity rules mapping fuzzified thresholds to the severity output, 14 configuration rules classifying audiogram shape from slope and notch, and 4 complex-interaction rules for contour presentations the severity group does not capture. A further 12 rules map inter-aural asymmetry to a separate referral output rather than to severity.

Decoupling asymmetry from severity is a deliberate design choice. Asymmetry between ears is an indication to investigate unilateral pathology, not evidence that the poorer ear hears less well, so it produces a referral recommendation (none, routine, expedited or urgent) while each ear is graded on its own thresholds. The 42-rule base is used for both single-ear and bilateral input, so the validated configuration and the deployed one coincide. All validation metrics were computed on individual ears under a single-ear protocol, in which the asymmetry input is zero and the referral output is correspondingly inert."""),

# ---------------------------------------------------------------- 2021 companion: methods
("""## Evaluation Metrics""",
 """## Comparator Schemas

The framework is schema-agnostic: the categories are a labelling convention, and the same construction applies to any of them. To separate the method from the convention, the entire pipeline was rebuilt under the WHO 2021 schema (seven categories, boundaries at 20, 35, 50, 65, 80 and 95 dB HL) using the same cohort, split, percentile-core fitting, Ruspini construction and calibration procedure, so the two arms differ only in their classification schema. Both were evaluated on the same held-out ears. The six-category system was additionally scored against the 2021 reference, which quantifies the cost of a mismatch between the fitted categories and the boundaries being claimed.

## Evaluation Metrics"""),

# ---------------------------------------------------------------- 2021 companion: results
("""## Decision-Curve Analysis""",
 """## Validation Under the WHO 2021 Schema

Rebuilt under the 2021 schema, the framework performed better on every metric except raw overall agreement (Table 4). Weighted kappa was 0.959 against 0.946, mean absolute error 3.74 dB against 4.35 dB, and Spearman's rho 0.844 against 0.812. Borderline agreement was 88.0%, and that figure is measured over a harder population: the 2021 boundaries place 29.5% of test ears within ±5 dB of a boundary, against 18.7% under the six-category scheme. Clear-case agreement was 99.4%.

Scoring the six-category system against the 2021 reference returned kappa 0.875, so construction and schema must match. The performance difference between the arms reflects the uniformity of the 2021 boundaries rather than any change to the inference method, since the cores, the partition and the calibration procedure were identical.

## Decision-Curve Analysis"""),

# ---------------------------------------------------------------- Bland-Altman correction
("""Bland-Altman analysis (Figure 2a) gave a mean difference of +1.9 dB with 95% limits of agreement −8.6 to +12.3 dB.""",
 """Bland-Altman analysis (Figure 2a) compared the FAI with PTA-4 after mapping the index onto the decibel scale through a linear transfer fitted on the training partition, FAI = 0.890 x PTA + 3.11 (r = 0.887). The mean difference was +0.25 dB with 95% limits of agreement −11.2 to +11.7 dB. A proportionate bias was present, the difference widening by 0.13 dB per decibel of mean level, so agreement is closest in the mild range and loosest at the extremes."""),

("""## Decision-Curve Analysis

FAI-based referral maintained net benefit comparable to PTA-4-based referral across the whole threshold-probability range for both outcomes, and both exceeded treat-all at every threshold (Figure 3). For any hearing loss at a 10% referral threshold, net benefit was 0.126 for the FAI against 0.131 for PTA-4 and 0.034 for treating all; for moderate-or-worse loss at a 20% threshold it was 0.029 against 0.038, with treat-all at −0.202. The small differences favour the crisp markers, which are defined on the outcome itself. The substantive finding is that adopting the graded index does not sacrifice decision utility.""",
 """## Decision-Curve Analysis

FAI-based referral maintained net benefit comparable to PTA-4-based referral across the whole threshold-probability range for both outcomes, and both exceeded treat-all at every threshold (Figure 3). For any hearing loss at a 10% referral threshold, net benefit was 0.126 for the FAI against 0.131 for PTA-4 and 0.034 for treating all. The small differences favour the crisp markers, which are defined on the outcome itself; the substantive finding is that adopting the graded index does not sacrifice decision utility."""),

# ---------------------------------------------------------------- Discussion: schema finding
("""## Clinical Implications""",
 """## The Classification Schema Is a Parameter

Rebuilding the pipeline under the WHO 2021 schema improved every metric except raw overall agreement. That result matters for how the framework should be described. The fuzzy construction is not tied to the 25/40/55/70/90 boundaries, which trace to Clark and ANSI rather than to WHO; the same cores, partition and calibration applied to the 2021 boundaries at 20/35/50/65/80/95 dB produced a better-calibrated system with a lower absolute error.

Two consequences follow. First, the framework should be presented as schema-agnostic, with the classification convention treated as a parameter rather than a premise. Second, agreement figures are only interpretable alongside the schema they were computed against: scoring the six-category system against the 2021 reference returned kappa 0.875, a penalty paid purely for a mismatch between the fitted categories and the boundaries being claimed. Any future change to WHO's grade table would require recalibration but not redesign, which is a property of the architecture rather than of these particular parameters.

## Clinical Implications"""),

# ---------------------------------------------------------------- Discussion: asymmetry
("""## Generalizability and Future Directions""",
 """## Asymmetry as a Referral Flag

Inter-aural asymmetry was decoupled from the severity output during this work. The rule base previously allowed asymmetry to upgrade severity, so an ear with a pure-tone average of 55 dB could be reported as moderately severe because the contralateral ear differed. Asymmetry is a referral indicator, not an amplifier of peripheral loss, and the revised rule base now emits a referral recommendation instead.

This change is neutral for every figure reported here, because the single-ear protocol pins the asymmetry input to zero and the referral output is correspondingly inert; the test-set index is unchanged. It does change the deployed bilateral behaviour, and it removes a discrepancy that previously existed between the validated configuration and the deployed one, which ran 48 rules against the 47 validated.

## Generalizability and Future Directions"""),

# ---------------------------------------------------------------- Discussion: limitations
("""Only air-conduction thresholds were used, so the framework grades combined air-conduction loss and cannot separate sensorineural from conductive or mixed components.""",
 """Only air-conduction thresholds were used, so the framework grades combined air-conduction loss and cannot separate sensorineural from conductive or mixed components; the four complex-interaction rules therefore capture air-conduction contour rather than pathophysiological mixed loss."""),

# ---------------------------------------------------------------- Table 2 baseline
("""| Uniform reference | — | 0.0000 | 86.9% | 0.8333 | 1.7918 | 0.7027 |""",
 """| Majority-class baseline | — | 0.0000 | 86.9% | 0.8333 | 1.7918 | 0.7027 |"""),

("""Note. The FAI row scores the six Ruspini memberships evaluated at the primary threshold as a probability distribution. ECE, expected calibration error. The ordinal logistic's exact reconstruction shows that the reference label is a deterministic thresholding of the pure-tone average, so agreement metrics cannot discriminate between models on this task.""",
 """Note. The FAI row scores the six Ruspini memberships evaluated at the primary threshold as a probability distribution. ECE, expected calibration error. The baseline assigns every ear to the majority class, which is why its accuracy is 86.9% while its Brier score of 0.8333 and log loss of 1.7918 are those of a uniform distribution over six classes; a uniform classifier would score 16.7% accuracy. The ordinal logistic's exact reconstruction shows that the reference label is a deterministic thresholding of the pure-tone average, so agreement metrics cannot discriminate between models on this task."""),
]

applied, missed = 0, []
for old, new in EDITS:
    if old in s:
        s = s.replace(old, new, 1); applied += 1
    else:
        missed.append(old[:72].replace("\n", " "))

out.write_text(s, encoding="utf-8")
print(f"  applied {applied}/{len(EDITS)} edits -> {out.name}")
for m in missed:
    print(f"    MISSED: {m}...")
sys.exit(0 if not missed else 1)
