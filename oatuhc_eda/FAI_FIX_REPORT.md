# Unfired Consequents in the FAI: Root Cause, Fix and Frequency

**Component:** `fuzzy_audiogram/core.py` (`classify_audiogram`), `webapp/services/fai_service.py`
**Version:** 0.3.0 to 0.3.1
**Dataset:** OAUTHC validation export, 410 ears / 205 patients
**Date:** 15 November 2026

---

## 1. What was wrong

`classify_audiogram` read two consequents unconditionally:

```python
severity_score = float(sim.output['severity'])
shape_score = float(sim.output['audiogram_shape'])
```

scikit-fuzzy's `ControlSystemSimulation` is constructed with `lenient=True` and its
`defuzz_consequents` catches `NoTermMembershipsError` and `EmptyMembershipError` and
`continue`s, so a consequent with nothing to defuzzify is **omitted from
`sim.output` entirely**. The index aborted with `KeyError` and `fai_service` turned
that into `{"error": "Classification failed: 'severity'"}`.

Measured on the frozen pre-fix code (`HEAD` = `f9893a9`): **20 of 410 ears (4.9 per
cent)** raise, 16 on `audiogram_shape` and 4 on `severity`. Reproduced exactly on the
pinned stack (NumPy 2.4.6, SciPy 1.18.0, scikit-fuzzy 0.5.0, pandas 3.1.1).

| Consequent | Ears | Studies |
|---|---|---|
| `audiogram_shape` | 16 | 13, 70, 107, 115, 165, 182, 198, 204, 214, 217, 230, 238, 265, 280, 305, 381 |
| `severity` | 4 | 55, 56, 83, 84 |

The EDA's table (section 1.9) lists fifteen identifiers against a count of sixteen; study
305 belongs in the list and was omitted from the printed row. The count of 20 is correct.

## 2. The distinction that the fix had to make

Two different situations both leave the key absent:

| Situation | Mechanism | Consequence terms | Rule support |
|---|---|---|---|
| **No rule fired** | no rule targeting the consequent, so `term_mfs` is empty and `NoTermMembershipsError` is raised | all `None` | 0.0 |
| **Rules fired at zero** | rules evaluate, each antecedent aggregate is 0.0, the aggregated output has zero area, so `EmptyMembershipError` is raised | all recorded as `0.0` | 0.0 |
| **Rule fired, empty area** | positive antecedent truth but a consequent membership function with no area, so `EmptyMembershipError` is raised | some recorded, possibly `0.0` | > 0.0 |

In this rule base every rule is evaluated on every compute, so every consequent that has
any incoming rule records a `0.0` for its terms even when nothing can fire. All 20 ears
here are the "rules fired at zero" case; none is a structurally unreachable consequent.
The fix does not rely on that coincidence. `core._consequent_status` returns one of three
statuses, `defuzzified`, `unfired` or `empty_membership`, derived from the **maximum rule
firing strength** for that consequent (`rule.aggregate_firing`), which is the quantity
that actually separates "nothing tried to fire" from "something fired and produced an
empty set". `sim.output.get()` is never trusted to be either present or meaningful.

## 3. What the system returns now

| Consequent | Unfired return | Flag |
|---|---|---|
| `severity` | crisp WHO/Clark grade for that ear's PTA-4 | `fai_label_source = 'crisp_who_fallback'`, `fai_score = None` |
| `audiogram_shape` | `configuration_label = 'Undetermined'` | `configuration_source = 'undetermined'`, `configuration_score = None` |

Both choices are recorded in the module docstring and are the only two places the fix
invents a label. The returned object also carries the missing-rule condition as data:

```python
'unfired_consequents': ['audiogram_shape'],   # every consequent without a crisp value
'n_unfired_consequents': 1,
'outputs': {'severity':       {'status': 'defuzzified', 'value': 51.29, 'rule_support': 1.0},
            'audiogram_shape': {'status': 'unfired',     'value': None,  'rule_support': 0.0},
            'referral':       {'status': 'defuzzified', 'value': 6.63,  'rule_support': 1.0}}
```

`fai_service.classify_values` passes all of it through (`unfired_consequents`,
`n_unfired_consequents`, `output_status`) instead of collapsing `bytes`/`None` to `0`,
which is what made a missing score look like a score of zero.

### Why a fallback for severity and `Undetermined` for configuration

**Severity: crisp fallback.** All four severity failures have PTA-4 of exactly 120.0 dB HL.
The `profound` trapezoid is `[91.9, 94.4, 103.5, 120.0]`, so its membership is 0 at exactly
120 and every other severity membership is 0 there too: the input sits on the closed right
edge of the universe of discourse, one dB above which the model has no opinion at all. A
screening index that declines to grade a 120 dB loss is not deployable, and the crisp grade
in that corner is not in doubt. The alternative routes were worse:

- *Undetermined for severity too* would leave the primary endpoint (severity agreement)
  undefined for exactly the ears with the most hearing loss, which is the selection
  problem the fix exists to remove.
