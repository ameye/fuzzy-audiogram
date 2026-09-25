#!/usr/bin/env python3
"""Bland-Altman with an explicit scale transfer.

The FAI is a defuzzified index on a 0-100 consequent universe. PTA-4 is in dB HL
on a 0-120 scale. The pipeline computed `fai - pta` directly and the manuscript
reported the result as a decibel difference, which is dimensionally invalid: the
two quantities are not the same unit and the relation is not the identity.

This computes the transfer on the TRAINING partition and reports the agreement
in decibels after mapping the FAI onto the dB scale, so the reported bias and
limits of agreement carry the units claimed.

  PTA_equivalent = (FAI - beta) / alpha

Alpha and beta are fitted on training data only, so the test-set comparison
remains out of sample.
"""
import sys, json, pickle, warnings
from pathlib import Path

warnings.filterwarnings("ignore")
ROOT = Path("/opt/data/fuzzy-audiogram")
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import numpy as np

OUT = ROOT / "data/output_participant"
TEST = pickle.load(open(OUT / "predictions_participant.pkl", "rb"))
TRAIN = pickle.load(open(OUT / "train_predictions.pkl", "rb"))

fai_te = np.asarray(TEST["fai"], float)
pta_te = np.asarray(TEST["pta"], float)
fai_tr = np.asarray(TRAIN["fai"], float)
pta_tr = np.asarray(TRAIN["pta"], float)

print(f"  train n={len(fai_tr):,}   test n={len(fai_te):,}")

# ---- transfer fitted on TRAINING only ----
alpha, beta = np.polyfit(pta_tr, fai_tr, 1)
r = float(np.corrcoef(pta_tr, fai_tr)[0, 1])
print(f"\n  training transfer:  FAI = {alpha:.4f} * PTA + {beta:.3f}   (r = {r:.4f})")
print(f"  inverse:            PTA_eq = (FAI - {beta:.3f}) / {alpha:.4f}")
print(f"  scale factor 1/alpha = {1/alpha:.4f}  "
      f"(so the index runs {1/alpha*100:.0f} dB-equivalent over its 0-100 range)")

# ---- the previously reported, unscaled comparison ----
d_raw = fai_te - pta_te
print(f"\n  as previously reported (FAI - PTA, mixed units):")
print(f"    bias {d_raw.mean():+.2f}   LoA {d_raw.mean()-1.96*d_raw.std():+.1f} to "
      f"{d_raw.mean()+1.96*d_raw.std():+.1f}   [NOT decibels]")

# ---- the corrected comparison, both directions ----
pta_eq = (fai_te - beta) / alpha           # map the FAI onto dB
d_db = pta_eq - pta_te
bias, sd = float(d_db.mean()), float(d_db.std())
lo, hi = bias - 1.96 * sd, bias + 1.96 * sd
print(f"\n  corrected, FAI mapped onto the dB scale:")
print(f"    bias {bias:+.2f} dB   95% LoA {lo:+.1f} to {hi:+.1f} dB   n={len(d_db):,}")

fai_eq = alpha * pta_te + beta             # map PTA onto the index scale
d_idx = fai_te - fai_eq
print(f"\n  equivalent form, PTA mapped onto the index scale:")
print(f"    bias {d_idx.mean():+.2f} index units   "
      f"95% LoA {d_idx.mean()-1.96*d_idx.std():+.1f} to "
      f"{d_idx.mean()+1.96*d_idx.std():+.1f}")
print(f"    (identical to the dB form rescaled by alpha = {alpha:.4f}: "
      f"{d_idx.mean()/alpha:+.2f} dB)")

# proportional bias check
slope, intercept = np.polyfit((pta_eq + pta_te) / 2, d_db, 1)
print(f"\n  proportional bias: difference = {slope:+.4f} * mean + {intercept:+.2f}")
print(f"    -> {'no material proportional bias' if abs(slope) < 0.05 else 'proportional bias present'}")

json.dump({
    "transfer_fitted_on": "training partition",
    "alpha": float(alpha), "beta": float(beta), "r_training": r,
    "scale_factor": float(1 / alpha),
    "unscaled_bias": float(d_raw.mean()),
    "unscaled_loa": [float(d_raw.mean() - 1.96 * d_raw.std()),
                     float(d_raw.mean() + 1.96 * d_raw.std())],
    "bias_db": bias, "loa_db": [lo, hi], "n": int(len(d_db)),
    "proportional_slope": float(slope), "proportional_intercept": float(intercept),
    "note": ("The FAI is an index on a 0-100 consequent universe, not dB HL. The "
             "dB figures map the index through a linear transfer fitted on training "
             "data. The unscaled difference mixes units and must not be reported "
             "as decibels."),
}, open(OUT / "bland_altman_scaled.json", "w"), indent=2)
print(f"\n  saved: {OUT/'bland_altman_scaled.json'}")
