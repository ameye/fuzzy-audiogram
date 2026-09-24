#!/usr/bin/env python3
"""Derive every number the manuscript reports, from the committed pipeline.

Several figures in the manuscript were previously hand-derived: the normal-mild
transition table, the decision-curve net benefits, and the case-study FAI
values. Those cannot be reproduced and had drifted from the fitted model. This
script recomputes all of them from the fitted partition and the held-out test
set so that every reported value has a code path.

Writes data/output_participant/manuscript_numbers.json.
"""
import sys, json, pickle, warnings
from pathlib import Path

warnings.filterwarnings("ignore")
ROOT = Path("/opt/data/fuzzy-audiogram")
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import cohen_kappa_score, accuracy_score, confusion_matrix, f1_score
from fuzzy_audiogram import core
from fuzzy_audiogram.ruspini import trapmf, SEVERITY_ORDER
from pipeline_participant import (build_fis_with_params, classify_ears_batched,
                                  who_grade, PTA_IDX)

OUT = ROOT / "data/output_participant"
D = pickle.load(open(OUT / "predictions_participant.pkl", "rb"))
MET = json.load(open(OUT / "metrics_participant.json"))
PARAMS = MET["mf_params"]
LABEL_TH = MET["label_thresholds"]

# Labels must follow the calibrated thresholds, as the pipeline sets them, or the
# case studies and transition table would be graded on the deployed defaults.
core.SEVERITY_LABEL_THRESHOLDS = list(LABEL_TH)
core.SEVERITY_MF_PARAMS = {k: list(v) for k, v in PARAMS.items()}

y = np.asarray(D["y_true"]).astype(int)
yp = np.asarray(D["yf"]).astype(int)
fai = np.asarray(D["fai"], float)
pta = np.asarray(D["pta"], float)
dist = np.asarray(D["dist"], float)
n = len(y)
NAMES = ["Normal", "Mild", "Moderate", "Moderately Severe", "Severe", "Profound"]

res = {}

# ---------------------------------------------------------------- 1. headline
res["headline"] = {k: MET[k] for k in
                   ("kappa", "overall", "rho", "mae", "borderline", "clear",
                    "borderline_share", "bias", "loa_lo", "loa_hi", "test_ears")}

# ---------------------------------------------------------------- 2. by distance
bands = []
for t in (1, 2, 3, 4, 5, 10, 15):
    m = np.abs(dist) <= t
    bands.append({"within_db": t, "n": int(m.sum()),
                  "agreement": float(accuracy_score(y[m], yp[m])),
                  "share": float(m.mean())})
res["by_distance"] = bands

# ---------------------------------------------------------------- 3. per class
cm = confusion_matrix(y, yp, labels=range(6))
per = []
for i, nm in enumerate(NAMES):
    tp = cm[i, i]; fn = cm[i].sum() - tp
    fp = cm[:, i].sum() - tp; tn = cm.sum() - tp - fn - fp
    per.append({"severity": nm, "n_reference": int(cm[i].sum()),
                "n_predicted": int(cm[:, i].sum()),
                "sensitivity": float(tp / (tp + fn)) if tp + fn else None,
                "specificity": float(tn / (tn + fp)) if tn + fp else None,
                "precision": float(tp / (tp + fp)) if tp + fp else None})
res["per_class"] = per
res["macro_f1"] = float(f1_score(y, yp, average="macro"))
res["macro_sensitivity"] = float(np.mean([p["sensitivity"] for p in per]))
res["confusion_matrix"] = cm.tolist()
edges = [{"reference": NAMES[i], "predicted": NAMES[j], "n": int(cm[i, j])}
         for i in range(6) for j in range(6) if i != j and cm[i, j]]
res["errors"] = edges
res["upward"] = int(sum(e["n"] for e in edges
                        if NAMES.index(e["predicted"]) > NAMES.index(e["reference"])))
res["downward"] = int(sum(e["n"] for e in edges
                          if NAMES.index(e["predicted"]) < NAMES.index(e["reference"])))

# ---------------------------------------------------------------- 4. transition
system, sim, *_ = build_fis_with_params(PARAMS)


def memberships(x):
    x = float(np.clip(x, 0, 120))
    return {k: float(trapmf(x, PARAMS[k])) for k in SEVERITY_ORDER}


