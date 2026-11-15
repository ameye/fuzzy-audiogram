"""Stage-2: frozen-FAI agreement and kappa precision for the OAUTHC dataset.

Reads derived/analysis_clean.csv (produced by clean.py), runs the frozen FAI
once per ear, caches the run to derived/fai_runs.csv, and writes stage2.json.

The FIS itself is NOT modified: build_audiogram_fis is wrapped in a memo so the
inference system is constructed once instead of once per ear. Outputs verified
identical to the uncached path.
"""
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "webapp"))
sys.path.insert(0, str(ROOT))

import fuzzy_audiogram.core as core  # noqa: E402

import copy  # noqa: E402

_orig_build = core.build_audiogram_fis
_cache = {}


def _cached_build(single_ear=False):
    # Memoise the *build* only. Each call gets a fresh deep copy: reusing a
    # single ControlSystemSimulation leaks sim.output between ears and can
    # return a previous ear's score when a compute produces no output.
    if single_ear not in _cache:
        _cache[single_ear] = _orig_build(single_ear=single_ear)
    return copy.deepcopy(_cache[single_ear])


core.build_audiogram_fis = _cached_build

from services import fai_service  # noqa: E402
fai_service._get_fuzzy  # touched to ensure import path

AC = ["th_250", "th_500", "th_1k", "th_2k", "th_3k", "th_4k", "th_6k", "th_8k"]
FREQ = [250, 500, 1000, 2000, 3000, 4000, 6000, 8000]
PTA_COLS = ["th_500", "th_1k", "th_2k", "th_4k"]
LBL6 = ["normal", "mild", "moderate", "moderately_severe", "severe", "profound"]
LBL5 = ["normal", "mild", "moderate", "severe", "profound"]
LBL7 = LBL6 + ["complete"]
CLARK = [25, 40, 55, 70, 90]
WHO5 = [25, 40, 60, 80]
WHO21 = [20, 35, 50, 65, 80, 95]

df = pd.read_csv(HERE / "derived" / "analysis_clean.csv")
df["pta4"] = df[PTA_COLS].mean(axis=1)


def grade(p, cuts):
    for i, c in enumerate(cuts):
        if p <= c:
            return i
    return len(cuts)


df["who_clark"] = df.pta4.apply(lambda p: LBL6[grade(p, CLARK)])
df["who5"] = df.pta4.apply(lambda p: LBL5[grade(p, WHO5)])
df["who21"] = df.pta4.apply(lambda p: LBL7[grade(p, WHO21)])

LABMAP = {"normal": "normal", "mild": "mild", "moderate": "moderate",
          "moderately severe": "moderately_severe", "moderately_severe": "moderately_severe",
          "severe": "severe", "profound": "profound", "complete": "complete"}

RUNS = HERE / "derived" / "fai_runs.csv"
if RUNS.exists():
    fai = pd.read_csv(RUNS)
    print(f"reusing cached FAI runs: {RUNS.name}")
else:
    rows = []
    t0 = time.time()
    for n, (_, r) in enumerate(df.iterrows(), 1):
        thr = {f: float(r[c]) for c, f in zip(AC, FREQ) if pd.notna(r[c])}
        res = fai_service.classify_values(thresholds_left=thr)
        if "error" in res:
            rows.append({"study_id": int(r.study_id), "fai_error": res["error"]})
        else:
            lab = str(res.get("fai_label", "")).strip()
            rec = {"study_id": int(r.study_id), "fai_score": res.get("fai_score"),
                   "fai_label_raw": lab,
                   "fai_label": LABMAP.get(lab.lower().replace("-", " ")),
                   "fai_config": res.get("configuration_label"),
                   "fai_pta": res.get("pta"), "fai_error": ""}
            for k, v in (res.get("threshold_memberships") or {}).items():
                rec[f"mem_{k}"] = v
            rows.append(rec)
        if n % 100 == 0:
            print(f"  {n}/{len(df)}  {time.time()-t0:.0f}s")
    fai = pd.DataFrame(rows)
    fai.to_csv(RUNS, index=False)

df = df.merge(fai, on="study_id", how="left")
df.to_csv(HERE / "derived" / "analysis_with_fai.csv", index=False)

out = {"n_classified": int(df.fai_score.notna().sum()),
       "n_error": int((df.fai_error.fillna("") != "").sum())}
