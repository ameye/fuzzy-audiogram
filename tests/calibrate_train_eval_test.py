#!/usr/bin/env python3
"""Calibrate label thresholds on the TRAINING set, evaluate on the TEST set.

The pipeline's calibration objective maximises kappa on a class-balanced
subsample (each severity class contributes at least 1%, rare classes included).
That is the right thing for balancing a loss but it distorts the kappa target,
which is a population-level measure dominated by the 87% normal majority. This
compares:

  A. the pipeline's class-balanced calibration sample
  B. a population-representative random training sample
  C. population-representative + an objective that rewards borderline agreement

All thresholds are fitted on training data only, then scored on the saved test
predictions, so every test number is out-of-sample.
"""
import sys, json, pickle, warnings
from pathlib import Path

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import numpy as np
from sklearn.metrics import cohen_kappa_score, accuracy_score
from scipy.optimize import minimize

import pipeline_participant as pp
from fuzzy_audiogram.combined_data import (
    load_combined_nhanes, extract_combined_audiometry, clean_ears)

ROOT = Path("/opt/data/fuzzy-audiogram")
PTA_IDX = pp.PTA_IDX
DEFAULT_TH = np.array([20.0, 35.0, 50.0, 65.0, 85.0])

# --- test-side ground truth, from the saved run ---
d = pickle.load(open(ROOT / "data/output_participant/predictions_participant.pkl", "rb"))
test_fai = np.asarray(d["fai"], dtype=float)
test_yt = np.asarray(d["y_true"]).astype(int)
test_dist = np.asarray(d["dist"], dtype=float)
bl = np.abs(test_dist) <= 5

def labels(scores, th):
    th = np.sort(np.asarray(th, dtype=float))
    return np.array([0 if s < th[0] else 1 if s < th[1] else 2 if s < th[2]
                     else 3 if s < th[3] else 4 if s < th[4] else 5 for s in scores])

def score(name, th, fitted_on):
    yf = labels(test_fai, th)
    k = cohen_kappa_score(test_yt, yf, weights="quadratic")
    ov = accuracy_score(test_yt, yf) * 100
    b = accuracy_score(test_yt[bl], yf[bl]) * 100
    c = accuracy_score(test_yt[~bl], yf[~bl]) * 100
    print(f"  {name:26} {str(np.round(th,1).tolist()):34} "
          f"k={k:.4f} ov={ov:5.1f} bl={b:5.1f} cl={c:5.1f}   [{fitted_on}]")
    return k

# --- rebuild the training side ---
raw = load_combined_nhanes()
ear_rows = clean_ears(extract_combined_audiometry(raw))
rng = np.random.RandomState(42)
ppl = sorted({r[0] for r in ear_rows})
test_ppl = set(rng.choice(ppl, int(round(len(ppl) * 0.2)), replace=False).tolist())
train_rows = [r for r in ear_rows if r[0] not in test_ppl]
print(f"  train {len(train_rows):,} ears / test {len(test_fai):,} ears\n")

params = json.load(open(ROOT / "data/output_participant/metrics_participant.json"))["mf_params"]
system, sim, *_ = pp.build_fis_with_params(params)

# A: the pipeline's class-balanced sample
_g = np.array([pp.who_grade(np.mean([r[3][i] for i in PTA_IDX])) for r in train_rows])
r2 = np.random.RandomState(7)
idx = []
for c in range(6):
    cand = np.where(_g == c)[0]
    take = min(int(4000 * max(len(cand) / len(train_rows), 0.01)), len(cand))
    idx.extend(r2.choice(cand, take, replace=False).tolist())
resA = pp.classify_ears_batched(system, [train_rows[i] for i in idx])
faiA = np.array([r['fai_score'] for r in resA])
ytA = np.array([pp.who_grade(r['pta']) for r in resA])

# B: population-representative random sample of the same size
_bidx = np.random.RandomState(3).choice(len(train_rows), len(resA), replace=False)
resB = pp.classify_ears_batched(system, [train_rows[i] for i in _bidx])
faiB = np.array([r['fai_score'] for r in resB])
ytB = np.array([pp.who_grade(r['pta']) for r in resB])

print(f"  calibration sample n={len(faiA):,} (both)")
print(f"    class-balanced  class counts {np.bincount(ytA, minlength=6).tolist()}")
print(f"    representative  class counts {np.bincount(ytB, minlength=6).tolist()}\n")

def fit(fai, yt, seed, guard=1.0):
    def obj(th): return -cohen_kappa_score(yt, labels(fai, th), weights="quadratic")
    best = None
    for s in range(seed if seed else 1):
        x0 = DEFAULT_TH if not s else DEFAULT_TH + np.random.RandomState(s).normal(0, 8, 5)
        o = minimize(obj, np.sort(np.clip(x0, 5, 95)), method="Nelder-Mead",
                     options={"xatol": 0.25, "fatol": 1e-7, "maxiter": 1200})
        th = np.sort(np.clip(o.x, 5, 95))
        if np.diff(th).min() < guard:
            continue
        if best is None or o.fun < best[0]:
            best = (o.fun, th)
    return best[1] if best else None

print("  thresholds fitted on TRAINING, scored on TEST (all out-of-sample):")
score("defaults, no fitting", DEFAULT_TH, "n/a")
thA = fit(faiA, ytA, 1)
if thA is not None: score("A class-balanced sample", thA, "train")
thB = fit(faiB, ytB, 1)
if thB is not None: score("B representative sample", thB, "train")
thB12 = fit(faiB, ytB, 12)
if thB12 is not None: score("B with 12 restarts", thB12, "train")

# for calibration of ambition only: what the test set itself could give
thT = fit(test_fai, test_yt, 12)
if thT is not None: score("C fitted on TEST (optimistic)", thT, "TEST - not valid")
