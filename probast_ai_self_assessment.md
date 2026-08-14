# FAI Manuscript — Self-Assessment Against PROBAST+AI and JAMA AI-Use Guidance

**Date:** 14 August 2026
**Manuscript:** "Fuzzy Audiometric Index (FAI)" — submission to *Ear & Hearing*
**Tools applied:** PROBAST+AI (Moons et al., *BMJ* 2025;388:e082505) and JAMA Network "Guidance for Acceptable Use of AI" (Flanagin, Perlis, Bibbins-Domingo, *JAMA* 2026)

---

## Part A. JAMA AI-Use Guidance — Compliance Check

| Use type | JAMA verdict | Our status | Action |
|---|---|---|---|
| Research | Yes — describe in Methods, follow reporting guidance, full responsibility | Partially compliant — Methods describe the analysis but no AI-assistance disclosure | Add sentence in Methods |
| Literature search | Yes — describe in Methods (research reports) + check accuracy | No disclosure present | Add to Methods |
| Manuscript preparation | Yes — describe in Acknowledgment section | ❌ **Missing** — Acknowledgements has no AI disclosure | Add AI-use statement to Acknowledgements |
| Grammar/spelling check | Yes — no disclosure needed | Compliant | — |
| Translation | Yes — with caution | N/A | — |
| Drafting letters/online comments | No | N/A (we do not draft journal letters) | — |
| Drafting opinion manuscripts | No | N/A | — |
| Bibliographic references | **Discouraged** — accuracy/integrity risk | ⚠️ References were AI-compiled; must verify all 24 | **Verification pass needed** |
| Data/graphic visualization | Yes — describe in figure legend | Compliant (figures from real data) | Optionally note in legends |
| Clinical images/illustrations | No | N/A (no clinical images) | — |
| Clinical video/audio | No | N/A | — |
| Peer review | No | N/A | — |
| Author response to reviewers | No | N/A (future) | Note: do NOT use AI for responses |

**Key gap:** the manuscript was prepared with substantial AI assistance but the
Acknowledgements section (line 259) contains no AI-use disclosure. JAMA/ICMJE
require: "the use is fully described in the Acknowledgment section and authors
check for accuracy and take full responsibility for all content."

---

## Part B. PROBAST+AI — Model Development (16 signalling questions)

### Domain 1 — Participants and data sources

| # | Signalling question | Answer | Evidence in manuscript |
|---|---|---|---|
| 1.1 | Were appropriate data sources used? | ✅ Yes | NHANES, the reference national survey for audiometry; three cycles with adults 20–69 y |
| 1.2 | Was an appropriate study design used? | ✅ Yes | Population-based cross-sectional; secondary analysis of de-identified public data |
| 1.3 | Did inclusions/exclusions result in a representative dataset? | ⚠️ Probably yes | 10,889 → 9,832 participants (90%); exclusion driven by sentinels (666/777/888/999) not clinical selection. Report flow diagram. |

### Domain 2 — Predictors

| # | Signalling question | Answer | Evidence |
|---|---|---|---|
| 2.1 | Were predictors defined and assessed similarly for all participants? | ✅ Yes | Same 7-frequency air-conduction protocol across cycles; standardised sentinel handling |
| 2.2 | Was preprocessing similar for all participants? | ✅ Yes | Identical cleaning (sentinel → missing, clip −10..120) applied uniformly |
| 2.3 | Were predictor assessments made without knowledge of outcome data? | ✅ Yes | Audiometry measured objectively; outcomes derived from same thresholds but fuzzy labels from FIS, not WHO cutoffs on PTA |
| 2.4 | Were predictors available at time of intended use? | ✅ Yes | Audiogram thresholds available in clinic at the moment of use |

### Domain 3 — Outcomes

| # | Signalling question | Answer | Evidence |
|---|---|---|---|
| 3.1 | Were outcomes defined and assessed appropriately? | ✅ Yes | WHO PTA-4 six-grade severity, the audiology reference standard |
| 3.2 | Were outcomes assessed similarly for all participants? | ✅ Yes | Single formula, applied uniformly |
| 3.3 | Were outcome assessments made without use of predictor data? | ⚠️ Partial | PTA-4 is a mean of 4 of the 7 predictor frequencies — outcome shares data with predictors by design; disclosed |
| 3.4 | Was the time interval between predictor and outcome appropriate? | ✅ Yes | Same audiogram (same session) |

### Domain 4 — Analyses

| # | Signalling question | Answer | Evidence |
|---|---|---|---|
| 4.1 | Was sample size reasonable? | ✅ Yes | 19,568 ears / 10,889 participants — large for this setting |
| 4.2 | Were continuous/categorical predictors handled appropriately? | ✅ Yes | Continuous thresholds fuzzified via trapezoidal MFs; slope/notch/asymmetry as derived features |
| 4.3 | Were participants with missing/censored data handled appropriately? | ✅ Yes | Ears with any sentinel/missing threshold excluded; proportion reported (10%) |
| 4.4 | If class imbalance methods used, were predictions recalibrated? | ✅ N/A | No imbalance correction used; borderline analysis stratified instead |
| 4.5 | Were methods used to address potential overfitting? | ⚠️ Partial | MFs optimised on training set only; but see leakage note below — **ear-level split** |

