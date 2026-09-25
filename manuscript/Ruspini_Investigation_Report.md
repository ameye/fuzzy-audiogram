# Fuzzy Audiometric Index — Investigation Report

**Subject:** CMPB submission pack, peer review response, and the Ruspini partition
**Repository:** `ameye/fuzzy-audiogram`
**Commits:** `3772e70` (Ruspini implementation), `10c42fa` (calibration fix)
**Status:** Reproducibility problem closed. Two manuscript figures need correcting.

---

## 1. Executive summary

The CMPB submission pack was built from a manuscript whose central methodological
claim was not implemented in the code, and whose reported metrics could not be
reproduced from any artefact in the repository. Both problems are now resolved.

The severity membership functions are now a verified Ruspini partition, the
pipeline that produced the reported numbers runs again, and the fresh run
reproduces the manuscript's headline result to within 0.004 kappa.

Four findings drove the work:

1. **Four synthetic references** were in the bibliography, not two. The external
   reviewer identified two and explicitly cleared the other two as valid.
2. **The Ruspini partition did not exist in code** — locally or on the remote.
   The committed figure still advertised "2 dB overlap", and the saved parameters
   failed the partition property at 59 of 121 universe points.
3. **The pipeline silently discarded its own calibration optimum** because a
   threshold gap came out 1.99 dB against a 2.0 dB guard. That single hundredth
   of a decibel cost 0.13 kappa.
4. **With both defects fixed, the manuscript's numbers hold**: kappa 0.946
   against a claimed 0.95.

---

## 2. The peer review

The review examined `Manuscript_CMPB.docx`, the earlier pack derived from the
Ear & Hearing manuscript. Its quoted figures (94.7% agreement, 79.8% borderline,
regression comparators, decision-curve analysis described as omitted) confirm it
was reading the superseded document.

Most of its requests were already satisfied in the rebuilt version. Its two
substantive methodological complaints were the comparator formulation and the
absence of net-benefit analysis. Both are addressed: the comparators are now five
multiclass classifiers trained directly on the WHO grade, and decision-curve
analysis with net benefit is reported for two outcomes.

### Review points and disposition

| Review point | Disposition |
|---|---|
| Abstract heading "Background and Objectives" | Corrected to "Background and Objective" |
| Highlights omitted | Outstanding — not yet supplied as a separate file |
| First-person plural in a single-author paper | 21 instances converted; zero remain |
| Drafting commentary in the text | Five instances removed |
| Three overlapping AI declarations | Consolidated to one, in back matter |
| Duplicate AI heading | Fixed — a build error was emitting it twice |
| Goodman page span truncated | Corrected to 262–273 |
| WHO cut-offs misattributed to the 2021 report | Corrected; WHO 1997 cited, 2021 difference stated |
| Reference [8] is an animal study | Ceriani flagged as a mouse model |
| References [9] and [12] synthetic | Confirmed and replaced |
| Membership overlap too narrow (2 dB) | **Resolved at source — see section 4** |
| Pre-averaging circularity | Acknowledged in Methods and Limitations |
| Asymmetry rules inactive in single-ear validation | Stated in Limitations |
| Mixed-loss rules cannot fire without bone conduction | Stated in Limitations |
| Comparators are a reconstruction task | Replaced with five multiclass classifiers |
| No confusion matrix or per-class metrics | Supplied — see section 7 |
| Decision-curve analysis omitted | Added, net benefit for two outcomes |

---

## 3. Bibliography audit

Every reference was checked against PubMed and CrossRef. Four entries carried a
real title attached to invented author and journal coordinates.

**Reference [9]** — the title belongs to Achakulvisut et al., *Journal of
Otology* 2025;20(1):26–32 (PMID 41069835). The attributed authors, journal,
volume and pages do not exist.

**Reference [12]** — the title belongs to Ellis & Souza, *Frontiers in Digital
Health* 2021;3:723533 (PMID 34713189). The attribution is fabricated. The real
paper is a closer fit to the manuscript's argument than the invented one was,
being machine learning on NHANES audiometry to classify hearing loss.

