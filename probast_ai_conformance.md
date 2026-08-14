# FAI Manuscript — PROBAST+AI Conformance Verdict

**Assessment date:** 14 August 2026
**Tool:** PROBAST+AI (Moons et al., *BMJ* 2025;388:e082505) — 16 development + 18
evaluation signalling questions, four domains (participants & data sources,
predictors, outcomes, analyses).
**Verdict scale:** ✅ Conforms · ⚠️ Partial (conforms with noted caveat) ·
❌ Does not conform · ➖ N/A

---

## Part 1 — Model Development (16 signalling questions)

### Domain 1: Participants and data sources

| # | Signalling question | Verdict | Evidence in manuscript |
|---|---|---|---|
| 1.1 | Were appropriate data sources used? | ✅ | NHANES national survey, three cycles with adult (20–69 y) audiometry; de-identified public data |
| 1.2 | Was an appropriate study design used? | ✅ | Population-based cross-sectional secondary analysis; appropriate for model development |
| 1.3 | Did inclusions/exclusions result in a representative dataset? | ⚠️ | 10,889 → 9,832 participants (90%) after sentinel exclusion; exclusion is completeness-driven, not clinical, but a formal flow diagram is absent (only counts reported) |

### Domain 2: Predictors

| # | Signalling question | Verdict | Evidence |
|---|---|---|---|
| 2.1 | Predictors defined & assessed similarly for all participants? | ✅ | Same 7-frequency air-conduction protocol, both ears, all cycles; standardised sentinel handling |
| 2.2 | Preprocessing similar for all participants? | ✅ | Identical cleaning pipeline (sentinel→missing, clip −10..120 dB, canonical8) |
| 2.3 | Predictor assessments made without knowledge of outcome data? | ✅ | Audiometry is an objective measurement; predictors (thresholds, slope, notch, asymmetry) computed before any grade assignment |
| 2.4 | Predictors available at time of intended use? | ✅ | Audiogram thresholds are exactly what the clinician has at point of use |

### Domain 3: Outcomes

| # | Signalling question | Verdict | Evidence |
|---|---|---|---|
| 3.1 | Outcomes defined & assessed appropriately? | ✅ | WHO PTA-4 six-grade severity — the audiology reference standard |
| 3.2 | Outcomes assessed similarly for all participants? | ✅ | Single PTA-4 formula applied uniformly |
| 3.3 | Outcome assessments made without use/knowledge of predictor data? | ⚠️ | **Inherent design limitation:** the outcome (PTA-4 grade) is the mean of 4 of the 7 predictor frequencies (500, 1k, 2k, 4k) — outcome shares data with predictors by construction. Disclosed in Limitations ("agreement with PTA-4 is partly by construction") |
| 3.4 | Time interval between predictor & outcome appropriate? | ✅ | Same audiogram, same session — contemporaneous by design |

### Domain 4: Analyses

| # | Signalling question | Verdict | Evidence |
|---|---|---|---|
| 4.1 | Sample size reasonable? | ✅ | 19,568 ears / 10,889 participants — large for this setting |
| 4.2 | Continuous/categorical predictors handled appropriately? | ✅ | Continuous thresholds fuzzified via trapezoidal MFs; no arbitrary categorisation; slope/notch/asymmetry as derived continuous features |
| 4.3 | Missing/censored data handled appropriately? | ⚠️ | Complete-case analysis (ears with any sentinel/missing threshold excluded); exclusion count reported but no imputation/sensitivity analysis for the 10% excluded |
| 4.4 | If class-imbalance methods used, were predictions recalibrated? | ➖ | No imbalance correction used; borderline analysis stratified instead — N/A |
| 4.5 | Methods to address overfitting? | ✅ | MF optimisation on training set only; held-out test; 2.0 dB overlap enforcement; label thresholds calibrated on training set only |

---

## Part 2 — Model Evaluation (18 signalling questions)

### Domain 1: Participants and data sources (same as development)

| # | Signalling question | Verdict |
|---|---|---|
| 1.1 | Appropriate data sources? | ✅ |
| 1.2 | Appropriate study design? | ✅ Internal validation with held-out test set |
| 1.3 | Representative dataset? | ⚠️ (same caveat as development) |

### Domain 2: Predictors (same as development)

| # | Signalling question | Verdict |
|---|---|---|
| 2.1–2.4 | (identical to development) | ✅ |

### Domain 3: Outcomes (same as development)

| # | Signalling question | Verdict |
|---|---|---|
| 3.1–3.4 | (identical to development) | ✅ (3.3 ⚠️ outcome-predictor overlap as above) |

### Domain 4: Analyses

