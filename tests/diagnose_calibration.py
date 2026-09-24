#!/usr/bin/env python3
"""Reproduce the pipeline's label-threshold calibration standalone.

Two questions:
  1. does the `_g = ...` line at 229 actually evaluate?
  2. what does calibration produce for the Ruspini parameters, and why did the
     pipeline call it degenerate?
"""
import sys, warnings, json
from pathlib import Path

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import numpy as np
from sklearn.metrics import cohen_kappa_score
from scipy.optimize import minimize

import pipeline_participant as pp
from fuzzy_audiogram.combined_data import (
    load_combined_nhanes, extract_combined_audiometry, clean_ears)

PTA_IDX = pp.PTA_IDX
print(f"  PTA_IDX = {PTA_IDX}")

# ---- load + split exactly as the pipeline does ----
raw = load_combined_nhanes()
ear_rows = clean_ears(extract_combined_audiometry(raw))
test_ppl = set()
rng = np.random.RandomState(42)
ppl = sorted({r[0] for r in ear_rows})
test_ppl.update(rng.choice(ppl, int(round(len(ppl) * 0.2)), replace=False).tolist())
train_rows = [r for r in ear_rows if r[0] not in test_ppl]
print(f"  train ears {len(train_rows):,}")

# ---- line 229, verbatim ----
print("\n  --- line 229 as written ---")
try:
    _g = np.array([pp.who_grade(np.mean([r[3][i] for r in PTA_IDX])) for r in train_rows])
    print("    evaluated, shape", _g.shape)
except Exception as e:
    print(f"    RAISES {type(e).__name__}: {e}")

print("\n  --- intended form ---")
try:
    _g = np.array([pp.who_grade(np.mean([r[3][i] for i in PTA_IDX])) for r in train_rows])
    print("    evaluated, shape", _g.shape, " class counts", np.bincount(_g))
except Exception as e:
    print(f"    RAISES {type(e).__name__}: {e}")

# ---- calibration on the Ruspini parameters ----
params = json.load(open("/opt/data/fuzzy-audiogram/data/output_participant/metrics_participant.json"))["mf_params"]
system, sim, *_ = pp.build_fis_with_params(params)
print("\n  --- calibration with the Ruspini partition ---")
_g = np.array([pp.who_grade(np.mean([r[3][i] for i in PTA_IDX])) for r in train_rows])
_idx, _rng2 = [], np.random.RandomState(7)
for _c in range(6):
    _cand = np.where(_g == _c)[0]
    _take = min(int(4000 * max(len(_cand) / len(train_rows), 0.01)), len(_cand))
    _idx.extend(_rng2.choice(_cand, _take, replace=False).tolist())
calib_rows = [train_rows[i] for i in _idx]
print(f"    calibration sample n={len(calib_rows):,}")
res = pp.classify_ears_batched(system, calib_rows)
fai = np.array([r['fai_score'] for r in res])
pta = np.array([r['pta'] for r in res])
yt = np.array([pp.who_grade(p) for p in pta])
print(f"    FAI range {fai.min():.1f}-{fai.max():.1f}  mean {fai.mean():.1f}")

DEFAULT_TH = [20.0, 35.0, 50.0, 65.0, 85.0]
def label_from_th(scores, th):
    th = np.sort(np.asarray(th, dtype=float))
    return np.array([0 if s < th[0] else 1 if s < th[1] else 2 if s < th[2]
                     else 3 if s < th[3] else 4 if s < th[4] else 5 for s in scores])

def obj(th):
    return -cohen_kappa_score(yt, label_from_th(fai, th), weights='quadratic')

for name, th in [("defaults", DEFAULT_TH),
                 ("pipeline's final", [20.0, 35.0, 50.0, 65.0, 85.0])]:
    print(f"    {name:18} kappa={-obj(th):.4f}")

opt = minimize(obj, np.array(DEFAULT_TH), method='Nelder-Mead',
               options={'xatol': 0.5, 'fatol': 1e-6, 'maxiter': 600})
th = np.sort(np.clip(opt.x, 5.0, 95.0))
print(f"    optimised          {np.round(th,1).tolist()}  kappa={-opt.fun:.4f}")
print(f"    gaps               {np.round(np.diff(th),2).tolist()}")
print(f"    min gap < 2.0 -> pipeline declares degenerate: {np.diff(th).min() < 2.0}")

# what would the FAI-percentile thresholds give?
for k in (5, 10):
    q = np.percentile(fai[yt > 0], [10, 30, 50, 70, 90]) if k == 5 else np.percentile(fai, [16, 33, 50, 66, 83])
    print(f"    FAI-quantile th    {np.round(q,1).tolist()}  kappa={-obj(q):.4f}")