def flat_fai(p):
    """FAI for a flat audiogram at p dB HL: slope, notch and asymmetry all zero."""
    from skfuzzy import control as ctrl
    ss = ctrl.ControlSystemSimulation(system)
    ss.input["threshold"] = float(np.clip(p, 0, 120))
    ss.input["slope"] = 0.0
    ss.input["notch"] = 0.0
    ss.input["asymmetry"] = 0.0
    ss.compute()
    return float(ss.output["severity"])


trans = []
for p in (24.0, 25.0, 26.0, 27.0):
    sc = flat_fai(p)
    m = memberships(p)
    trans.append({"pta4": p, "fai": round(sc, 1),
                  "normal": round(m["normal"], 2), "mild": round(m["mild"], 2),
                  "label": core._interpret_severity_score(sc)})
res["normal_mild_transition"] = trans

# where do the shoulders cross at 0.5? the midpoint of the shared band [c_i, b_{i+1}]
cross = (PARAMS["normal"][2] + PARAMS["mild"][1]) / 2.0
res["shoulder_cross_db"] = round(cross, 1)
# transition band width between category i and i+1 is b_{i+1} - c_i
res["transition_widths_db"] = [
    round(PARAMS[SEVERITY_ORDER[i + 1]][1] - PARAMS[SEVERITY_ORDER[i]][2], 1)
    for i in range(5)]

# ---------------------------------------------------------------- 5. decision curve
prev_any = float((y >= 1).mean())
prev_mod = float((y >= 2).mean())
dc = {"prevalence_any": prev_any, "prevalence_moderate": prev_mod, "curves": []}


def net_benefit(pred_pos, outcome, t):
    pos = np.asarray(pred_pos, bool); out = np.asarray(outcome, bool)
    tp = (pos & out).sum(); fp = (pos & ~out).sum()
    return tp / len(out) - fp / len(out) * (t / (1 - t))


# The risk model must be fitted on training data, not on the set being scored.
try:
    TR = pickle.load(open(OUT / "train_predictions.pkl", "rb"))
    tr_fai, tr_pta, tr_y = TR["fai"], TR["pta"], TR["y_true"]
    have_train = True
except FileNotFoundError:
    print("  WARNING: train_predictions.pkl missing, decision curve fitted on test")
    tr_fai, tr_pta, tr_y = fai, pta, y
    have_train = False

for name, outcome_tr, outcome_te, prev in (
        ("any loss (grade>=1)", (tr_y >= 1), (y >= 1), prev_any),
        ("moderate-or-worse (grade>=2)", (tr_y >= 2), (y >= 2), prev_mod)):
    lr_fai = LogisticRegression(max_iter=2000).fit(tr_fai.reshape(-1, 1), outcome_tr)
    lr_pta = LogisticRegression(max_iter=2000).fit(tr_pta.reshape(-1, 1), outcome_tr)
    p_fai = lr_fai.predict_proba(fai.reshape(-1, 1))[:, 1]
    p_pta = lr_pta.predict_proba(pta.reshape(-1, 1))[:, 1]
    rows = []
    for t in (0.05, 0.10, 0.20, 0.30):
        rows.append({"threshold_prob": t, "prevalence": prev,
                     "fai_net_benefit": float(net_benefit(p_fai >= t, outcome_te, t)),
                     "pta_net_benefit": float(net_benefit(p_pta >= t, outcome_te, t)),
                     "treat_all": float(prev - (1 - prev) * (t / (1 - t))),
                     "treat_none": 0.0})
    dc["curves"].append({"outcome": name, "rows": rows})
dc["fitted_on"] = "train" if have_train else "test"
res["decision_curve"] = dc