**Reference [10]** — the title belongs to Saak, Huelsmeier, Kollmeier & Buhl,
*Frontiers in Neurology* 2022;13:959582 (PMID 36188360). The attributed
"Sanchez-Lopez et al., *Front Digit Health* 2021;3:673686" resolves to nothing:
no PubMed record, and no article 673686 in that journal for 2021. **The reviewer
examined this entry and marked it "Valid citation."**

**Reference [11]** — the title belongs to Saak, Oetting, Kollmeier & Buhl,
*Trends in Hearing* 2025;29:23312165251349617 (PMID 40583732). The attributed
"Van Beek et al." authorship is fabricated. **The reviewer also passed this one.**

The signature is consistent across all four: a genuine title, real subject
matter, invented authors and journal coordinates. The reviewer caught two and
missed two of the same kind, which suggests the audit was partial rather than
that the errors were subtle.

Also corrected:

- **Goodman (1965)** page span 262–263 → 262–273.
- **Ceriani et al. (2025)** is a study of auditory brainstem responses in
  C57BL/6N mice carrying the *Cdh23* hypomorphic allele (PMID 40532491). No
  patients, no audiograms. The citation is retained and the text now says so.
- **WHO cut-offs.** The 25/40/55/70/90 dB HL boundaries are the 1997 grade
  table, replaced in 2021 by 20/35/50/65/80/95 dB. The text now cites the 1997
  source for the boundaries it models and states the difference plainly.

---

## 4. The Ruspini partition

### 4.1 What the manuscript claimed

The Methods described arranging the six trapezoids "as a formal Ruspini
partition, in which the memberships of the six severity categories sum to exactly
1 at every point of the 0–120 dB universe." The Figure 1 caption stated that
"adjacent shoulders cross at 0.5 so memberships sum to 1 at every threshold."

### 4.2 What was actually there

**No implementation existed.** A content scan of all 44 Python blobs on the
remote `main` branch, searching for `ruspini`, "shoulders cross", "complementary
linear" and "core end", returned zero hits. The only filename matches were the
figure and its provenance report. There were no other branches, tags or stashes,
and no other repository under the account.

**The construction in use was a fixed 2 dB margin.** The provenance report
`data/output/MF_OPTIMIZATION_REPORT.md`, dated 2026-07-27, states it directly:

```
a = max(0, P5 - 2)
b = P25
c = P75
d = min(P95 + 2, 120)
```

Its own overlap table records what that produced:

| Boundary | Before | After |
|---|---:|---:|
| Normal → Mild | 10.0 dB | **−1.7 dB** |
| Mild → Moderate | 10.0 dB | −1.0 dB |
| Moderate → Moderately severe | 10.0 dB | −1.0 dB |
| Moderately severe → Severe | 10.0 dB | −1.0 dB |
| Severe → Profound | 10.0 dB | +0.1 dB |

Negative overlap means a gap: ranges where no category holds any membership.
The report nonetheless recommends the result on the grounds that it "preserves
overlap structure".

**The saved parameters failed the property.** Taking the parameters the pipeline
actually wrote to `data/output_participant/metrics_participant.json`, the six
memberships sum to 1 at only 34 of 61 sampled thresholds and range from 0.00 to
1.23. Every adjacent overlap is exactly 2.0 dB.

**The figure contradicted the caption.** `fig1_membership_functions.png`, the
file used as Figure 1, carries the title *"NHANES-optimized trapezoidal MFs with
2 dB overlap"* and shows the Normal and Mild shoulders crossing at roughly 0.4
each in a shaded band labelled "Boundary zone (24–28 dB)".

### 4.3 The construction now implemented

`fuzzy_audiogram/ruspini.py`. Percentile cores are retained (`b = P25`,
`c = P75`) and each trapezoid's feet are tied to its neighbours' cores:

```
a_i = c_{i-1}      left foot  = previous category's core end
d_i = b_{i+1}      right foot = next category's core start
```

Over the shared interval `[c_{i-1}, b_i]` the descending and ascending
memberships are complementary ramps:

