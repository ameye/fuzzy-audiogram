#!/usr/bin/env python3
"""Implement the remaining review items against v4.

The review was written against v3. Most of what it asks for is already in v4 —
Ceriani's framing in the Introduction, the Clark/WHO attribution, Suen's actual
criteria, the WHO/PDH/91.1 archival code, the asymmetry-to-referral refactor, the
"complex-interaction" rename, the Bland-Altman transfer, and the Table 2
relabelling. What follows are the items that were genuinely still outstanding, plus
two the review exposed that it had not named:

  1. Discussion still cited [2,3] jointly for human-audiogram classifiers,
     re-grouping Ceriani with Achakulvisut after the Introduction had separated
     them. The reviewer's "or remove [3]" option is the right one here, since the
     Introduction already frames Ceriani correctly.
  2. Table 1 had no intervals. A sensitivity of 1.000 from 19 ears and one of
     1.000 from 3,401 are not the same claim, and the reader could not tell.
     Wilson score intervals, not Wald: Wald collapses to zero width at p = 0 or 1,
     which is exactly the case in these rows.
  3. The two-point ablation quoted a clear-case difference with no interval while
     the kappa and borderline differences both carried one.
  4. Clark's tiers were defined on the three-frequency average and are applied
     here to the four-frequency window. That was in a bib note, which does not
     render, so the text never said it.
  5. Figure 2's caption still read "nearest WHO severity boundary" — a
     misattribution the body text no longer makes.
  6. "United States" was being lowercased by the CSL, having no case protection.
"""
import sys
from pathlib import Path

ROOT = Path("/opt/data/fuzzy-audiogram/manuscript")
Q = ROOT / "manuscript_v4.qmd"
BIB = ROOT / "references_v2.bib"

s = Q.read_text(encoding="utf-8")
b = BIB.read_text(encoding="utf-8")

EDITS = [
# ---- 1. Ceriani must not be grouped as a human-audiogram classifier
("Machine-learning classifiers [@achakulvisut2025; @ceriani2025] achieve strong accuracy but are not inspectable",
 "Machine-learning classifiers [@achakulvisut2025] achieve strong accuracy but are not inspectable"),

# ---- 2. Table 1 with Wilson intervals
("""| Severity category | n | Sensitivity | Specificity | Precision |
|---|---|---|---|---|
| Normal | 3,401 | 0.980 | 1.000 | 1.000 |
| Mild | 361 | 0.950 | 0.974 | 0.790 |
| Moderate | 103 | 0.621 | 0.993 | 0.703 |
| Moderately severe | 26 | 0.500 | 0.996 | 0.464 |
| Severe | 18 | 1.000 | 0.999 | 0.783 |
| Profound | 3 | 0.667 | 1.000 | 1.000 |""",
 """| Severity category | n | Sensitivity (95% CI) | Specificity (95% CI) | Precision (95% CI) |
|---|---|---|---|---|
| Normal | 3,401 | 0.980 (0.975–0.984) | 1.000 (0.993–1.000) | 1.000 (0.999–1.000) |
| Mild | 361 | 0.950 (0.923–0.968) | 0.974 (0.969–0.979) | 0.790 (0.750–0.826) |
| Moderate | 103 | 0.621 (0.525–0.709) | 0.993 (0.990–0.995) | 0.703 (0.603–0.787) |
| Moderately severe | 26 | 0.500 (0.321–0.679) | 0.996 (0.994–0.998) | 0.464 (0.295–0.642) |
| Severe | 18 | 1.000 (0.824–1.000) | 0.999 (0.997–0.999) | 0.783 (0.581–0.903) |
| Profound | 3 | 0.667 (0.208–0.939) | 1.000 (0.999–1.000) | 1.000 (0.342–1.000) |"""),

# ---- 3. clear-case interval, which the review noticed was missing
("""and borderline agreement from 79.5% to 85.1% (+5.6 pp, 95% CI +2.8 to +8.5), both intervals excluding zero.""",
 """borderline agreement from 79.5% to 85.1% (+5.6 pp, 95% CI +2.8 to +8.5) and clear-case agreement from 98.1% to 99.1% (+1.0 pp, 95% CI +0.7 to +1.4), all three intervals excluding zero."""),

# ---- 4. Clark's tiers were defined on three frequencies
("""The categories follow the Clark scheme at 25, 40, 55, 70 and 90 dB HL [@clark1981], the convention in most clinical reporting.""",
 """The categories follow the Clark scheme at 25, 40, 55, 70 and 90 dB HL [@clark1981], the convention in most clinical reporting; Clark defined those tiers on the three-frequency average, and they are applied here to the four-frequency window that WHO later adopted for grading."""),

# ---- 5. Figure 2 caption: Clark, and the transfer stated as the review asks
("""**Figure 2.** (a) Bland-Altman plot of the difference between FAI and PTA-4 against their mean on the held-out test set (bias +0.25 dB after mapping the index onto the decibel scale, 95% limits of agreement −11.2 to +11.7 dB). (b) Classification agreement as a function of distance from the nearest WHO severity boundary, with the boundary zone shaded.""",
 """**Figure 2.** (a) Bland-Altman plot of the difference between FAI and PTA-4 against their mean on the held-out test set. The FAI is a defuzzified index on a 0 to 100 universe and is not a decibel quantity, so it is mapped onto the decibel scale before differencing, using FAI = 0.890 × PTA-4 + 3.11 fitted on the training partition (r = 0.887); bias +0.25 dB, 95% limits of agreement −11.2 to +11.7 dB. (b) Classification agreement as a function of distance from the nearest Clark severity boundary, with the boundary zone shaded."""),
]

applied, missed = 0, []
for old, new in EDITS:
    if old in s:
        s = s.replace(old, new, 1); applied += 1
    else:
        missed.append(old[:70].replace("\n", " "))

# ---- 6. protect "United States" from the CSL's case handling
b2 = b.replace("Prevalence of asymmetric hearing among adults in the united states",
               "Prevalence of asymmetric hearing among adults in the {United States}")
if b2 != b:
    BIB.write_text(b2, encoding="utf-8"); print("  bib: United States protected")

Q.write_text(s, encoding="utf-8")
print(f"  applied {applied}/{len(EDITS)} manuscript edits")
for m in missed:
    print(f"    MISSED: {m}...")
sys.exit(0 if not missed else 1)
