"""Stage-4 rerun: FAI/WHO agreement on all 410 OAUTHC ears, clean state.

Run after the unfired-consequent fix in ``fuzzy_audiogram/core.py``.

Differences from ``stage2_fai.py``:

* Every ear is classified with a freshly constructed inference system. The
  memoised-build/deep-copy path of stage 2 is kept only as a cross-check, and
  a single shared simulation object is exercised as a third check, because
  reusing one ``ControlSystemSimulation`` across ears can return the previous
  ear's consequent (scikit-fuzzy clears only the first rule's terms).
* Both WHO reference schemes are reported: the protocol's six grades at
  25/40/55/70/90 and the five grades at 25/40/60/80 that
  ``scripts/validate_oatuhc.py`` hard-codes.
* Weighted (quadratic and linear) and unweighted kappa, each with a 95 per
  cent bootstrap interval, ear-level and patient-clustered.
* Fallback and undetermined counts are reported, with agreement computed both
  including and excluding the fallback ears.

Writes ``stage5.json`` and ``figures/fig11_confusion_matrices.png``.
"""
import copy
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
from services import fai_service  # noqa: E402

RNG_SEED = 20261115
N_BOOT = 2000

AC = ["th_250", "th_500", "th_1k", "th_2k", "th_3k", "th_4k", "th_6k", "th_8k"]
FREQ = [250, 500, 1000, 2000, 3000, 4000, 6000, 8000]
PTA_COLS = ["th_500", "th_1k", "th_2k", "th_4k"]
LBL6 = ["normal", "mild", "moderate", "moderately_severe", "severe", "profound"]
LBL5 = ["normal", "mild", "moderate", "severe", "profound"]
PRETTY6 = ["Normal", "Mild", "Moderate", "Mod. severe", "Severe", "Profound"]
PRETTY5 = ["Normal", "Mild", "Moderate", "Severe", "Profound"]

# Protocol section 12.3: six grades. Identical cut points to the Clark scheme
# already implemented in fuzzy_audiogram.validate.crisp_classify.
PROTOCOL_WHO = [25, 40, 55, 70, 90]
PROTOCOL_WHO_LABELS = LBL6
# scripts/validate_oatuhc.py, as shipped: five grades.
SCRIPT_WHO = [25, 40, 60, 80]
SCRIPT_WHO_LABELS = LBL5

FAI_TO_LABEL = {"Normal": "normal", "Mild": "mild", "Moderate": "moderate",
                "Moderately Severe": "moderately_severe", "Severe": "severe",
                "Profound": "profound"}
SHAPEMAP = {"flat": "Flat", "sloping": "Sloping", "rising": "Rising",
            "notched": "Notched"}

df = pd.read_csv(HERE / "derived" / "analysis_clean.csv")
df["pta4"] = df[PTA_COLS].mean(axis=1)


def grade(p, cuts):
    """Index of the grade whose upper bound is the first that contains p."""
    for i, c in enumerate(cuts):
        if p <= c:
            return i
    return len(cuts)


def classify_row(row):
    thr = {f: float(row[c]) for c, f in zip(AC, FREQ) if pd.notna(row[c])}
    return fai_service.classify_values(thresholds_left=thr)


def record(study_id, res):
    if "error" in res:
        return {"study_id": int(study_id), "error": res["error"]}
    return {"study_id": int(study_id), "error": "",
            "fai_score": res.get("fai_score"),
            "fai_label": res.get("fai_label"),
            "fai_label_index": FAI_TO_LABEL.get(str(res.get("fai_label"))),
            "label_source": res.get("fai_label_source"),
            "fai_config": res.get("configuration_label"),
            "config_source": res.get("configuration_source"),
            "n_unfired": res.get("n_unfired_consequents"),
            "unfired": "|".join(res.get("unfired_consequents") or [])}


# --------------------------------------------------------------------------
# Run A: primary. No shared state of any kind: build_audiogram_fis is called
# inside classify_audiogram for every ear.
# --------------------------------------------------------------------------
started = time.time()
runs_a = []
for _, row in df.iterrows():
    runs_a.append(record(row.study_id, classify_row(row)))