out["fai_failures"] = {
    "ids": sorted(df.loc[df.fai_error.fillna("") != "", "study_id"].astype(int).tolist()),
    "errors": {str(k): int(v) for k, v in df.fai_error.fillna("").value_counts().items() if k},
    "overlap_with_monotonicity": None,
}
out["fai_labels"] = {str(k): int(v) for k, v in df.fai_label.value_counts(dropna=False).items()}
out["fai_configs"] = {str(k): int(v) for k, v in df.fai_config.value_counts(dropna=False).items()}
out["fai_score"] = {"median": round(float(df.fai_score.median()), 2),
                    "q1": round(float(df.fai_score.quantile(.25)), 2),
                    "q3": round(float(df.fai_score.quantile(.75)), 2),
                    "min": round(float(df.fai_score.min()), 2),
                    "max": round(float(df.fai_score.max()), 2)}


def kappa_quad(a, b, k):
    a = np.asarray(a, dtype=np.int64)
    b = np.asarray(b, dtype=np.int64)
    O = np.zeros((k, k))
    np.add.at(O, (a, b), 1.0)
    O /= O.sum()
    r, c = O.sum(1), O.sum(0)
    E = np.outer(r, c)
    W = np.array([[(i - j) ** 2 for j in range(k)] for i in range(k)], dtype=float) / ((k - 1) ** 2)
    return float(1 - (W * O).sum() / (W * E).sum())


def boot_ci(a, b, k, n=1000, cluster=None, seed=7):
    rng = np.random.default_rng(seed)
    a, b = np.asarray(a), np.asarray(b)
    vals = []
    if cluster is None:
        idx = np.arange(len(a))
        for _ in range(n):
            s = rng.choice(idx, len(idx), replace=True)
            vals.append(kappa_quad(a[s], b[s], k))
    else:
        cl = np.asarray(cluster)
        uc = np.unique(cl)
        groups = [np.where(cl == u)[0] for u in uc]
        for _ in range(n):
            pick = rng.integers(0, len(uc), len(uc))
            s = np.concatenate([groups[i] for i in pick])
            vals.append(kappa_quad(a[s], b[s], k))
    v = np.array(vals)
    return float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5)), float(v.std(ddof=1))


def agreement(fai_col, ref_col, labels):
    sub = df[df[fai_col].isin(labels) & df[ref_col].isin(labels)]
    a = sub[fai_col].map({g: i for i, g in enumerate(labels)}).to_numpy(int)
    b = sub[ref_col].map({g: i for i, g in enumerate(labels)}).to_numpy(int)
    k = len(labels)
    lo, hi, se = boot_ci(a, b, k)
    lo_c, hi_c, se_c = boot_ci(a, b, k, cluster=sub.patient_id.to_numpy())
    d = {"n": int(len(sub)), "kappa_quad": round(kappa_quad(a, b, k), 3),
         "kappa_ci_ear": [round(lo, 3), round(hi, 3)], "kappa_se_ear": round(se, 4),
         "kappa_ci_patient": [round(lo_c, 3), round(hi_c, 3)], "kappa_se_patient": round(se_c, 4),
         "design_effect": round(se_c / se, 2),
         "exact": round(float((a == b).mean()), 3),
         "within1": round(float((np.abs(a - b) <= 1).mean()), 3),
         "mae_grade": round(float(np.abs(a - b).mean()), 3),
         "n_fai_higher": int((a > b).sum()),
         "n_fai_lower": int((a < b).sum())}
    ct = np.zeros((k, k), dtype=int)
    np.add.at(ct, (b, a), 1)          # rows reference, cols FAI
    d["crosstab"] = [[int(x) for x in row] for row in ct]
    return d


out["fai_vs"] = {"clark": agreement("fai_label", "who_clark", LBL6),
                 "who5": agreement("fai_label", "who5", LBL5),
                 "who21": agreement("fai_label", "who21", LBL7)}

# borderline stratification against the protocol/Clark reference
df["border"] = df.pta4.apply(lambda p: int(any(abs(p - c) <= 5 for c in CLARK)))
sub = df[df.fai_label.isin(LBL6)]
a = sub.fai_label.map({g: i for i, g in enumerate(LBL6)}).to_numpy(int)
b = sub.who_clark.map({g: i for i, g in enumerate(LBL6)}).to_numpy(int)
out["strat_clark"] = {}
for lab, m in [("clear", (sub.border == 0).to_numpy()), ("borderline", (sub.border == 1).to_numpy())]:
    aa, bb = a[m], b[m]
    out["strat_clark"][lab] = {"n": int(m.sum()), "exact": round(float((aa == bb).mean()), 3),
                               "kappa": round(kappa_quad(aa, bb, 6), 3),
                               "mae": round(float(np.abs(aa - bb).mean()), 3)}

SHAPEMAP = {"flat": "Flat", "sloping": "Sloping", "rising": "Rising", "notched": "Notched"}
s2 = df[df.documented_shape.isin(SHAPEMAP) & df.fai_config.notna()]
out["config_agreement"] = {"n": int(len(s2)),
                           "exact": round(float((s2.documented_shape.map(SHAPEMAP) == s2.fai_config).mean()), 3)}