- *Widening the rule base* (extending the `profound` support to 120) changes membership
  functions and therefore changes outputs for ears that already worked. That is a change
  to the published index, not a bug fix, and is out of scope here.

The cost is that, **against a crisp reference, a fallback ear agrees by construction**. It
is therefore flagged, counted, and left out of the primary agreement estimate; the
sensitivity analysis that includes it is reported alongside.

**Configuration: `Undetermined`.** The protocol defines no crisp standard for audiogram
configuration, and the only candidate, `documented_shape`, is itself under a provenance
query (EDA section 1.3). Substituting it would fabricate a label and would make the
configuration endpoint circular. `Undetermined` is a real class: it says the rule base has
no opinion, which is true, and it is counted as a disagreement against documented shape
rather than being silently dropped.

## 4. Frequency: this is a rule-base coverage finding, not only a software bug

| Consequent | Ears | Share | Pattern |
|---|---|---|---|
| `severity` | 4 | 1.0 per cent | PTA-4 = 120.0 dB HL, beyond the support of every severity membership function |
| `audiogram_shape` | 16 | 3.9 per cent | three slope/notch combinations that no configuration rule covers |

The sixteen shape failures are not a rounding artefact. They fall into exactly three
uncovered antecedent pairs, all of them anatomically ordinary:

| Slope term | Notch term | Ears | Studies |
|---|---|---|---|
| `rising` | `shallow_notch` | 8 | 107, 115, 165, 182, 230, 238, 265, 381 |
| `steeply_sloping` | `shallow_notch` | 7 | 13, 70, 198, 204, 214, 280, 305 |
| `precipitous` | `deep_notch` | 1 | 217 |

`get_configuration_rules` covers `flat`/`gently_sloping`/`steeply_sloping`/`precipitous`/
`rising` against `no_notch`, and shallow-notched cases only against `flat` and
`gently_sloping`. A rising or steeply sloping contour with a shallow notch, which is what a
mildly notched high-frequency drop produces, has no rule. That is a coverage gap in the
published rule base, reported as such: 3.9 per cent of this sample cannot be assigned a
configuration by the index as published. It is not repaired here, because adding rules
would change the instrument. The author's options are to add those three combinations in a
documented version of the rule base, or to accept `Undetermined` as a reportable outcome.

Severity coverage is effectively complete: 1.0 per cent, all of it at a single input value
on the edge of the universe.

## 5. Effect on ears that already worked

**None.** All 390 ears that classified before the fix return an identical `fai_score`,
`fai_label` and `configuration_label` after it: 0 score changes, 0 label changes, 0
configuration changes, verified ear by ear against the pre-fix code at `f9893a9`.

This is structural rather than lucky. The fix only adds a branch that is reachable when
`sim.output` has no finite value; on the path where a value exists, the arithmetic is the
line-for-line original. Membership functions, rule weights, rule text and
`SEVERITY_LABEL_THRESHOLDS` are untouched.

One deliberate behaviour change for a *working* ear would have been possible and was
avoided: `sim.reset()` is now called before the inputs are set. It clears the per-call
state that the cached path used to carry. On a simulation built inside
`classify_audiogram` it is a no-op, which the zero-change result confirms.

## 6. A second defect found next to the first

scikit-fuzzy clears consequent state for the **first rule only**:

```python
first = True
for rule in self.ctrl.rules:
    if first:
        for c in rule.consequent:
            c.term.membership_value[self] = None
        first = False
```

Reusing one `ControlSystemSimulation` across ears therefore leaves the *other*
consequents holding the previous ear's memberships, and a subsequent ear can be given a
stale score instead of a missing one. That is the mechanism behind the EDA's
false "PTA 120 graded normal". The fix adds `sim.reset()` at the top of every
classification, so even a caller that hands in a shared object gets a clean inference, and
`stage5_rerun.py` verifies a fully shared object against per-ear construction.

## 7. Tests

`tests/test_unfired_consequents.py`, 15 cases, part of the existing suite:

- an ear where every consequent fires (`[10]*8`);
- an ear where the severity consequent has no support (`[120]*8`): status, `None` score,
  flagged fallback, unaffected configuration;
- an ear where one consequent fires and another does not (study 13's contour), checking
  the score and label of the firing one are unchanged;
- a synthetic FIS proving `empty_membership` (positive support, zero area) is not
  reported as `unfired`;
- a shared-simulation regression that would have returned the previous ear's grade;
- nine extreme synthetic contours (120 dB, 0 dB, -5 dB, alternating, non-monotone) that
  must not raise;
- all 410 ears of the validation export, skipped when the patient-level file is absent,
  which asserts no error and that each fallback class stays under 5 per cent.

CI (`.github/workflows/tests.yml`) is unchanged and collects the new file through its
existing `pytest tests/` step. With the pre-existing collection failure ignored
(`tests/calibrate_train_eval_test.py` reads a git-ignored pickle from a hard-coded
`/opt/data/fuzzy-audiogram` path, and `tests/verify_asymmetry_refactor.py` does the same
for its baseline), the suite is 31 passed. Both of those already fail at `f9893a9` for that
path reason; neither is touched here and neither exercises this fix.