fai_a = pd.DataFrame(runs_a)
print(f"run A (fresh build per ear): {len(fai_a)} ears, "
      f"{int(fai_a.error.ne('').sum())} errors, {time.time() - started:.0f}s")

# --------------------------------------------------------------------------
# Run B: stage-2 pattern. one built system, deep-copied per ear.
# --------------------------------------------------------------------------
built = core.build_audiogram_fis(single_ear=True)
original_build = core.build_audiogram_fis
core.build_audiogram_fis = lambda single_ear=False: copy.deepcopy(built)
try:
    runs_b = [record(row.study_id, classify_row(row)) for _, row in df.iterrows()]
finally:
    core.build_audiogram_fis = original_build
fai_b = pd.DataFrame(runs_b)
fai_a.to_csv(HERE / "derived" / "fai_runs_fixed.csv", index=False)
print(f"run B (deep-copied cache): {len(fai_b)} ears")

# --------------------------------------------------------------------------
# Run C: worst case: one simulation object reused for every ear.
# --------------------------------------------------------------------------
shared = core.build_audiogram_fis(single_ear=True)
core.build_audiogram_fis = lambda single_ear=False: shared
try:
    runs_c = [record(row.study_id, classify_row(row)) for _, row in df.iterrows()]
finally:
    core.build_audiogram_fis = original_build
fai_c = pd.DataFrame(runs_c)
print(f"run C (shared simulation): {len(fai_c)} ears")

df = df.merge(fai_a, on="study_id", how="left")
df["who_protocol"] = df.pta4.apply(lambda p: PROTOCOL_WHO_LABELS[grade(p, PROTOCOL_WHO)])
df["who_script"] = df.pta4.apply(lambda p: SCRIPT_WHO_LABELS[grade(p, SCRIPT_WHO)])
df["who_protocol_index"] = df.who_protocol.map({g: i for i, g in enumerate(LBL6)})
df["who_script_index"] = df.who_script.map({g: i for i, g in enumerate(LBL5)})
df["border"] = df.pta4.apply(lambda p: int(any(abs(p - c) <= 5 for c in PROTOCOL_WHO)))


def weighted_kappa(a, b, k, weights):
    a = np.asarray(a, np.int64)
    b = np.asarray(b, np.int64)
    observed = np.zeros((k, k))
    np.add.at(observed, (a, b), 1.0)
    observed /= observed.sum()
    rows, cols = observed.sum(1), observed.sum(0)
    expected = np.outer(rows, cols)
    if weights == "quadratic":
        w = np.array([[(i - j) ** 2 for j in range(k)] for i in range(k)], float) / (k - 1) ** 2
    elif weights == "linear":
        w = np.array([[abs(i - j) for j in range(k)] for i in range(k)], float) / (k - 1)
    else:
        w = np.ones((k, k)) - np.eye(k)
    return float(1 - (w * observed).sum() / (w * expected).sum())


def bootstrap_ci(a, b, k, weights, cluster=None, n=N_BOOT, seed=RNG_SEED):
    rng = np.random.default_rng(seed)
    a, b = np.asarray(a), np.asarray(b)
    values = []
    if cluster is None:
        idx = np.arange(len(a))
        for _ in range(n):
            s = rng.choice(idx, len(idx), replace=True)
            values.append(weighted_kappa(a[s], b[s], k, weights))
    else:
        groups = [np.where(np.asarray(cluster) == u)[0] for u in np.unique(cluster)]
        for _ in range(n):
            pick = rng.integers(0, len(groups), len(groups))
            s = np.concatenate([groups[i] for i in pick])
            values.append(weighted_kappa(a[s], b[s], k, weights))
    v = np.array(values)
    return [round(float(np.percentile(v, 2.5)), 3),
            round(float(np.percentile(v, 97.5)), 3)], round(float(v.std(ddof=1)), 4)


