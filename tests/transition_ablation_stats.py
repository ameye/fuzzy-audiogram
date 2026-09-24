#!/usr/bin/env python3
"""Is the wider transition band's advantage real?

The ablation compares the same Ruspini construction with the same fixed
calibration, differing only in the floor on the core gap: the raw percentile
gaps (5.7-13.6 dB) against a 10 dB floor. This bootstraps the paired difference
in quadratic-weighted kappa and in borderline agreement over ears.
"""
import sys, json, pickle, warnings
from pathlib import Path

warnings.filterwarnings("ignore")
ROOT = Path("/opt/data/fuzzy-audiogram")
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import numpy as np
from sklearn.metrics import cohen_kappa_score, accuracy_score

def load(tag):
    d = pickle.load(open(ROOT / f"archive/transition_{tag}/predictions_participant.pkl", "rb"))
    return (np.asarray(d["y_true"]).astype(int),
            np.asarray(d["yf"]).astype(int),
            np.asarray(d["dist"], dtype=float),
            np.asarray(d["fai"], dtype=float))

y_a, p_a, d_a, f_a = load("2.0")
y_b, p_b, d_b, f_b = load("10.0")
assert np.array_equal(y_a, y_b), "runs must share the same test reference"
n = len(y_a)
print(f"  n = {n:,} ears")

def stats(y, p, dist):
    bl = np.abs(dist) <= 5
    return (cohen_kappa_score(y, p, weights="quadratic"),
            accuracy_score(y, p),
            accuracy_score(y[bl], p[bl]),
            accuracy_score(y[~bl], p[~bl]))

k_a, ov_a, bl_a, cl_a = stats(y_a, p_a, d_a)
k_b, ov_b, bl_b, cl_b = stats(y_b, p_b, d_b)

print(f"\n  {'metric':<22}{'2 dB gaps':>12}{'10 dB floor':>14}{'difference':>13}")
print("  " + "-"*61)
for name, a, b in [("weighted kappa", k_a, k_b), ("overall accuracy", ov_a, ov_b),
                   ("borderline accuracy", bl_a, bl_b), ("clear accuracy", cl_a, cl_b)]:
    print(f"  {name:<22}{a:>12.4f}{b:>14.4f}{b-a:>+13.4f}")

# paired bootstrap
rng = np.random.RandomState(20260924)
B = 4000
dk = np.empty(B); dbl = np.empty(B); dov = np.empty(B)
bl = np.abs(d_a) <= 5
for i in range(B):
    idx = rng.randint(0, n, n)
    y = y_a[idx]
    if len(np.unique(y)) < 2:
        dk[i] = dbl[i] = dov[i] = 0.0
        continue
    dk[i] = (cohen_kappa_score(y, p_b[idx], weights="quadratic")
             - cohen_kappa_score(y, p_a[idx], weights="quadratic"))
    dov[i] = accuracy_score(y, p_b[idx]) - accuracy_score(y, p_a[idx])
    b = bl[idx]
    if b.sum() and (~b).sum():
        dbl[i] = accuracy_score(y[b], p_b[idx][b]) - accuracy_score(y[b], p_a[idx][b])

print(f"\n  paired bootstrap, {B:,} resamples")
for name, arr, point in [("kappa", dk, k_b - k_a), ("overall", dov, ov_b - ov_a),
                         ("borderline", dbl, bl_b - bl_a)]:
    lo, hi = np.percentile(arr, [2.5, 97.5])
    pgt = (arr > 0).mean()
    sig = "excludes 0" if lo > 0 or hi < 0 else "includes 0"
    print(f"    d_{name:<12} {point:+.4f}   95% CI [{lo:+.4f}, {hi:+.4f}]   "
          f"P(>0)={pgt:.3f}   {sig}")

# how much do the labels actually differ?
diff = (p_a != p_b)
print(f"\n  ears labelled differently between the two widths: {diff.sum():,} "
      f"({diff.mean()*100:.1f}%)")
print(f"  of those: 2 dB correct {accuracy_score(y_a[diff], p_a[diff])*100:.1f}%  "
      f"10 dB correct {accuracy_score(y_a[diff], p_b[diff])*100:.1f}%")

out = ROOT / "data/output_participant/transition_ablation.json"
json.dump({"n": int(n),
           "widths": {"2.0": {"kappa": k_a, "overall": ov_a, "borderline": bl_a, "clear": cl_a},
                      "10.0": {"kappa": k_b, "overall": ov_b, "borderline": bl_b, "clear": cl_b}},
           "bootstrap": {"kappa_diff": float(k_b - k_a),
                         "kappa_ci": [float(x) for x in np.percentile(dk, [2.5, 97.5])],
                         "borderline_diff": float(bl_b - bl_a),
                         "borderline_ci": [float(x) for x in np.percentile(dbl, [2.5, 97.5])],
                         "n_resamples": B},
           "relabelled": int(diff.sum())},
          open(out, "w"), indent=2)
print(f"\n  saved: {out}")