ct = pd.crosstab(s2.documented_shape.map(SHAPEMAP), s2.fai_config)
ct = ct.reindex(index=list(SHAPEMAP.values()), columns=list(SHAPEMAP.values())).fillna(0).astype(int)
out["config_crosstab"] = {str(k): {str(k2): int(v2) for k2, v2 in v.items()} for k, v in ct.iterrows()}

d = df.fai_score - df.pta4
out["fai_vs_pta"] = {"spearman": round(float(df.fai_score.corr(df.pta4, method="spearman")), 3),
                     "pearson": round(float(df.fai_score.corr(df.pta4)), 3),
                     "mae": round(float(d.abs().mean()), 2), "bias": round(float(d.mean()), 2),
                     "loa": [round(float(d.mean() - 1.96 * d.std()), 2),
                             round(float(d.mean() + 1.96 * d.std()), 2)]}

# ---------------- kappa precision ----------------
# Approach: take the OBSERVED 6x6 agreement matrix (FAI vs Clark), blend it
# toward statistical independence by a factor t, and bisect on t so the
# resulting quadratic-weighted kappa equals the target. This preserves this
# dataset's actual disagreement structure (mostly one step, asymmetric) rather
# than inventing an error model, while spanning the plausible kappa range.
def _kappa_from_O(O):
    O = O / O.sum()
    r, c = O.sum(1), O.sum(0)
    E = np.outer(r, c)
    k = O.shape[0]
    W = np.array([[(i - j) ** 2 for j in range(k)] for i in range(k)], float) / ((k - 1) ** 2)
    return float(1 - (W * O).sum() / (W * E).sum())


sub = df[df.fai_label.isin(LBL6)]
a = sub.fai_label.map({g: i for i, g in enumerate(LBL6)}).to_numpy(int)
b = sub.who_clark.map({g: i for i, g in enumerate(LBL6)}).to_numpy(int)
O_obs = np.zeros((6, 6))
np.add.at(O_obs, (b, a), 1.0)
O_obs /= O_obs.sum()
E_obs = np.outer(O_obs.sum(1), O_obs.sum(0))


def blend_O(t):
    return (1 - t) * O_obs + t * E_obs


def sim(target, n=410, reps=600, seed=11, cluster_ids=None):
    rng = np.random.default_rng(seed)
    lo, hi = 0.0, 1.0
    for _ in range(40):
        t = (lo + hi) / 2
        if _kappa_from_O(blend_O(t)) > target:
            lo = t
        else:
            hi = t
    O = blend_O((lo + hi) / 2)
    k_true = _kappa_from_O(O)
    p = O.ravel()
    ks, ws = [], []
    for _ in range(reps):
        if cluster_ids is None:
            draw = rng.multinomial(n, p).reshape(6, 6).astype(float)
            kappa = _kappa_from_O(draw)
            ks.append(kappa)
            boot = []
            for _ in range(120):
                bd = rng.multinomial(n, draw.ravel() / draw.sum()).reshape(6, 6).astype(float)
                boot.append(_kappa_from_O(bd))
            ws.append(np.percentile(boot, 97.5) - np.percentile(boot, 2.5))
    return k_true, float(np.mean(ws)), float(np.std(ks, ddof=1))


out["kappa_precision"] = {
    "n_ears": 410, "n_cluster_units": 205,
    "note": "agreement matrix blended toward independence to span kappa; "
            "marginals are this sample's Clark grades",
    "observed": round(_kappa_from_O(O_obs), 3),
}
for t in (0.6, 0.7, 0.8, 0.9):
    km, w, se = sim(t)
    out["kappa_precision"][str(t)] = {"achieved": round(km, 3), "width": round(w, 3),
                                      "half_width": round(w / 2, 3), "se_bootstrap": round(se, 4)}
out["kappa_precision"]["n_vs_width"] = {}
for n in (200, 410, 800, 1600):
    _, w, _ = sim(0.8, n=n, reps=250)
    out["kappa_precision"]["n_vs_width"][str(n)] = round(w, 3)
# empirical design effect from the real data (cluster bootstrap vs iid)
lo_e, hi_e, se_e = boot_ci(b, a, 6, n=1500)
lo_c, hi_c, se_c = boot_ci(b, a, 6, n=1500, cluster=sub.patient_id.to_numpy())
out["kappa_precision"]["design_effect_observed"] = round(se_c / se_e, 2)
out["kappa_precision"]["ci_observed"] = {"ear": [round(lo_e, 3), round(hi_e, 3)],
                                         "patient": [round(lo_c, 3), round(hi_c, 3)]}

(HERE / "stage2.json").write_text(json.dumps(out, indent=1, default=str))
print(json.dumps(out, indent=1, default=str))