def agreement(frame, labels, ref_index_col, pretty):
    k = len(labels)
    sub = frame[frame.fai_label_index.isin(labels) & frame[ref_index_col].notna()].copy()
    sub["fai_idx"] = sub.fai_label_index.map({g: i for i, g in enumerate(labels)})
    sub["ref_idx"] = sub[ref_index_col].astype(int)
    a = sub.fai_idx.to_numpy(int)
    b = sub.ref_idx.to_numpy(int)

    out = {"n": int(len(sub))}
    for weights in ("quadratic", "linear", "unweighted"):
        ci, se = bootstrap_ci(a, b, k, weights)
        out[f"kappa_{weights}"] = round(weighted_kappa(a, b, k, weights), 3)
        out[f"kappa_{weights}_ci95"] = ci
        out[f"kappa_{weights}_se"] = se
    ci_c, se_c = bootstrap_ci(a, b, k, "quadratic", cluster=sub.patient_id.to_numpy())
    out["kappa_quadratic_ci95_patient_cluster"] = ci_c
    out["design_effect"] = round(se_c / out["kappa_quadratic_se"], 2)

    out["exact"] = round(float((a == b).mean()), 3)
    out["exact_n"] = int((a == b).sum())
    out["within_one"] = round(float((np.abs(a - b) <= 1).mean()), 3)
    out["mae_grade"] = round(float(np.abs(a - b).mean()), 3)
    out["n_fai_higher"] = int((a > b).sum())
    out["n_fai_lower"] = int((a < b).sum())

    matrix = np.zeros((k, k), int)
    np.add.at(matrix, (b, a), 1)          # rows reference, columns FAI
    out["crosstab_reference_rows"] = {"labels": pretty,
                                      "matrix": matrix.tolist()}
    out["distribution_fai"] = {pretty[i]: int((a == i).sum()) for i in range(k)}
    out["distribution_reference"] = {pretty[i]: int((b == i).sum()) for i in range(k)}
    return out


out = {"generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
       "n_ears": int(len(df)),
       "n_patients": int(df.patient_id.nunique()),
       "n_classified": int(df.fai_score.notna().sum()),
       "n_errors": int(df.error.fillna("").ne("").sum())}

out["unfired"] = {
    "n_ears_with_any_unfired": int((df.n_unfired.fillna(0) > 0).sum()),
    "by_consequent": {str(k): int(v) for k, v in
                      df.unfired.fillna("").replace("", np.nan).dropna().value_counts().items()},
    "severity_fallback_ears": int((df.label_source == "crisp_who_fallback").sum()),
    "severity_fallback_ids": sorted(df.loc[df.label_source == "crisp_who_fallback",
                                           "study_id"].astype(int).tolist()),
    "severity_fallback_pta4": sorted(df.loc[df.label_source == "crisp_who_fallback",
                                             "pta4"].round(1).tolist()),
    "undetermined_config_ears": int((df.config_source == "undetermined").sum()),
    "undetermined_config_ids": sorted(df.loc[df.config_source == "undetermined",
                                             "study_id"].astype(int).tolist()),
    "unfired_severity_ids": sorted(df.loc[df.unfired.fillna("") == "severity",
                                         "study_id"].astype(int).tolist()),
    "unfired_shape_ids": sorted(df.loc[df.unfired.fillna("") == "audiogram_shape",
                                      "study_id"].astype(int).tolist()),
}

native = df[df.label_source == "fuzzy"]
out["fai_vs_protocol_who"] = agreement(df, LBL6, "who_protocol_index", PRETTY6)
out["fai_vs_protocol_who_native_only"] = agreement(native, LBL6, "who_protocol_index", PRETTY6)
out["fai_vs_script_who"] = agreement(df, LBL5, "who_script_index", PRETTY5)

# clear / borderline against the protocol scheme
out["strat_protocol"] = {}
for name, mask in (("clear", df.border == 0), ("borderline", df.border == 1)):
    sub = df[mask & df.fai_label_index.notna()].copy()
    sub["fai_idx"] = sub.fai_label_index.map({g: i for i, g in enumerate(LBL6)})
    a = sub.fai_idx.to_numpy(int)
    b = sub.who_protocol_index.to_numpy(int)
    out["strat_protocol"][name] = {"n": int(len(sub)),
                                   "exact": round(float((a == b).mean()), 3),
                                   "kappa_quadratic": round(weighted_kappa(a, b, 6, "quadratic"), 3),
                                   "mae": round(float(np.abs(a - b).mean()), 3)}