---

## Part C. PROBAST+AI — Model Evaluation (18 signalling questions)

### Domain 1 — Participants and data sources

| # | Signalling question | Answer | Evidence |
|---|---|---|---|
| 1.1 | Were appropriate data sources used? | ✅ Yes | Same NHANES cycles |
| 1.2 | Was an appropriate study design used? | ✅ Yes | Internal validation with held-out test set |
| 1.3 | Did inclusions/exclusions result in a representative dataset? | ⚠️ Probably yes | Same as development |

### Domain 2 — Predictors

| # | Signalling question | Answer | Evidence |
|---|---|---|---|
| 2.1–2.4 | (same as development) | ✅ Yes | Consistent preprocessing across train/test |

### Domain 3 — Outcomes

| # | Signalling question | Answer | Evidence |
|---|---|---|---|
| 3.1–3.4 | (same as development) | ✅ Yes | Same outcome definition |

### Domain 4 — Analyses

| # | Signalling question | Answer | Evidence |
|---|---|---|---|
| 4.1 | Was evaluation based on only apparent performance avoided? | ✅ Yes | Independent 20% held-out test set (3,914 ears) |
| 4.2 | Was sample size reasonable? | ✅ Yes | 3,914 test ears |
| 4.3 | Were missing/censored data handled appropriately? | ✅ Yes | 0/3,914 dropped after the batched-classifier fix |
| 4.4 | If imbalance correction used, evaluated without correction? | ✅ N/A | No correction applied |
| 4.5 | If data splitting used, was data leakage avoided? | ❌ **RISK FOUND** | **88.3% of test participants also contributed ears to training** (ear-level split, not participant-level). Bilateral ears are highly correlated (94.9% symmetric ≤15 dB), so this overstates independence |
| 4.6 | If resampling used, were all development steps replicated? | ✅ N/A | Single hold-out split, not resampling |
| 4.7 | Was predictive performance evaluated appropriately (calibration, discrimination, net benefit)? | ✅ Yes | κ, accuracy, Spearman ρ, MAE, Bland-Altman (calibration), boundary-distance curve |

---

## Part D. Actions Required (priority order)

1. **Fix the leakage (CRITICAL):** re-run validation with a **participant-level split** —
   all ears of a participant go to the same side. Script written
   (`scripts/pipeline_participant.py`), running now. This gives the honest headline
   numbers (κ, accuracy, etc.) that survive reviewer scrutiny.
2. **Verify all 24 references** (JAMA: AI-compiled references "discouraged").
   Run `academic-verify` / CrossRef / PubMed checks on each entry.
3. **Add AI-use disclosure** to:
   - Acknowledgements (manuscript_eh.qmd) — required by JAMA/ICMJE
   - Methods (research + literature search description)
   - Cover letter (one line)
   - Note: blinded build strips Acknowledgements — ensure the disclosure survives
     via Methods/cover letter for the blinded version
4. **Report the exclusion flow** (10,889 → 9,832 → 19,568 ears) more explicitly
   in Methods (PROBAST+AI 1.3).
5. **Re-render + commit + push** all deliverables after fixes.

---

## Part E. Expected effect of participant-level split — RESULT

The ear-level split (88.3% of test participants also in training) modestly
inflated performance. The participant-level re-run (`scripts/pipeline_participant.py`,
seed 42, 15,656 train / 3,912 test ears from 7,866 / 1,966 participants, zero
overlap) gives the honest numbers:

| Metric | Ear-level split | **Participant-level split** |
|---|---|---|
| Weighted κ | 0.932 | **0.931** |
| Overall accuracy | 95.8% | **94.7%** |
| Clear-case accuracy | 98.4% | **98.1%** |
| Borderline accuracy | 84.9% | **79.8%** |
| MAE | 5.08 dB | **5.01 dB** |
| Spearman ρ | 0.802 | **0.807** |
| Bland-Altman | bias +1.0, LoA −11.3..13.2 | **bias +1.2, LoA −10.9..13.2** |
| Calibrated thresholds | [22.2, 32.9, 50.9, 67.8, 83.7] | [21.9, 34.6, 52.5, 70.6, 74.1] |

**Interpretation:** the headline κ is essentially unchanged (0.932 → 0.931) — the
FAI's core agreement is robust to the leakage fix. The meaningful change is
**borderline accuracy 84.9% → 79.8%** — the borderline zone is where the correlated-
ears effect mattered most. The submission should report the participant-level
numbers as primary, with the ear-level figures noted (if at all) as a sensitivity
analysis.

**Note on threshold calibration:** the participant-level calibration produced
[21.9, 34.6, 52.5, 70.6, 74.1] — the severe/profound gap is only 3.5 points
(70.6 → 74.1), a tight squeeze driven by the sparse severe+ profound training
sample. The 2-point degenerate-guard did not trigger, but reviewers may query the
narrow severe–profound interval; consider reporting this as a limitation or
fixing severe/profound thresholds to stable values (e.g. 75, 90).

