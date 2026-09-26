# Rule base of the deployed fuzzy inference system

Mamdani inference, 42 rules, single-ear mode. Extracted from the built control system (`fuzzy_audiogram.rules`), not transcribed, and reconciled against the 42 rules the assembled FIS actually contains.

The source defines the configuration rules with one `if severity is not None / else` pair, so counting `ctrl.Rule` call sites gives 43. In single-ear mode the `severity`-free branch is the one taken, giving 14 configuration rules and 42 in total. That is the figure the manuscript states.

Antecedents are joined by AND. Each variable is a linguistic term of the fuzzified input named.


## A. Severity rules  (12)

| # | Antecedent | Consequent |
|---|---|---|
| 1 | threshold is normal | severity = normal |
| 2 | threshold is mild | severity = mild |
| 3 | threshold is moderate | severity = moderate |
| 4 | threshold is moderately_severe | severity = moderately_severe |
| 5 | threshold is severe | severity = severe |
| 6 | threshold is profound | severity = profound |
| 7 | threshold is normal and threshold is mild | severity = mild |
| 8 | threshold is mild and threshold is moderate | severity = moderate |
| 9 | threshold is moderate and threshold is moderately_severe | severity = moderately_severe |
| 10 | threshold is moderately_severe and threshold is severe | severity = severe |
| 11 | threshold is severe and threshold is profound | severity = severe |
| 12 | threshold is normal and threshold is mild and threshold is moderate | severity = moderate |

## B. Configuration rules  (14)

| # | Antecedent | Consequent |
|---|---|---|
| 13 | slope is flat and notch is no_notch | audiogram_shape = flat |
| 14 | slope is gently_sloping and notch is no_notch | audiogram_shape = sloping |
| 15 | slope is steeply_sloping and notch is no_notch | audiogram_shape = sloping |
| 16 | slope is precipitous and notch is no_notch | audiogram_shape = precipitous |
| 17 | slope is rising and notch is no_notch | audiogram_shape = rising |
| 18 | slope is flat and notch is no_notch | audiogram_shape = normal |
| 19 | notch is shallow_notch and slope is flat | audiogram_shape = notched |
| 20 | notch is deep_notch and slope is flat | audiogram_shape = notched |
| 21 | notch is shallow_notch and slope is gently_sloping | audiogram_shape = notched |
| 22 | notch is deep_notch and slope is steeply_sloping | audiogram_shape = notched |
| 23 | slope is rising and notch is deep_notch | audiogram_shape = rising |
| 24 | slope is precipitous and notch is shallow_notch | audiogram_shape = precipitous |
| 25 | slope is gently_sloping and notch is deep_notch | audiogram_shape = notched |
| 26 | slope is steeply_sloping and notch is deep_notch | audiogram_shape = precipitous |

## C. Complex configuration interaction rules  (4)

| # | Antecedent | Consequent |
|---|---|---|
| 27 | slope is precipitous and threshold is moderate | severity = severe |
| 28 | slope is precipitous and threshold is mild | severity = moderately_severe |
| 29 | threshold is normal and slope is steeply_sloping | severity = mild |
| 30 | threshold is normal and slope is precipitous | severity = moderate |

## D. Referral rules  (12)

| # | Antecedent | Consequent |
|---|---|---|
| 31 | asymmetry is symmetric | referral = none |
| 32 | asymmetry is mildly_asymmetric | referral = routine |
| 33 | asymmetry is moderately_asymmetric | referral = expedited |
| 34 | asymmetry is severely_asymmetric | referral = urgent |
| 35 | asymmetry is mildly_asymmetric and referral is none | referral = routine |
| 36 | asymmetry is moderately_asymmetric and referral is routine | referral = expedited |
| 37 | asymmetry is severely_asymmetric and referral is expedited | referral = urgent |
| 38 | asymmetry is mildly_asymmetric and referral is routine | referral = routine |
| 39 | asymmetry is moderately_asymmetric and referral is expedited | referral = expedited |
| 40 | asymmetry is severely_asymmetric and referral is urgent | referral = urgent |
| 41 | asymmetry is severely_asymmetric | referral = urgent |
| 42 | asymmetry is moderately_asymmetric | referral = expedited |

**Total: 42 rules** — 12 severity, 14 configuration, 4 complex interaction, 12 referral.


Verified against the assembled FIS, which contains 42 rules.
