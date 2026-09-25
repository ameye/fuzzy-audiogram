#!/usr/bin/env python3
"""Bootstrap the transition-width sweep.

The published ablation compared two points, which shows that widening helps but
cannot distinguish a broad optimum from a lucky setting. This puts intervals on
the sweep so the plateau can be described honestly.

Also reports the MAE trajectory alongside kappa: the two move in opposite
directions at the wide end, which is the substantive finding. Wider transitions
improve the continuous agreement by smoothing the graded output while eventually
costing categorical agreement at the boundaries.
"""
import sys, json, pickle, warnings
from pathlib import Path

warnings.filterwarnings("ignore")
ROOT = Path("/opt/data/fuzzy-audiogram")
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import numpy as np
from sklearn.metrics import cohen_kappa_score

WIDTHS = [4.0, 6.0, 8.0, 10.0, 12.0, 14.0, 16.0]
REFERENCE = 10.0
N_BOOT = 2000
RNG = np.random.RandomState(20260925)

data = {}
for w in WIDTHS:
    d = ROOT / f"archive/sweep_{w}"
    pred = pickle.load(open(d / "predictions_participant.pkl", "rb"))
    data[w] = {
        "fai": np.asarray(pred["fai"], float),
        "pta": np.asarray(pred["pta"], float),
        "true": np.asarray(pred["y_true"]),
        "pred": np.asarray(pred["yf"]),
    }
n = len(data[WIDTHS[0]]["true"])
print(f"  n = {n:,} test ears per width\n")

def metrics(idx, w):
    d = data[w]
    k = cohen_kappa_score(d["true"][idx], d["pred"][idx], weights="quadratic")
    mae = float(np.abs(d["fai"][idx] - d["pta"][idx]).mean())
    return k, mae

print("  === point estimates and 95% bootstrap intervals ===")
base = np.arange(n)
boot_idx = [RNG.choice(n, n, replace=True) for _ in range(N_BOOT)]
summary = {}
for w in WIDTHS:
    k, mae = metrics(base, w)
    ks = np.array([metrics(i, w)[0] for i in boot_idx])
    maes = np.array([metrics(i, w)[1] for i in boot_idx])
    summary[w] = (k, mae)
    print(f"    {w:5.1f} dB  kappa {k:.4f} [{np.percentile(ks,2.5):.4f}, {np.percentile(ks,97.5):.4f}]"
          f"   MAE {mae:.2f} [{np.percentile(maes,2.5):.2f}, {np.percentile(maes,97.5):.2f}]")

print(f"\n  === difference against the deployed {REFERENCE:.0f} dB floor ===")
kd = {w: np.array([metrics(i, w)[0] for i in boot_idx]) for w in WIDTHS}
for w in WIDTHS:
    if w == REFERENCE:
        continue
    diff = kd[w] - kd[REFERENCE]
    lo, hi = np.percentile(diff, [2.5, 97.5])
    sig = "excludes zero" if (lo > 0 or hi < 0) else "includes zero"
    print(f"    {w:5.1f} vs {REFERENCE:.0f} dB:  {diff.mean():+.4f}  "
          f"[{lo:+.4f}, {hi:+.4f}]   {sig}")

peak = max(WIDTHS, key=lambda w: summary[w][0])
plateau = [w for w in WIDTHS if summary[w][0] >= summary[peak][0] - 0.005]
print(f"\n  === plateau ===")
print(f"    peak {peak:.1f} dB at kappa {summary[peak][0]:.4f}")
print(f"    within 0.005 of peak: {plateau} dB")
print(f"    deployed floor ({REFERENCE:.0f} dB) is {summary[peak][0]-summary[REFERENCE][0]:+.4f} below the peak")

json.dump({str(w): {"kappa": summary[w][0], "mae": summary[w][1]} for w in WIDTHS},
          open(ROOT / "data/output_participant/transition_sweep.json", "w"), indent=2)
print(f"\n  saved: data/output_participant/transition_sweep.json")