| # | Signalling question | Verdict | Evidence |
|---|---|---|---|
| 4.1 | Evaluation based on only apparent performance avoided? | ✅ | Independent 20% held-out test set (3,914 ears); all metrics from test set |
| 4.2 | Sample size reasonable? | ✅ | 3,914 test ears |
| 4.3 | Missing/censored handled appropriately? | ✅ | 0/3,914 dropped after batched-classifier fix; all ears classified |
| 4.4 | If imbalance correction used, evaluated without correction? | ➖ | No correction applied — N/A |
| 4.5 | **If data splitting used, was data leakage avoided?** | ❌ | **Ear-level split:** 88.3% of test participants also contributed ears to training (3,108 of 3,519). Bilateral ears are highly correlated (94.9% symmetric ≤15 dB) → inflated apparent performance. **Fixed** by participant-level re-run (κ 0.931, borderline 79.8%) — manuscript must adopt these numbers |
| 4.6 | If resampling used, were all dev steps replicated? | ➖ | Single hold-out split, no resampling — N/A |
| 4.7 | Predictive performance evaluated appropriately (calibration, discrimination, net benefit)? | ⚠️ | Discrimination ✅ (κ, accuracy, ρ); Calibration ✅ (Bland-Altman, MAE); **Net benefit ❌** — no decision-curve analysis (DCA) |

---

## Part 3 — Summary Verdict

| Dimension | Verdict | Notes |
|---|---|---|
| Participants & data sources | ✅ (1 partial) | Add participant-flow diagram (1.3) |
| Predictors | ✅ | Fully conforms |
| Outcomes | ⚠️ (3.3) | Outcome derived from predictor data by construction — disclosed, but reviewers will probe |
| Analyses — development | ✅ (1 partial) | Missing-data handling could be stronger (4.3) |
| Analyses — evaluation | ❌ (4.5) + ⚠️ (4.7) | **Data leakage must be fixed**; net-benefit analysis missing |

**Bottom line: 27 of 34 questions conform or are N/A; 5 partial; 2 issues of substance —**
1. ❌ **4.5 data leakage (ear-level split)** — the manuscript's headline numbers
   (κ 0.93, 95.8%, 84.9% borderline) were computed on a split where 88.3% of test
   participants were also in training. The participant-level re-run
   (`scripts/pipeline_participant.py`) gives the honest numbers: κ 0.931,
   overall 94.7%, clear 98.1%, **borderline 79.8%**, MAE 5.01, ρ 0.807,
   bias +1.2 (LoA −10.9..13.2). **The submission must switch to these.**
2. ⚠️ **3.3 outcome–predictor overlap** — PTA-4 (outcome) is built from the same
   thresholds the FIS consumes; agreement is partly by construction. Already
   disclosed in Limitations; keep and make it more prominent.
3. ⚠️ **4.7 net benefit** — no decision-curve analysis. Either add a DCA or state
   why it is not applicable for a classification-vs-reference design.

## Part 4 — Associated JAMA AI-use compliance (from Flanagin et al., JAMA 2026)

| Requirement | Verdict | Action |
|---|---|---|
| AI use described in Acknowledgment | ✅ APPLIED | AI-use disclosure added to Acknowledgements (manuscript_eh.qmd) |
| AI use described in Methods (research/lit search) | ✅ APPLIED | "Role of artificial intelligence" paragraph added to Methods |
| Bibliographic references accuracy | ✅ APPLIED | 3 fabricated refs removed (chen2017, zadoush2020, miller2004); 4 unverified unused refs removed (adeyemo2006, bright2023, swanepoel2021, lee2025 re-checked OK); Stuart 1991 (PMID 1877901) added as real test–retest citation |
| Grammar/spelling AI | ✅ | No disclosure needed |
| Cover letter | ✅ APPLIED | One-line AI disclosure added to cover letter |

## Part 5 — Fix status (applied 14 Aug 2026, commit follows)

1. **Participant-level split (PROBAST+AI 4.5)** — `scripts/pipeline_participant.py`
   run; all manuscripts, report, tables, deck, cover letter, and figures updated
   to the honest numbers: κ 0.931, overall 94.7%, clear 98.1%, borderline 79.8%,
   MAE 5.01, ρ 0.807, bias +1.2 (LoA −10.9..13.2), n = 3,912 test ears from
   1,966 participants.
2. **AI-use disclosure** — added to Acknowledgements, Methods, and cover letter
   (JAMA/ICMJE compliant). Blinded version keeps the Methods disclosure.
3. **Fabricated references** — removed from references.bib and manuscript text;
   Stuart 1991 (real, PMID 1877901) now supports the test–retest claim.
4. **Participant-flow diagram** — split described in Methods as participant-level
   with counts (1.3 partial remains: a formal CONSORT-style figure could still be
   added if the journal requests it).
5. **Net-benefit statement (4.7)** — Methods now state why decision-curve analysis
   was not performed (graded classifier without a single decision threshold).