# ---------------------------------------------------------------- 6. case studies
# The archetypes are synthetic illustrations. Their threshold arrays are stated
# explicitly here and in Supplementary Table S5 so the reported values can be
# reproduced; earlier versions of the manuscript quoted FAI values for
# archetypes whose audiograms were never recorded.
CASES = {
    # label: (left thresholds, right thresholds or None)
    "A_BorderlineMild": ([25, 25, 25, 30, 30, 30, 30, 30], None),
    "B_NoiseNotch":     ([15, 10, 10, 20, 15, 50, 50, 20], None),
    "C_Presbycusis":    ([20, 20, 25, 35, 45, 55, 60, 65], None),
    "D_Asymmetric":     ([50, 55, 55, 55, 55, 55, 55, 55],
                         [25, 25, 30, 30, 30, 30, 30, 30]),
}
cases = {}
for name, (left, right) in CASES.items():
    a = np.array(left, float)
    b = np.array(right, float) if right is not None else None
    f = core.compute_audiogram_features(a, b)
    from skfuzzy import control as ctrl
    ss = ctrl.ControlSystemSimulation(system)
    ss.input["threshold"] = np.clip(f["threshold_primary"], 0, 120)
    ss.input["slope"] = np.clip(f["slope"], -40, 80)
    ss.input["notch"] = np.clip(f["notch_depth"], 0, 50)
    ss.input["asymmetry"] = np.clip(f["asymmetry"], 0, 60)
    ss.compute()
    sc = float(ss.output["severity"])
    try:
        shape = float(ss.output["audiogram_shape"])
        cfg = core._interpret_shape_score(shape)
        shape_v = round(shape, 1)
    except (KeyError, TypeError, ValueError):
        cfg, shape_v = "ERROR", None
    cases[name] = {"left": list(map(float, left)),
                   "right": list(map(float, right)) if right else None,
                   "pta4": round(float(f["pta"]), 1),
                   "pta4_right": round(float(np.mean([b[1], b[2], b[3], b[5]])), 1) if b is not None else None,
                   "fai": round(sc, 1),
                   "label": core._interpret_severity_score(sc),
                   "shape_score": shape_v,
                   "configuration": cfg,
                   "memberships": {k: round(float(trapmf(f["pta"], PARAMS[k])), 2)
                                   for k in SEVERITY_ORDER},
                   "slope": round(float(f["slope"]), 1),
                   "notch": round(float(f["notch_depth"]), 1),
                   "asymmetry": round(float(f["asymmetry"]), 1)}
res["case_studies"] = cases

# ---------------------------------------------------------------- 7. facts
res["label_thresholds"] = LABEL_TH
res["mf_params"] = PARAMS

out = OUT / "manuscript_numbers.json"
json.dump(res, open(out, "w"), indent=2, default=float)

print("  === headline ===")
print(f"    kappa {MET['kappa']:.3f}  overall {MET['overall']*100:.1f}%  "
      f"MAE {MET['mae']:.2f}  rho {MET['rho']:.3f}")
print(f"    borderline {MET['borderline']*100:.1f}%  clear {MET['clear']*100:.1f}%")
print(f"    Bland-Altman bias {MET['bias']}  LoA {MET['loa_lo']} to {MET['loa_hi']}")
print(f"    thresholds {LABEL_TH}")
print("\n  === agreement by distance ===")
for b in res["by_distance"]:
    print(f"    within {b['within_db']:>2} dB  n={b['n']:>5,}  {b['agreement']*100:5.1f}%")
print("\n  === per class ===")
print(f"    {'severity':<20}{'n':>6}{'sens':>8}{'spec':>8}{'prec':>8}")
for p in res["per_class"]:
    print(f"    {p['severity']:<20}{p['n_reference']:>6}"
          f"{(p['sensitivity'] or 0):>8.3f}{(p['specificity'] or 0):>8.3f}"
          f"{(p['precision'] or 0):>8.3f}")
print(f"    macro F1 {res['macro_f1']:.4f}   macro sensitivity {res['macro_sensitivity']:.4f}")
print(f"    errors: {res['upward']} upward, {res['downward']} downward")
print("\n  === normal-mild transition ===")
for t in trans:
    print(f"    PTA-4 {t['pta4']:>4.0f} dB  FAI {t['fai']:>5.1f}  "
          f"Normal {t['normal']:.2f}  Mild {t['mild']:.2f}  -> {t['label']}")
print(f"    shoulders cross at {res['shoulder_cross_db']} dB")
print(f"    transition widths {res['transition_widths_db']} dB")
print("\n  === decision curve ===")
for c in dc["curves"]:
    print(f"    {c['outcome']}")
    for r in c["rows"]:
        print(f"      t={r['threshold_prob']:.2f}  FAI {r['fai_net_benefit']:+.3f}  "
              f"PTA {r['pta_net_benefit']:+.3f}  treat-all {r['treat_all']:+.3f}")
print("\n  === case studies ===")
for k, v in cases.items():
    print(f"    {k:<26} PTA-4 {v['pta4']:>5.1f}  FAI {v['fai']:>5.1f}  {v['label']}")
print(f"\n  saved: {out}")