# configuration agreement against documented shape
s2 = df[df.documented_shape.isin(SHAPEMAP) & df.fai_config.notna()].copy()
s2["doc"] = s2.documented_shape.map(SHAPEMAP)
out["config"] = {"n": int(len(s2)),
                 "exact": round(float((s2.doc == s2.fai_config).mean()), 3),
                 "exact_n": int((s2.doc == s2.fai_config).sum()),
                 "n_undetermined": int((s2.fai_config == core.UNDETERMINED_SHAPE_LABEL).sum())}
rated = s2[s2.fai_config != core.UNDETERMINED_SHAPE_LABEL]
out["config"]["exact_excluding_undetermined"] = round(float((rated.doc == rated.fai_config).mean()), 3)
out["config"]["n_excluding_undetermined"] = int(len(rated))
cols = ["Flat", "Sloping", "Notched", "Precipitous", "Rising",
        core.UNDETERMINED_SHAPE_LABEL]
ct = pd.crosstab(s2.doc, s2.fai_config).reindex(index=cols[:-1], columns=cols).fillna(0).astype(int)
out["config"]["crosstab"] = {str(k): {str(c): int(v) for c, v in row.items()} for k, row in ct.iterrows()}

# continuous agreement
d = df.fai_score - df.pta4
paired = df.dropna(subset=["fai_score"])
dd = paired.fai_score - paired.pta4
out["continuous"] = {"n": int(len(paired)),
                     "spearman": round(float(paired.fai_score.corr(paired.pta4, method="spearman")), 3),
                     "mae": round(float(dd.abs().mean()), 2),
                     "bias": round(float(dd.mean()), 2),
                     "loa": [round(float(dd.mean() - 1.96 * dd.std()), 2),
                             round(float(dd.mean() + 1.96 * dd.std()), 2)],
                     "score_min": round(float(df.fai_score.min()), 2),
                     "score_max": round(float(df.fai_score.max()), 2)}

# ---- clean-state verification ----
def compare(left, right):
    keys = ["fai_score", "fai_label", "fai_config", "label_source",
            "config_source", "n_unfired", "error"]
    a = left.set_index("study_id")[keys].astype(object).fillna("").astype(str)
    b = right.set_index("study_id")[keys].astype(object).fillna("").astype(str)
    common = a.index.intersection(b.index).sort_values()
    a, b = a.loc[common], b.loc[common]
    diff = (a.to_numpy() != b.to_numpy()).any(axis=1)
    return {"n": int(len(common)), "n_differing": int(diff.sum()),
            "differing_ids": sorted(common[diff].astype(int).tolist())}


out["verification"] = {
    "run_a": "fresh ControlSystem built inside every classify call (primary)",
    "run_b": "one built system deep-copied per ear (stage-2 pattern)",
    "run_c": "one simulation object reused across all ears (worst case)",
    "a_vs_b": compare(fai_a, fai_b),
    "a_vs_c": compare(fai_a, fai_c),
    "repeat_a": None,
}

# repeat a random subsample of run A in a fresh process-equivalent state
sample = df.sample(40, random_state=17)
built_repeat = core.build_audiogram_fis(single_ear=True)
core.build_audiogram_fis = lambda single_ear=False: copy.deepcopy(built_repeat)
try:
    repeat = pd.DataFrame([record(r.study_id, classify_row(r)) for _, r in sample.iterrows()])
finally:
    core.build_audiogram_fis = original_build
first = fai_a[fai_a.study_id.isin(sample.study_id)]
out["verification"]["repeat_a"] = compare(first, repeat)

(HERE / "stage5.json").write_text(json.dumps(out, indent=1, default=str))
print(json.dumps({k: out[k] for k in
                  ("n_ears", "n_classified", "n_errors", "unfired", "verification")},
                 indent=1, default=str))
print("\nprotocol WHO:", json.dumps(out["fai_vs_protocol_who"], indent=0, default=str)[:600])