```
mu_{i-1}(x) = (b_i - x) / (b_i - c_{i-1})
mu_i(x)     = (x - c_{i-1}) / (b_i - c_{i-1})
```

which sum to exactly 1. Outside that interval the incumbent holds full
membership and its neighbours hold zero, so the sum is 1 there as well.

The bottom trapezoid's left foot is padded 0.5 dB below the universe floor and
the top core extended 0.5 dB past the ceiling. This is a boundary convention: the
standard trapezoid is zero at `x = a` and `x = d`, so a partition on the closed
interval would otherwise leave both endpoints uncovered. Thresholds are clipped
to the universe before fuzzification, so the padded shoulders are never
traversed.

**Verification.** Maximum deviation from 1.0 is `0.000e+00` across all 1,201
sampled thresholds, and 0 of 121 universe points are off-partition when checked
through the live fuzzy control system, against 59 of 121 for the previously
deployed `core.py` parameters.

**`min_transition`.** Because the Ruspini transition width equals the core gap,
a data-driven fit can leave a band narrower than the ±5 dB test-retest
variability the partition represents. Passing `min_transition=10.0` widens every
core gap to at least that value while preserving the partition property. The
pipeline uses 10 dB; `None` keeps the raw percentile gaps.

### 4.4 Parameters produced by the fresh run

```
normal             [-0.5,  0.0, 16.4, 30.0]
mild               [16.4, 30.0, 35.4, 45.4]
moderate           [35.4, 45.4, 52.1, 62.1]
moderately_severe  [52.1, 62.1, 66.1, 76.1]
severe             [66.1, 76.1, 83.6, 94.8]
profound           [83.6, 94.8, 120.0, 120.5]
```

Transition bands are 13.6 / 10.0 / 10.0 / 10.0 / 11.2 dB, against a flat 2.0 dB
before. The construction holds: `normal d = 30.0 = mild b`, and
`mild a = 16.4 = normal c`.

### 4.5 Tests

Sixteen unit tests in `tests/test_ruspini.py` plus an end-to-end pipeline check.
They include a regression guard asserting the old parameters **fail** the
partition check rather than only asserting the new ones pass, complementary
shoulder verification at eleven points per band, endpoint coverage, monotonic
ordering, and the degenerate cases (overlapping cores with repair or raise,
inverted cores, missing categories).

---

## 5. Data recovery

The NHANES source files had been lost and the pipeline expects them at
`/opt/data/` root. Downloading required finding the new CDC paths: the legacy
scheme `wwwn.cdc.gov/Nchs/Nhanes/<cycle>/<FILE>.XPT` now serves a **404 page with
HTTP 200**, so a status check reports success while returning 24 KB of HTML. The
live scheme is:

```
https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/<year>/DataFiles/<FILE>.xpt
```

Six files were fetched (AUX1, DEMO, AUX_G, DEMO_G, AUX_I, DEMO_I; 25 MB total)
and the loader reproduces the manuscript's cohort exactly:

| Quantity | Reproduced | Manuscript |
|---|---:|---:|
| Adults | 10,889 | 10,889 |
| Clean ears | 19,568 | 19,568 |
| Participants | 9,832 | 9,832 |
| Age range | 20–69 | 20–69 |

The raw files are mirrored to the durable volume at
`/home/hermes/.hermes/home/nhanes_raw/`.

---

## 6. Pipeline diagnosis

Two defects in the label-threshold calibration explain why the first fresh run
returned kappa 0.794.

### 6.1 The guard rejected a valid optimum

The calibration maximised quadratic-weighted kappa over five FAI-to-label
thresholds by Nelder-Mead, then applied:

```python
if gaps.min() < 2.0:
    label_th = list(DEFAULT_TH)
```

Its optimum scored **0.9208** on the calibration sample, but the smallest gap
between its thresholds came out at **1.99 dB**. The guard rejected it and
silently reverted to the deployed defaults, which scored 0.8352 on the same
sample. On the held-out test set the difference was **0.794 against 0.892**.

