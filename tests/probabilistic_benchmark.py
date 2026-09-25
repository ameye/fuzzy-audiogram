#!/usr/bin/env python3
"""Probabilistic multi-class benchmark against the fuzzy membership vector.

The review asked for the fuzzy output to be benchmarked against a probabilistic
multi-class model, scored with Brier scores and cross-entropy rather than
agreement alone. Agreement is a weak test here: the FAI-to-label step is
calibrated to reproduce the crisp WHO grade, so it absorbs most of what the
graded representation changes.

What is compared
----------------
The fuzzy system's graded output is the six Ruspini memberships evaluated at the
primary threshold, which in this implementation is PTA-4 itself. Those six
values are non-negative and sum to one, so they are a probability distribution
over severity and can be scored as one.

Two feature sets are used, because the fuzzy system sees PTA-4 alone while a
machine-learning model can be given more:

  PTA-only   the primary threshold on its own. This is the information the fuzzy
             system actually uses, so it isolates the inference layer.
  seven-freq the thresholds at 500, 1000, 2000, 3000, 4000, 6000 and 8000 Hz.
             This shows what is available when the full audiogram is used.

The seven-frequency set contains the four thresholds that define PTA-4, so a
model given all seven can partly reconstruct the reference label from the
target's own components. That is inherent to predicting a grade defined from
those thresholds, and it is why the PTA-only comparison carries the argument.

Metrics: quadratic-weighted kappa, accuracy, multi-class Brier score, log loss,
and expected calibration error on the top class.

Usage:  python3 tests/probabilistic_benchmark.py
"""
import sys
import json
import pickle
import hashlib
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
ROOT = Path("/opt/data/fuzzy-audiogram")
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.metrics import cohen_kappa_score, accuracy_score, log_loss
from sklearn.preprocessing import StandardScaler
from statsmodels.miscmodels.ordinal_model import OrderedModel

from fuzzy_audiogram.combined_data import (
    load_combined_nhanes, extract_combined_audiometry, clean_ears)
from fuzzy_audiogram import core
from fuzzy_audiogram.ruspini import build_from_percentiles, trapmf, SEVERITY_ORDER
from pipeline_participant import who_grade as _pipeline_who_grade

SEED = 42
N_CLASS = 6
FREQS = [500, 1000, 2000, 3000, 4000, 6000, 8000]   # threshold indices 1..7


# ---------------------------------------------------------------- metrics
def qwk(y, p):
    return cohen_kappa_score(y, p, weights="quadratic")


def brier(y, P):
    Y = np.zeros_like(P)
    Y[np.arange(len(y)), y] = 1.0
    return float(np.mean(np.sum((P - Y) ** 2, axis=1)))


def xent(y, P):
    P = np.clip(P, 1e-12, 1.0)
    P = P / P.sum(axis=1, keepdims=True)
    return float(-np.mean(np.log(P[np.arange(len(y)), y])))


def ece(y, P, bins=10):
    conf = P.max(axis=1)
    pred = P.argmax(axis=1)
    hit = (pred == y).astype(float)
    edges = np.linspace(0.0, 1.0, bins + 1)
    n, total = len(y), 0.0
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = (conf > lo) & (conf <= hi)
        if m.sum() == 0:
            continue
        total += m.sum() / n * abs(hit[m].mean() - conf[m].mean())
    return float(total)


def report(name, y, P, extra=""):
    pred = P.argmax(axis=1)
    row = dict(model=name, kappa=round(qwk(y, pred), 4),
               accuracy=round(accuracy_score(y, pred), 4),
               brier=round(brier(y, P), 5), log_loss=round(xent(y, P), 4),
               ece=round(ece(y, P), 4))
    print(f"  {name:34} k={row['kappa']:.4f}  acc={row['accuracy']*100:5.1f}%  "
          f"brier={row['brier']:.4f}  xent={row['log_loss']:.4f}  "
          f"ece={row['ece']:.4f}{extra}")
    return row


# ---------------------------------------------------------------- data
print("  loading cohort and reproducing the participant-level split...")
raw = load_combined_nhanes()
ear_rows = clean_ears(extract_combined_audiometry(raw))
participants = sorted(set(s for s, _, _, _ in ear_rows))


def _in_test(p, seed=SEED, holdout=0.20):
    """SEQN-keyed holdout. Must match scripts/pipeline_participant.py exactly:
    a positional permutation reshuffles the whole test set whenever the cohort
    changes, so the two would silently disagree after any cohort correction."""
    h = hashlib.md5(f'{int(p)}:{seed}'.encode()).hexdigest()
    return (int(h[:8], 16) % 10_000) < int(holdout * 10_000)


test_ppl = set(p for p in participants if _in_test(p))
test_rows = [r for r in ear_rows if r[0] in test_ppl]
train_rows = [r for r in ear_rows if r[0] not in test_ppl]

d = pickle.load(open(ROOT / "data/output_participant/predictions_participant.pkl", "rb"))
y_saved = np.asarray(d["y_true"]).astype(int)

