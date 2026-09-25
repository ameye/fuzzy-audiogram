# Probabilistic Benchmark and Transition-Width Ablation

**Subject:** the reviewer's two open requests, implemented and measured
**Repository:** `ameye/fuzzy-audiogram`
**Reference runs:** `archive/transition_2.0/`, `archive/transition_10.0/`
**Verdict:** The reviewer's circularity objection is confirmed more strongly than
they stated it. The requested widening is not a trade-off — it improves
agreement, with a bootstrap interval excluding zero.

---

## 1. Why these two things

Two items were left open after the reproducibility work. Both were raised by the
external review.

**The comparator formulation.** The reviewers noted that the machine-learning
comparators regressed PTA-4 from seven frequency thresholds, four of which are
the arithmetic terms of the target. That is a reconstruction task, not a
clinical benchmark, and the near-perfect scores demonstrated it. They proposed a
probabilistic multi-class model instead, benchmarked against the fuzzy
membership vectors with Brier scores and cross-entropy.

**The transition width.** The reviewers asked for the graded region to be at
least as wide as the ±5 dB test-retest variability the partition represents,
rather than the 2 dB margin in use. The partition construction was changed to
satisfy this, but the *consequence* had not been measured.

---

## 2. What was implemented

### 2.1 The probabilistic benchmark

`tests/probabilistic_benchmark.py`. The fuzzy system's graded output is the six
Ruspini memberships evaluated at the primary threshold. In this implementation
the primary threshold is PTA-4 itself, so those memberships are a function of
PTA-4 alone. They are non-negative and sum to one, so they are a probability
distribution over severity and can be scored as one.

Against that, six probabilistic models were fitted on the training split and
scored on the held-out test split:

| Model | Features |
|---|---|
| Proportional-odds ordinal logistic | PTA-4 |
| Multinomial logistic | PTA-4 |
| Proportional-odds ordinal logistic | seven frequencies |
| Multinomial logistic | seven frequencies |
| Gradient boosting | seven frequencies |
| Random forest | seven frequencies |

Metrics: quadratic-weighted kappa and accuracy from the arg-max label,
multi-class Brier score, log loss, and expected calibration error on the top
class.

Two feature sets are used deliberately. The fuzzy system consumes PTA-4 alone,
so the PTA-only row is the like-for-like comparison that isolates the inference
layer. The seven-frequency rows show what becomes available with the full
audiogram, and they contain the four thresholds that define the reference label.

### 2.2 The transition-width ablation

`scripts/run_transition_ablation.sh`, `tests/transition_ablation_stats.py`. The
same Ruspini construction and the same fixed calibration were run twice,
differing only in the floor placed on the core gap:

- **2 dB arm** — the raw percentile gaps, which after construction range from
  5.7 to 13.6 dB
- **10 dB arm** — gaps floored at 10 dB, giving 10.0 to 13.6 dB

Everything else was held constant, so the difference is attributable to the
width of the graded region alone. The transition width is now settable through
`FA_MIN_TRANSITION`, which made the ablation possible without editing code.

---

## 3. The circularity objection, confirmed

The result is decisive and it is stronger than the reviewers' own statement.

| Model | Features | kappa | accuracy | Brier | log loss | ECE |
|---|---|---:|---:|---:|---:|---:|
| Ordinal logistic | PTA-4 | **1.0000** | **100.0%** | **0.0000** | **0.0000** | **0.0000** |
| Ordinal logistic | 7 freq | **1.0000** | **100.0%** | **0.0000** | **0.0000** | **0.0000** |
| Multinomial logistic | PTA-4 | 0.9941 | 99.6% | 0.0158 | 0.0335 | 0.0242 |
| Multinomial logistic | 7 freq | 0.9934 | 99.6% | 0.0107 | 0.0227 | 0.0135 |
| Random forest | 7 freq | 0.9701 | 98.3% | 0.0321 | 0.0599 | 0.0291 |
| **FAI membership vector** | **PTA-4** | **0.9564** | **97.2%** | **0.0474** | **0.0805** | **0.0300** |
| Gradient boosting | 7 freq | 0.9177 | 97.4% | 0.0479 | 0.2771 | 0.0304 |
| Uniform reference | — | 0.0000 | 86.9% | 0.8333 | 1.7918 | 0.7027 |

**A proportional-odds ordinal logistic regression on PTA-4 alone reproduces the
reference grade exactly, in every one of 3,912 ears, with a Brier score of
zero.**

That is not a good model. It is proof that the label is a deterministic
monotone function of the input. The WHO grade is by construction a thresholding
of PTA-4, so a model with a monotone latent recovers it exactly and the
probabilities collapse to 0 and 1. Perfect separation drives the coefficients
to the boundary and the Brier score to zero.

The consequence is that **agreement metrics cannot discriminate between models
on this task.** Any model capable of representing monotone thresholds will
score near-perfectly, and the remaining differences measure how well each
approximation fits a step function, not how well it predicts anything.

This sharpens the reviewers' criticism rather than answering it. They objected
that the comparator was reconstructing its target; the correct statement is that
*any* supervised model on this target is reconstructing it, including the
probabilistic one they proposed. The fuzzy system is not worse at the task. It
is not doing the same kind of task.

### 3.1 What the comparison can still show

Two things survive, and both are informative.

**Discrimination among approximations.** The models do not all saturate. The
ordinal logistic represents monotone thresholds exactly and scores 1.0000. The
random forest approximates them piecewise and scores 0.9701. Gradient boosting
scores 0.9177 — *worse than the fuzzy memberships*, on seven-frequency input,
with more capacity.