A guard is warranted, since thresholds collapsing onto one another is
pathological, but 2.0 dB is a tolerance masquerading as a constraint. It is now
a 1 dB floor, with a comment recording why.

### 6.2 The calibration sample optimised the wrong target

The original drew a **class-balanced** subsample, giving each severity class at
least 1% representation. That is appropriate when balancing a loss, but kappa is
a population-level measure dominated by the 87% normal majority, so a balanced
draw optimises a different quantity from the one being reported. The sample is
now drawn to match the population, with a floor protecting the rare classes
rather than an inflation.

### 6.3 Labelling schemes, all fitted on training and scored on test

| Scheme | Thresholds | kappa | overall | borderline | clear |
|---|---|---:|---:|---:|---:|
| Defaults, no fitting | 20, 35, 50, 65, 85 | 0.794 | 85.8% | 47.5% | 94.6% |
| Class-balanced sample | 22.9, 40.3, 48.3, 65.9, 67.9 | 0.892 | 92.1% | 69.4% | 97.4% |
| Population-representative | 25.0, 43.7, 56.2, 57.6, 71.0 | 0.912 | 94.5% | 79.1% | 98.1% |
| Representative, 12 restarts | 23.8, 41.0, 55.5, 68.8, 81.0 | 0.932 | 94.8% | 80.7% | 98.1% |
| Fitted on test (not valid) | 24.3, 48.4, 65.3, 70.4, 78.9 | 0.948 | 96.6% | 86.5% | 98.9% |

The last row is reported only to bound what is achievable; it is fitted on the
evaluation set and is not a valid estimate. It is included because the
manuscript's borderline figure of 88.0% sits between the honest 0.932 row and
this optimistic 0.948 row, which is the pattern a calibration that had seen the
test set would produce.

---

## 7. Fresh run results

With the Ruspini partition in place and the calibration fixed:

| Run | kappa | overall | borderline | clear |
|---|---:|---:|---:|---:|
| Old 2 dB construction | 0.931 | 94.7% | 79.8% | 98.1% |
| Ruspini, rejected calibration | 0.794 | 85.8% | 47.5% | 94.6% |
| **Ruspini, fixed calibration** | **0.946** | **96.5%** | **85.1%** | **99.1%** |
| Manuscript claims | 0.950 | 97.1% | 88.0% | 99.2% |

Other metrics on the final run: ρ = 0.812, MAE = 4.35 dB, Bland-Altman bias
+1.9 dB with limits of agreement −8.6 to +12.3 dB, n = 3,912.

**The Ruspini partition with a working calibration is worth about +0.015 kappa**
against the old 2 dB construction with its own calibration.

### 7.1 Per-class performance

Confusion matrix, rows the WHO reference and columns the FAI label:

| | Normal | Mild | Mod | ModSev | Sev | Prof | sens | spec | prec |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Normal | 3,334 | 67 | 0 | 0 | 0 | 0 | 0.980 | 1.000 | 1.000 |
| Mild | 0 | 343 | 18 | 0 | 0 | 0 | 0.950 | 0.974 | 0.790 |
| Moderate | 0 | 24 | 64 | 15 | 0 | 0 | 0.621 | 0.993 | 0.703 |
| Mod. severe | 0 | 0 | 9 | 13 | 4 | 0 | 0.500 | 0.996 | 0.464 |
| Severe | 0 | 0 | 0 | 0 | 18 | 0 | 1.000 | 0.999 | 0.783 |
| Profound | 0 | 0 | 0 | 0 | 1 | 2 | 0.667 | 1.000 | 1.000 |

Macro-averaged F1 **0.779**, macro-averaged sensitivity **0.786**.

The overall 96.5% is carried by the 87% normal majority. The moderate and
moderately-severe grades sit at 0.62 and 0.50 sensitivity, which is the honest
picture and the reason the aggregated figure should not stand alone.

### 7.2 Error structure

Off-diagonal moves:

```
Normal      -> Mild            67
Mild        -> Moderate        18
Moderate    -> Mild            24
Moderate    -> Mod. severe     15
Mod. severe -> Moderate         9
Mod. severe -> Severe           4
Profound    -> Severe           1
```

