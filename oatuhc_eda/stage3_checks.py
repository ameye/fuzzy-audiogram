"""Stage-3 checks: alternative weighting, uncached cross-validation, subgroup counts."""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "webapp"))
sys.path.insert(0, str(ROOT))

LBL6 = ["normal", "mild", "moderate", "moderately_severe", "severe", "profound"]
CLARK = [25, 40, 55, 70, 90]
PTA = ["th_500", "th_1k", "th_2k", "th_4k"]
AC = ["th_250", "th_500", "th_1k", "th_2k", "th_3k", "th_4k", "th_6k", "th_8k"]

df = pd.read_csv(HERE / "derived" / "analysis_with_fai.csv")
df["pta4"] = df[PTA].mean(axis=1)


def kap(a, b, weights, k=6):
    O = np.zeros((k, k)); np.add.at(O, (a, b), 1.0); O /= O.sum()
    r, c = O.sum(1), O.sum(0); E = np.outer(r, c)
    if weights == "quadratic":
        W = np.array([[(i - j) ** 2 for j in range(k)] for i in range(k)], float) / ((k - 1) ** 2)
    elif weights == "linear":
        W = np.array([[abs(i - j) for j in range(k)] for i in range(k)], float) / (k - 1)
    else:
        W = (np.ones((k, k)) - np.eye(k))
    return float(1 - (W * O).sum() / (W * E).sum())


sub = df[df.fai_label.isin(LBL6)]
a = sub.fai_label.map({g: i for i, g in enumerate(LBL6)}).to_numpy(int)
b = sub.who_clark.map({g: i for i, g in enumerate(LBL6)}).to_numpy(int)
out = {"n": int(len(sub)), "exact": round(float((a == b).mean()), 3)}
for w in ("quadratic", "linear", "unweighted"):
    out[w] = round(kap(a, b, w), 3)

# crosstab rows = reference
ct = np.zeros((6, 6), int); np.add.at(ct, (b, a), 1)
out["crosstab"] = ct.tolist()

# ---- subgroup ear counts ----
out["subgroups"] = {}
out["subgroups"]["sex"] = df.sex.value_counts().to_dict()
age = pd.cut(df.age_years, [17, 39, 59, 200], labels=["18-39", "40-59", "60+"])
out["subgroups"]["age"] = age.value_counts().sort_index().to_dict()
out["subgroups"]["diagnosis"] = df.diagnosis_category.value_counts().to_dict()
out["subgroups"]["consultant"] = df.consultant_grade.value_counts().to_dict()
out["subgroups"]["by_patient_sex"] = df.groupby("sex").patient_id.nunique().to_dict()
out["subgroups"]["patients_by_age"] = df.groupby(age, observed=True).patient_id.nunique().to_dict()
out["subgroups"]["patients_by_diagnosis"] = df.groupby("diagnosis_category").patient_id.nunique().to_dict()

# CI width scaling from the measured n_vs_width curve (width = c/sqrt(n) at kappa 0.8)
kp = json.loads((HERE / "stage2.json").read_text())["kappa_precision"]
n410 = kp["n_vs_width"]["410"]
out["derived_widths_at_kappa_08"] = {
    str(n): round(n410 * np.sqrt(410 / n), 3) for n in (390, 252, 158, 137, 92, 76, 32, 24, 20, 15, 10, 4)
}

# ---- verification: deepcopy-cache path vs fully uncached path ----
import copy  # noqa: E402
import fuzzy_audiogram.core as core  # noqa: E402
from services import fai_service  # noqa: E402

rng = np.random.default_rng(3)
sample = df[df.fai_score.notna()].sample(15, random_state=3)
built = core.build_audiogram_fis(single_ear=True)
orig = core.build_audiogram_fis
core.build_audiogram_fis = lambda single_ear=False: copy.deepcopy(built)
cached = {}
for _, r in sample.iterrows():
    thr = {f: float(r[c]) for c, f in zip(AC, [250, 500, 1000, 2000, 3000, 4000, 6000, 8000])
           if pd.notna(r[c])}
    res = fai_service.classify_values(thresholds_left=thr)
    cached[int(r.study_id)] = (res.get("fai_score"), res.get("fai_label"))

core.build_audiogram_fis = orig      # fully uncached, exactly as shipped
mism = []
for _, r in sample.iterrows():
    thr = {f: float(r[c]) for c, f in zip(AC, [250, 500, 1000, 2000, 3000, 4000, 6000, 8000])
           if pd.notna(r[c])}
    res = fai_service.classify_values(thresholds_left=thr)
    got = (res.get("fai_score"), res.get("fai_label"))
    if got != cached[int(r.study_id)]:
        mism.append((int(r.study_id), cached[int(r.study_id)], got))
out["cache_verification"] = {"n_checked": int(len(sample)), "mismatches": mism}

# ---- 120 ears: outcome of the FIS ----
n120 = (df[AC] == 120).any(axis=1)
out["ears_120_outcome"] = {
    "n_ears": int(n120.sum()),
    "failed": int((n120 & df.fai_error.fillna("").ne("")).sum()),
    "failed_ids": sorted(df.loc[n120 & df.fai_error.fillna("").ne(""), "study_id"].astype(int).tolist()),
    "classified": int((n120 & df.fai_score.notna()).sum()),
}
fails = df.fai_error.fillna("").ne("")
out["failure_profile"] = {
    "n": int(fails.sum()),
    "median_pta": float(df.loc[fails, "pta4"].median()),
    "median_pta_ok": float(df.loc[~fails, "pta4"].median()),
    "mean_pta": round(float(df.loc[fails, "pta4"].mean()), 1),
    "n_with_120": int((n120 & fails).sum()),
    "mono_flag": int(df.loc[fails, "flag_monotonicity_40"].sum()),
    "bc_flag": int(df.loc[fails, "flag_bc_gt_ac_10"].sum()),
}
out["fai_score_saturation"] = {"n_above_94": int((df.fai_score > 94).sum()),
                               "max": round(float(df.fai_score.max()), 2),
                               "n_pta_above_95": int((df.pta4 > 95).sum())}

print(json.dumps(out, indent=1, default=str))
(HERE / "stage3.json").write_text(json.dumps(out, indent=1, default=str))