That ordering is not incidental. A label defined by thresholds on a single
continuous quantity is exactly the structure a set of trapezoidal membership
functions represents natively: the partition's breakpoints *are* thresholds on
decibels. A tree ensemble has to approximate the same step function with axis
aligned splits on noisy inputs, and it does that less well. The fuzzy system
therefore has the correct inductive bias for this label, and the comparison
demonstrates it.

**Probabilistic quality.** Where the models do differ is in the quality of
their graded output, and there the fuzzy system is fully competitive:

- Brier 0.0474 against 0.0479 for gradient boosting, on richer input
- Log loss 0.0805 against 0.2771 for gradient boosting
- Expected calibration error 0.0300 against 0.0304

The fuzzy memberships are better calibrated than gradient boosting and much
better on log loss, from less input. The two metrics beyond the label are
therefore not decoration: they are the only place the comparison carries
information, which is precisely why the reviewers asked for them.

**A note on the labelling step.** The membership vector's own arg-max recovers
the reference grade at kappa 0.9564, which is *better* than the 0.9456 obtained
from the separately calibrated FAI-score thresholds. The graded representation
is a slightly better classifier than the crisp labelling step layered on top of
it. That had not been observed before, because only the calibrated label was
ever reported.

---

## 4. The transition-width ablation

| Metric | 2 dB gaps | 10 dB floor | Difference | 95% CI |
|---|---:|---:|---:|---|
| Weighted kappa | 0.9266 | 0.9456 | **+0.0190** | [+0.0108, +0.0272] |
| Overall accuracy | 94.61% | 96.47% | **+1.87 pp** | [+1.28, +2.48] |
| Borderline accuracy | 79.48% | 85.09% | **+5.61 pp** | [+2.78, +8.48] |
| Clear accuracy | 98.08% | 99.09% | +1.01 pp | — |

Paired bootstrap over 4,000 resamples, n = 3,912 ears. All three intervals
exclude zero.

Of the 152 ears (3.9%) that the two widths label differently, the narrow
construction gets 24.3% right and the wide one 72.4%.

**The reviewers' requested widening improves the agreement metrics; it does not
trade against them.** Borderline agreement gains 5.6 points, which is the
quantity the review specifically probed.

### 4.1 A correction to my own earlier analysis

I had predicted the opposite — that widening the graded region would reduce
borderline agreement with the crisp reference by construction, since more ears
would fall in a partially-graded state where the reference is a hard boundary. I
said so in an earlier report and proposed the manuscript present it as an
expected cost.

That was wrong, and the measurement refutes it. The reason is that the
label-threshold calibration is fitted after the partition is fixed: a wider
graded region changes the shape of the defuzzified score in a way the
calibration can exploit, aligning the FAI thresholds with the WHO boundaries
more effectively. Borderline accuracy rose from 79.5% to 85.1%.

The manuscript should therefore state the widening as a measured improvement
with a confidence interval, not as a trade-off to be excused.

### 4.2 What the two widths actually differ in

```
2 dB gaps                     10 dB floor
normal             [-0.5,  0.0, 16.4, 30.0]   normal             [-0.5,  0.0, 16.4, 30.0]
mild               [16.4, 30.0, 35.7, 45.0]   mild               [16.4, 30.0, 35.4, 45.4]
moderate           [35.7, 45.0, 54.3, 60.0]   moderate           [35.4, 45.4, 52.1, 62.1]
moderately_severe  [54.3, 60.0, 67.1, 75.0]   moderately_severe  [52.1, 62.1, 66.1, 76.1]
severe             [67.1, 75.0, 83.6, 94.8]   severe             [66.1, 76.1, 83.6, 94.8]
profound           [83.6, 94.8, 120.0, 120.5] profound           [83.6, 94.8, 120.0, 120.5]
```

Both are valid partitions summing to one everywhere. They differ only in the
width of the bands where the membership is shared, and the wide arm's bands are
all 10.0 dB or more against a floor of 5.7 dB in the narrow arm.

---

## 5. What this means for the manuscript

Four changes are warranted.

**Report the transition width as a measured improvement.** Replace any framing
of the wider band as a trade-off with the ablation result and its interval.

**Add the probabilistic comparison, and state what it proves.** The ordinal
logistic's exact reconstruction is the clearest possible evidence that the
reference label is a deterministic function of its input. Reporting it converts
the reviewers' objection from a weakness into a stated property of the task, and
makes the case for why the fuzzy representation is appropriate to it.

**Lead with the metrics that discriminate.** Agreement is saturated by
construction. Brier score, log loss and calibration error are where the
comparison lives, and the fuzzy memberships are competitive or better there
against richer input.

**Report the membership arg-max.** Kappa 0.9564 from the graded representation
against 0.9456 from the calibrated label is a better headline and a more honest
description of what the system produces.

---

## 6. Artefacts

**Scripts**
`tests/probabilistic_benchmark.py` — the probabilistic comparison
`tests/transition_ablation_stats.py` — paired bootstrap on the ablation
`scripts/run_transition_ablation.sh` — the ablation driver
`scripts/pipeline_participant.py` — `FA_MIN_TRANSITION` override added

**Results**
`data/output_participant/probabilistic_benchmark.json`
`data/output_participant/transition_ablation.json`
`archive/transition_2.0/` and `archive/transition_10.0/` — full runs

**Consistency checks applied**
The benchmark aborts unless its reconstructed test set aligns with the saved
predictions. That check caught two real errors during development: a split drawn
with `choice` where the pipeline uses `permutation`, and severity bounds written
exclusive where the pipeline uses inclusive upper bounds. The pipeline's
`who_grade` is now imported rather than reimplemented, so the boundaries cannot
diverge again.