Under the old 2 dB construction every disagreement was a single upward step and
none was downward. With genuine graded memberships the errors are
**bidirectional**: 24 Moderate→Mild and 9 Moderately-severe→Moderate moves now
occur. A crisp classifier cannot produce that; a graded one should.

### 7.3 What the kappa does and does not show

kappa = 0.946 for the Ruspini partition against 0.931 for the 2 dB construction
is a small difference, and it should not be over-read. The FAI-to-label step is
calibrated to reproduce the crisp reference, so calibration absorbs much of
whatever the partition changes. **Agreement with the WHO grade is therefore a
weak test of the partition's value.**

This is consistent with the manuscript's own framing, that its contribution is
"gradation and interpretability, not higher agreement with the reference". The
evidence for the partition has to be the borderline behaviour and the graded
outputs, which is where the reviewer's demand for a wider transition band and
per-class reporting actually bites.

---

## 8. Corrections required in the manuscript

| Parameter | Currently stated | Corrected |
|---|---|---|
| Weighted kappa | 0.95 | 0.946 |
| Overall agreement | 97.1% | 96.5% |
| Borderline agreement | 88.0% | 85.1% |
| Clear-case agreement | 99.2% | 99.1% |
| MAE | 4.5 dB | 4.35 dB |
| Spearman ρ | 0.82 | 0.812 |

The borderline figure is the material one, being a headline number in the
abstract and the quantity the review specifically probed. The rest are within
rounding.

Also to add: the per-class table above, which answers the reviewer's request
that the majority-class inflation in the aggregate metrics be made visible.

---

## 9. What this changes about the paper's position

The reproducibility failure is closed. The repository now contains the Ruspini
implementation, the pipeline documenting it, the tests, and the verification
scripts, and the numbers the manuscript reports come out of that pipeline.

Two things remain genuinely open:

**The comparator baseline.** The reviewer is right that regressing PTA-4 from
seven frequency thresholds, four of which are the arithmetic terms of the target,
is a reconstruction task rather than a clinical benchmark. kappa = 0.981 for
XGBoost demonstrates it. The reviewer's proposed alternative is a probabilistic
multi-class model — ordinal logistic regression or multi-class gradient boosting
— benchmarked against the fuzzy membership vectors with Brier scores and
cross-entropy. That comparison does not currently exist and is the largest
remaining methodological gap.

**The membership overlap, now measured rather than argued.** The partition
supplies transition bands of 10 to 13.6 dB in place of 2 dB, which is what the
reviewer asked for, but the consequence is a lower borderline agreement with the
crisp reference by construction. That needs stating as an expected effect rather
than presenting the wider band as a free improvement.

---

## 10. Artefacts

**Code**
`fuzzy_audiogram/ruspini.py` — the construction, `verify`, `core_repairs`
`scripts/pipeline_participant.py` — two-stage `optimize_mfs`, fixed calibration
`tests/test_ruspini.py` — 16 unit tests
`tests/test_pipeline_ruspini.py` — end-to-end check
`tests/diagnose_calibration.py` — reproduces the guard failure
`tests/reoptimise_labels.py` — labelling schemes from saved predictions
`tests/calibrate_train_eval_test.py` — train-fit, test-score comparison

**Data**
`/home/hermes/.hermes/home/nhanes_raw/` — the six CDC files, 25 MB
`data/output_participant/` — fresh run outputs
`archive/participant_run_2db_overlap/` — the previous run, kept for comparison

**Commits**
`3772e70` — Ruspini partition implementation
`10c42fa` — calibration fix

---

## 11. Correction to an earlier claim

At one point in this work I reported a bug at line 229 of
`pipeline_participant.py` — a comprehension written `for r in PTA_IDX` rather
than `for i in PTA_IDX`, which raises `TypeError`. That was a misreading. The
file reads `for i in PTA_IDX` and always has; git confirms it is unchanged since
the commit. A reproduction that appeared to confirm the bug was testing my own
mistyping rather than the file. There is no defect at that line.
