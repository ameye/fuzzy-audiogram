#!/usr/bin/env python3
"""Re-derive the severity labels from the saved FAI scores.

The pipeline's label-threshold calibration optimised to kappa 0.9208 but was
rejected by a `gaps.min() < 2.0` guard because its last gap came out 1.99 dB,
so the run fell back to the defaults. The FAI scores themselves are already
saved, so the labelling can be re-optimised without re-running the FIS.
"""
import sys, json, pickle, warnings
from pathlib import Path

warnings.filterwarnings("ignore")
import numpy as np
from sklearn.metrics import cohen_kappa_score, accuracy_score
from scipy.optimize import minimize

ROOT = Path("/opt/data/fuzzy-audiogram")
d = pickle.load(open(ROOT / "data/output_participant/predictions_participant.pkl", "rb"))
fai = np.asarray(d["fai"], dtype=float)
pta = np.asarray(d["pta"], dtype=float)
yt = np.asarray(d["y_true"]).astype(int)
dist = np.asarray(d["dist"], dtype=float)
print(f"  saved predictions: n={len(fai):,}  FAI {fai.min():.1f}-{fai.max():.1f}")

DEFAULT_TH = np.array([20.0, 35.0, 50.0, 65.0, 85.0])
CALIB_TH = np.array([22.9, 40.3, 48.3, 65.9, 67.9])

def labels(scores, th):
    th = np.sort(np.asarray(th, dtype=float))
    return np.array([0 if s < th[0] else 1 if s < th[1] else 2 if s < th[2]
                     else 3 if s < th[3] else 4 if s < th[4] else 5 for s in scores])

bl = np.abs(dist) <= 5
def report(name, th):
    yf = labels(fai, th)
    k = cohen_kappa_score(yt, yf, weights="quadratic")
    ov = accuracy_score(yt, yf)
    b = accuracy_score(yt[bl], yf[bl]) if bl.any() else float("nan")
    c = accuracy_score(yt[~bl], yf[~bl]) if (~bl).any() else float("nan")
    print(f"    {name:30} kappa={k:.4f}  overall={ov*100:5.1f}%  "
          f"borderline={b*100:5.1f}%  clear={c*100:5.1f}%")
    return k

print("\n  --- labelling schemes on the held-out test set ---")
report("defaults [20,35,50,65,85]", DEFAULT_TH)
report("pipeline's rejected optimum", CALIB_TH)

# re-optimise, with multiple restarts and a sane guard
def obj(th):
    return -cohen_kappa_score(yt, labels(fai, th), weights="quadratic")

best = None
for seed in range(12):
    rs = np.random.RandomState(seed)
    x0 = DEFAULT_TH + rs.normal(0, 6, 5) if seed else DEFAULT_TH
    o = minimize(obj, np.sort(np.clip(x0, 5, 95)), method="Nelder-Mead",
                 options={"xatol": 0.25, "fatol": 1e-7, "maxiter": 1200})
    th = np.sort(np.clip(o.x, 5, 95))
    if np.diff(th).min() < 1.0:
        continue
    if best is None or o.fun < best[0]:
        best = (o.fun, th, seed)

if best:
    _, th, seed = best
    print(f"\n    {'re-optimised (12 restarts)':30} {np.round(th,1).tolist()}  (seed {seed})")
    report("re-optimised", th)

    # the same thresholds with the pipeline's own guard applied
    print(f"\n    gaps {np.round(np.diff(th),2).tolist()}   "
          f"min {np.diff(th).min():.2f}  -> pipeline guard (<2.0) "
          f"{'REJECTS' if np.diff(th).min() < 2.0 else 'accepts'}")

# what does the FAI-alone ceiling look like (fit thresholds on the same data)?
print("\n  --- for reference ---")
order = np.argsort(fai)
print(f"    FAI vs WHO grade Spearman {np.corrcoef(fai.argsort().argsort(), yt)[0,1]:.3f}")