X7_te = np.array([r[3][1:8] for r in test_rows], dtype=float)
pta_te = np.nanmean(X7_te[:, [0, 1, 2, 4]], axis=1)          # 500,1k,2k,4k


def who_grade(v):
    """WHO 1997 classification. Imported from the pipeline so the boundaries
    cannot drift; the pipeline uses inclusive upper bounds (v <= 25 is normal)."""
    return _pipeline_who_grade(v)


y_te = np.array([who_grade(p) for p in pta_te])

assert len(y_te) == len(y_saved), f"{len(y_te)} vs {len(y_saved)}"
match = (y_te == y_saved).mean()
print(f"  test ears {len(y_te):,}   alignment with saved run: {match*100:.2f}%")
if match < 0.999:
    raise SystemExit("  ABORT: test rows do not align with the saved predictions")

X7_tr = np.array([r[3][1:8] for r in train_rows], dtype=float)
pta_tr = np.nanmean(X7_tr[:, [0, 1, 2, 4]], axis=1)
y_tr = np.array([who_grade(p) for p in pta_tr])

m = np.isnan(X7_te).any(axis=1)
if m.any():                                    # rare; impute from the train median
    X7_te[m] = np.nanmedian(X7_tr, axis=0)
m = np.isnan(X7_tr).any(axis=1)
if m.any():
    X7_tr[m] = np.nanmedian(X7_tr, axis=0)

print(f"  train {len(y_tr):,} / test {len(y_te):,}")
print(f"  class counts (test): {np.bincount(y_te, minlength=6).tolist()}")

rows = []

# ---------------------------------------------------------------- FAI
print("\n  --- fuzzy system (Ruspini memberships at PTA-4) ---")
params = json.load(open(ROOT / "data/output_participant/metrics_participant.json"))["mf_params"]
P_fai = np.zeros((len(pta_te), N_CLASS))
for i, x in enumerate(np.clip(pta_te, 0, 120)):
    for j, name in enumerate(SEVERITY_ORDER):
        P_fai[i, j] = trapmf(x, params[name])
rowsum = P_fai.sum(axis=1, keepdims=True)
bad = (np.abs(rowsum - 1.0) > 1e-6).sum()
print(f"    membership rows summing to 1: {len(P_fai)-bad:,}/{len(P_fai):,} "
      f"(max deviation {np.abs(rowsum-1).max():.2e})")
rows.append(report("FAI membership vector (PTA-4)", y_te, P_fai))

# uniform reference
P_u = np.full((len(y_te), N_CLASS), 1.0 / N_CLASS)
rows.append(report("uniform reference", y_te, P_u))

# ---------------------------------------------------------------- PTA-only
print("\n  --- PTA-only models (same information as the fuzzy system) ---")
sc = StandardScaler().fit(pta_tr.reshape(-1, 1))
A_tr, A_te = sc.transform(pta_tr.reshape(-1, 1)), sc.transform(pta_te.reshape(-1, 1))

om = OrderedModel(y_tr, A_tr, distr="logit").fit(method="bfgs", disp=False)
pr = om.predict(A_te, which="prob")
rows.append(report("ordinal logistic (PTA-4)", y_te, np.asarray(pr)))

lr = LogisticRegression(max_iter=3000, random_state=SEED).fit(A_tr, y_tr)
rows.append(report("multinomial logistic (PTA-4)", y_te, lr.predict_proba(A_te)))

# ---------------------------------------------------------------- seven freq
print("\n  --- seven-frequency models (full audiogram) ---")
sc7 = StandardScaler().fit(X7_tr)
B_tr, B_te = sc7.transform(X7_tr), sc7.transform(X7_te)

om7 = OrderedModel(y_tr, B_tr, distr="logit").fit(method="bfgs", disp=False)
rows.append(report("ordinal logistic (7 freq)", y_te, np.asarray(om7.predict(B_te, which="prob"))))

mlr = LogisticRegression(max_iter=5000, random_state=SEED).fit(B_tr, y_tr)
rows.append(report("multinomial logistic (7 freq)", y_te, mlr.predict_proba(B_te)))

gb = HistGradientBoostingClassifier(max_iter=300, learning_rate=0.08,
                                    random_state=SEED).fit(B_tr, y_tr)
rows.append(report("gradient boosting (7 freq)", y_te, gb.predict_proba(B_te)))

rf = RandomForestClassifier(n_estimators=500, min_samples_leaf=5,
                            random_state=SEED, n_jobs=-1).fit(B_tr, y_tr)
rows.append(report("random forest (7 freq)", y_te, rf.predict_proba(B_te)))

# ---------------------------------------------------------------- save
out = ROOT / "data/output_participant/probabilistic_benchmark.json"
json.dump({"n_test": int(len(y_te)), "class_counts": np.bincount(y_te, minlength=6).tolist(),
           "results": rows,
           "note": "metrics on the held-out test set; FAI membership vector is the "
                   "Ruspini partition evaluated at PTA-4"},
          open(out, "w"), indent=2)
print(f"\n  saved: {out}")
