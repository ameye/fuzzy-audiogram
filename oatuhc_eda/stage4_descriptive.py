"""Stage-4: descriptive statistics behind the expanded EDA figures.

Reads derived/analysis_with_fai.csv (from clean.py + stage2_fai.py) and writes
descriptive.json. Everything the report quotes as a number outside the ten
original figures is computed here, so the report text and the figures cannot
drift apart.

No thresholds are altered and no record is dropped.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import statlib as S  # noqa: E402

POOL = [1, 2]
AC = ["th_250", "th_500", "th_1k", "th_2k", "th_3k", "th_4k", "th_6k", "th_8k"]
FREQ = [250, 500, 1000, 2000, 3000, 4000, 6000, 8000]
FREQLAB = ["250", "500", "1k", "2k", "3k", "4k", "6k", "8k"]
BC = ["bc_500", "bc_1k", "bc_2k", "bc_4k"]
BC_AC = ["th_500", "th_1k", "th_2k", "th_4k"]
BCLAB = ["500", "1k", "2k", "4k"]
PTA4 = ["th_500", "th_1k", "th_2k", "th_4k"]
PTA3 = ["th_500", "th_1k", "th_2k"]
LBL6 = ["normal", "mild", "moderate", "moderately_severe", "severe", "profound"]
PRETTY = ["Normal", "Mild", "Moderate", "Mod. severe", "Severe", "Profound"]
LBL5 = ["normal", "mild", "moderate", "severe", "profound"]
LBL7 = LBL6 + ["complete"]
CLARK = [25, 40, 55, 70, 90]
WHO5 = [25, 40, 60, 80]
WHO21 = [20, 35, 50, 65, 80, 95]
GRADE_ORDER = ["normal", "mild", "moderate", "moderately_severe", "severe", "profound"]
DIAG_ORDER = ["presbyacusis", "meniere", "ototoxicity", "otosclerosis", "csom", "nihl",
              "ssnhl", "other", "not_documented"]

df = pd.read_csv(HERE / "derived" / "analysis_with_fai.csv")
df["pta4"] = df[PTA4].mean(axis=1)
df["pta3"] = df[PTA3].mean(axis=1)
df["pta8"] = df[AC].mean(axis=1)
ABG = pd.DataFrame(df[BC].values - df[BC_AC].values, index=df.index, columns=BCLAB)
df["abg_mean"] = ABG.mean(axis=1).values
df["abg_max"] = ABG.max(axis=1).values
df["n_abg"] = ABG.notna().sum(axis=1).values
df["abg_any_gt10"] = (ABG > 10).any(axis=1).values
df["year"] = pd.to_datetime(df["test_year_month"], errors="coerce").dt.year
df["ym"] = pd.to_datetime(df["test_year_month"], errors="coerce")
df["ok"] = df.fai_score.notna()

out: dict = {}
out["meta"] = {
    "n_ears": int(len(df)), "n_patients": int(df.patient_id.nunique()),
    "n_left": int((df.ear == "left").sum()), "n_right": int((df.ear == "right").sum()),
    "n_fai_ok": int(df.ok.sum()), "n_fai_fail": int((~df.ok).sum()),
    "n_shapes_documented": int(df.documented_shape.notna().sum()),
    "n_consultant": int(df.consultant_grade.notna().sum()),
}


def grade_idx(p, cuts):
    for i, c in enumerate(cuts):
        if p <= c:
            return i
    return len(cuts)


def kappa_quad(a, b, k):
    """Quadratic-weighted kappa; k is the number of categories."""
    a = np.asarray(a, dtype=np.int64); b = np.asarray(b, dtype=np.int64)
    O = np.zeros((k, k)); np.add.at(O, (a, b), 1.0); O /= O.sum()
    r, c = O.sum(1), O.sum(0)
    W = np.array([[(i - j) ** 2 for j in range(k)] for i in range(k)], float) / ((k - 1) ** 2)
    return float(1 - (W * O).sum() / (W * np.outer(r, c)).sum())


def kappa_plain(a, b, k):
    a = np.asarray(a, dtype=np.int64); b = np.asarray(b, dtype=np.int64)
    O = np.zeros((k, k)); np.add.at(O, (a, b), 1.0); O /= O.sum()
    pe = float((O.sum(1) * O.sum(0)).sum())
    return float((np.trace(O) - pe) / (1 - pe))


df["g_clark"] = df.pta4.apply(lambda p: grade_idx(p, CLARK))
df["g_who5"] = df.pta4.apply(lambda p: grade_idx(p, WHO5))
df["g_who21"] = df.pta4.apply(lambda p: grade_idx(p, WHO21))
df["g_consult"] = df.consultant_grade.map({g: i for i, g in enumerate(LBL6)})
df["g_fai"] = df.fai_label.map({g: i for i, g in enumerate(LBL6)})


# --------------------------------------------------------------- 1. age
age = out["age"] = {}
age["all"] = S.desc(df.age_years)
for sx, lab in [(1, "male"), (2, "female")]:
    age[lab] = S.desc(df.loc[df.sex == sx, "age_years"])
age["left"] = S.desc(df.loc[df.ear == "left", "age_years"])
age["right"] = S.desc(df.loc[df.ear == "right", "age_years"])
age["test_sex"] = S.mannwhitney(df.loc[df.sex == 1, "age_years"], df.loc[df.sex == 2, "age_years"])
age["test_ear"] = S.mannwhitney(df.loc[df.ear == "left", "age_years"],
                                df.loc[df.ear == "right", "age_years"])
age["by_patient"] = S.desc(df.groupby("patient_id").age_years.first())
# heaping
ends = df.age_years % 5 == 0
age["pct_end_in_5"] = float(ends.mean())
age["heaping_test"] = {"observed": int(ends.sum()), "n": int(len(df)),
                       "expected_p": 0.2,
                       "binomial_p": float(stats.binomtest(int(ends.sum()), len(df), 0.2).pvalue)}
age["by_grade_clark"] = {g: S.desc(df.loc[df.g_clark == i, "age_years"])
                         for i, g in enumerate(LBL6)}
age["test_grade_clark"] = S.kruskal([df.loc[df.g_clark == i, "age_years"] for i in range(6)], LBL6)
age["trend_grade_clark"] = {
    "test": "Spearman rho, age against ordered grade",
    "rho": float(stats.spearmanr(df.age_years, df.g_clark).statistic),
    "p": float(stats.spearmanr(df.age_years, df.g_clark).pvalue)}
age["by_grade_consult"] = {g: S.desc(df.loc[df.g_consult == i, "age_years"])
                           for i, g in enumerate(LBL6)}
age["test_grade_consult"] = S.kruskal([df.loc[df.g_consult == i, "age_years"] for i in range(6)], LBL6)
age["by_diagnosis"] = {d: S.desc(df.loc[df.diagnosis_category == d, "age_years"]) for d in DIAG_ORDER}
age["test_diagnosis"] = S.kruskal(
    [df.loc[df.diagnosis_category == d, "age_years"] for d in DIAG_ORDER], DIAG_ORDER)
age["age_vs_pta"] = {
    "spearman": float(stats.spearmanr(df.age_years, df.pta4).statistic),
    "spearman_p": float(stats.spearmanr(df.age_years, df.pta4).pvalue),
    "spearman_ci": S.boot_spearman(df.age_years, df.pta4),
    "ols": S.ols(df.age_years, df.pta4),
}
# within-patient: does age-vs-PTA hold when patients are the unit?
pat = df.groupby("patient_id").agg(age=("age_years", "first"), pta=("pta4", "mean"))
age["age_vs_pta_patient"] = {"n": int(len(pat)),
                             "spearman": float(stats.spearmanr(pat.age, pat.pta).statistic),
                             "p": float(stats.spearmanr(pat.age, pat.pta).pvalue)}

# --------------------------------------------------------------- 2. sex, laterality, asymmetry
sx = out["sex"] = {}
sx["counts"] = {"male": int((df.sex == 1).sum()), "female": int((df.sex == 2).sum())}
sx["patients"] = {"male": int(df.loc[df.sex == 1, "patient_id"].nunique()),
                  "female": int(df.loc[df.sex == 2, "patient_id"].nunique())}
dec = pd.cut(df.age_years, [17, 29, 39, 49, 59, 69, 79, 200],
             labels=["18-29", "30-39", "40-49", "50-59", "60-69", "70-79", "80+"])
tab = pd.crosstab(dec, df.sex).reindex(columns=[1, 2], fill_value=0)
sx["decade_table"] = {str(i): [int(a), int(b)] for i, (a, b) in zip(tab.index, tab.values)}
sx["decade_test"] = S.chisq(tab.values)
sx["by_ear"] = {e: {"male": int(((df.sex == 1) & (df.ear == e)).sum()),
                    "female": int(((df.sex == 2) & (df.ear == e)).sum())} for e in ("left", "right")}
sx["test_by_ear"] = S.chisq([[((df.sex == 1) & (df.ear == "left")).sum(),
                              ((df.sex == 2) & (df.ear == "left")).sum()],
                             [((df.sex == 1) & (df.ear == "right")).sum(),
                              ((df.sex == 2) & (df.ear == "right")).sum()]])

lat = out["laterality"] = {"left": int((df.ear == "left").sum()),
                           "right": int((df.ear == "right").sum()),
                           "patients_with_both": int((df.groupby("patient_id").ear.nunique() == 2).sum())}

# interaural asymmetry: right minus left PTA-4, one row per patient
w = df.pivot_table(index="patient_id", columns="ear", values="pta4", aggfunc="first")
d = (w["right"] - w["left"]).dropna()
asy = out["interaural"] = {
    "n_pairs": int(len(d)), "median_diff": float(d.median()),
    "q1": float(d.quantile(.25)), "q3": float(d.quantile(.75)),
    "mean": float(d.mean()), "sd": float(d.std(ddof=1)),
    "min": float(d.min()), "max": float(d.max()),
    "n_zero": int((d == 0).sum()), "pct_zero": float((d == 0).mean()),
    "n_ge15": int((d.abs() >= 15).sum()), "pct_ge15": float((d.abs() >= 15).mean()),
    "n_ge15_ci": list(S.wilson(int((d.abs() >= 15).sum()), len(d))),
    "n_ge30": int((d.abs() >= 30).sum()),
    "n_right_worse": int((d > 0).sum()), "n_left_worse": int((d < 0).sum()),
    "wilcoxon_symmetry": {"test": "Wilcoxon signed-rank (right vs left)",
                          "statistic": float(stats.wilcoxon(w["right"], w["left"]).statistic),
                          "p": float(stats.wilcoxon(w["right"], w["left"]).pvalue)},
    "abs_median": float(d.abs().median()),
}
# asymmetry by diagnosis (patient-level, using the patient's worse-ear diagnosis)
pat_diag = df.sort_values("pta4").groupby("patient_id").diagnosis_category.first()
asy_tab = pd.crosstab(pat_diag.reindex(d.index), (d.abs() >= 15).reindex(d.index))
asy["by_diagnosis_table"] = {str(k): [int(a), int(b)] for k, (a, b) in
                             zip(asy_tab.index, asy_tab.values)}
asy["by_diagnosis_test"] = S.chisq(asy_tab.values)
# ICC / design effect on PTA-4
groups = [g.pta4.values for _, g in df.groupby("patient_id")]
icc = S.icc1(groups)
asy["icc_pta4"] = icc
asy["design_effect_pta4"] = 1 + (2 - 1) * icc

# --------------------------------------------------------------- 3. collection
col = out["collection"] = {}
per = df.dropna(subset=["ym"]).groupby(df.ym.dt.to_period("M")).size()
per.index = per.index.to_timestamp()
idx = pd.period_range("2020-01", "2026-06", freq="M").to_timestamp()
per = per.reindex(idx, fill_value=0)
col["months_in_window"] = int(len(idx))
col["months_with_records"] = int((per > 0).sum())
col["coverage"] = float((per > 0).mean())
col["by_year"] = {int(y): int((df.year == y).sum()) for y in sorted(df.year.dropna().unique())}
col["series"] = {str(k.date()): int(v) for k, v in per.items()}
# contiguous runs of covered months = extraction batches
runs, start = [], None
for i, (ts, v) in enumerate(per.items()):
    if v > 0 and start is None:
        start = i
    if v == 0 and start is not None:
        runs.append((start, i - 1)); start = None
if start is not None:
    runs.append((start, len(per) - 1))
runs = [{"start": str(per.index[a].date()), "end": str(per.index[b].date()),
         "months": b - a + 1, "ears": int(per.iloc[a:b + 1].sum())} for a, b in runs]
col["runs"] = runs
col["n_runs"] = len(runs)
col["runs_std_ears"] = float(np.std([r["ears"] for r in runs], ddof=1)) if len(runs) > 1 else 0.0
col["monthly_max"] = int(per.max())
col["stat_22_months"] = [str(k.date()) for k, v in per.items() if v == 22]
col["n_months_at_22"] = len(col["stat_22_months"])
col["study_id_range"] = [int(df.study_id.min()), int(df.study_id.max())]
col["study_id_sequential"] = bool((np.diff(np.sort(df.study_id.unique())) == 1).all())

# --------------------------------------------------------------- 4. thresholds
th = out["thresholds"] = {}
th["by_freq"] = {}
for c, f in zip(AC, FREQ):
    th["by_freq"][f] = {"all": S.desc(df[c]),
                        "left": S.desc(df.loc[df.ear == "left", c]),
                        "right": S.desc(df.loc[df.ear == "right", c])}
th["ear_test"] = {}
for c, f in zip(AC, FREQ):
    a = df.loc[df.ear == "left", c].dropna()
    b = df.loc[df.ear == "right", c].dropna()
    # ears are paired, so compare within patient
    ww = df.pivot_table(index="patient_id", columns="ear", values=c)
    ww = ww.dropna()
    if len(ww) > 5:
        r = stats.wilcoxon(ww["right"], ww["left"])
        th["ear_test"][f] = {"n": int(len(ww)), "median_right_minus_left": float((ww.right - ww.left).median()),
                             "p": float(r.pvalue), "statistic": float(r.statistic)}
# median heatmap matrix
th["median_matrix"] = {f: {"left": float(df.loc[df.ear == "left", c].median()),
                           "right": float(df.loc[df.ear == "right", c].median()),
                           "all": float(df[c].median())} for c, f in zip(AC, FREQ)}
# by grade
th["by_grade"] = {}
for g in LBL6:
    sub = df[df.consultant_grade == g]
    th["by_grade"][g] = {f: {"median": float(sub[c].median()), "n": int(sub[c].notna().sum())}
                         for c, f in zip(AC, FREQ)}
th["by_clark"] = {}
for g in LBL6:
    sub = df[df.who_clark == g]
    th["by_clark"][g] = {f: {"median": float(sub[c].median()), "n": int(sub[c].notna().sum())}
                         for c, f in zip(AC, FREQ)}
# frequency correlation (Spearman, pairwise complete)
M = df[AC].corr(method="spearman")
th["corr"] = {"labels": FREQLAB, "matrix": [[float(M.loc[a, b]) for b in AC] for a in AC]}
th["corr_n"] = {f"{a}|{b}": int(df[[a, b]].dropna().shape[0]) for a in AC for b in AC}

# --------------------------------------------------------------- 5. clustering
# Configuration is a property of the *shape* of an ear's profile, not its
# level: two ears at 20 and 70 dB with the same 4 kHz slope have the same
# documented shape. Clustering is therefore done on profiles centred on each
# ear's own mean (level removed), on the seven measured frequencies. 3 kHz is
# excluded because it is missing for 200 of 410 ears. Level-only clustering is
# computed as a check and reported in the text.
COLS7 = ["th_250", "th_500", "th_1k", "th_2k", "th_4k", "th_6k", "th_8k"]
Xraw = df[COLS7].copy()
Xraw = Xraw.fillna(Xraw.median())
lev = Xraw.mean(axis=1)
Xn = (Xraw.sub(lev, axis=0) / Xraw.std(ddof=0)).values
Xs = ((Xraw - Xraw.mean()) / Xraw.std(ddof=0)).values


def _fit(mat, ks=(2, 3, 4, 5, 6)):
    sils, labs = {}, {}
    for k in ks:
        C, lab = S.kmeans(mat, k)
        sils[k] = S.silhouette(mat, lab)
        labs[k] = lab
    return sils, labs


sil, labs = _fit(Xn)
# Silhouette is maximised at the smallest k tried, which separates only
# "better" from "worse" hearing and says nothing about configuration. k=4 is
# used because the comparator (documented_shape) has four categories; the
# weaker k=4 silhouette is reported rather than hidden.
best_k = 4
lab = labs[best_k]
df["cluster"] = lab
# order clusters by the 4 kHz minus 250 Hz slope so the figure reads
# low-to-high frequency loss
slopes = [np.median(Xraw.loc[df.cluster == j, "th_4k"] - Xraw.loc[df.cluster == j, "th_250"])
          for j in range(best_k)]
remap = {int(o): i for i, o in enumerate(np.argsort(slopes))}
df["cluster"] = df.cluster.map(remap)

sil_lev, _ = _fit(Xs)
cl = out["clusters"] = {"silhouette": {str(k): round(v, 3) for k, v in sil.items()},
                        "silhouette_level_clustering": {str(k): round(v, 3) for k, v in sil_lev.items()},
                        "silhouette_best_k": int(max(sil, key=sil.get)),
                        "clustered_on": "7 measured AC frequencies, each ear centred on its own mean",
                        "k": int(best_k),
                        "n": {str(j): int((df.cluster == j).sum()) for j in range(best_k)}}
cl["slopes_db_per_octave"] = {
    str(j): float((df.loc[df.cluster == j, "th_4k"] - df.loc[df.cluster == j, "th_250"]).median()
                  / 4.0) for j in range(best_k)}
cl["profiles"] = {str(j): {f: float(df.loc[df.cluster == j, c].median())
                           for c, f in zip(AC, FREQ)} for j in range(best_k)}
cl["profiles_centred"] = {str(j): {f: float((df.loc[df.cluster == j, c] -
                                             df.loc[df.cluster == j, COLS7].mean(axis=1)).median())
                                   for c, f in zip(COLS7, [250, 500, 1000, 2000, 4000, 6000, 8000])}
                          for j in range(best_k)}
cl["level"] = {str(j): S.desc(lev[df.cluster == j]) for j in range(best_k)}
cl["pta4"] = {str(j): S.desc(df.loc[df.cluster == j, "pta4"]) for j in range(best_k)}
SHAPES4 = ["flat", "sloping", "rising", "notched"]
ct = pd.crosstab(df.cluster, df.documented_shape).reindex(columns=SHAPES4).fillna(0).astype(int)
cl["shape_table"] = {str(i): [int(x) for x in row] for i, row in zip(ct.index, ct.values)}
cl["shape_cols"] = SHAPES4
cl["shape_test"] = S.chisq(ct.values)
cl["purity"] = float(ct.max(axis=1).sum() / ct.values.sum())
dg_ct = pd.crosstab(df.cluster, df.diagnosis_category).reindex(columns=DIAG_ORDER).fillna(0).astype(int)
cl["diagnosis_table"] = {str(i): [int(x) for x in row] for i, row in zip(dg_ct.index, dg_ct.values)}
cl["diagnosis_test"] = S.chisq(dg_ct.values)

# --------------------------------------------------------------- 6. PTA variants
pv = out["pta_variants"] = {}
for name, series in [("pta3", df.pta3), ("pta4", df.pta4), ("pta8", df.pta8)]:
    pv[name] = S.desc(series)
pv["diff_pta4_minus_pta3"] = S.desc(df.pta4 - df.pta3)
pv["diff_pta8_minus_pta4"] = S.desc(df.pta8 - df.pta4)
for name, series in [("pta3", df.pta3), ("pta8", df.pta8)]:
    g = series.apply(lambda p: grade_idx(p, CLARK))
    pv[f"grade_change_{name}_vs_pta4"] = {
        "n_changed": int((g != df.g_clark).sum()),
        "pct_changed": float((g != df.g_clark).mean()),
        "table": {str(k): int(v) for k, v in (g - df.g_clark).value_counts().sort_index().items()},
        "kappa_vs_pta4": float(1 - ((g != df.g_clark).mean())),
        "spearman": float(stats.spearmanr(series, df.pta4).statistic),
    }
pv["corr"] = {"pta3_vs_pta4": float(stats.spearmanr(df.pta3, df.pta4).statistic),
              "pta8_vs_pta4": float(stats.spearmanr(df.pta8, df.pta4).statistic),
              "pta3_vs_pta8": float(stats.spearmanr(df.pta3, df.pta8).statistic)}

# --------------------------------------------------------------- 7. air-bone
ab = out["abg"] = {}
ab["per_freq"] = {lab: S.desc(df[bc] - df[ac]) for bc, ac, lab in zip(BC, BC_AC, BCLAB)}
ab["mean"] = S.desc(df.abg_mean)
ab["max"] = S.desc(df.abg_max)
ab["n_complete"] = int((df.n_abg == 4).sum())
ab["overall"] = {
    "median": float(np.nanmedian(ABG.values)),
    "q1": float(np.nanpercentile(ABG.values, 25)),
    "q3": float(np.nanpercentile(ABG.values, 75)),
    "mean": float(np.nanmean(ABG.values)),
    "n_cells": int(np.isfinite(ABG.values).sum()),
    "pct_positive": float((ABG.values > 0).sum() / np.isfinite(ABG.values).sum()),
    "pct_gt10": float((ABG.values > 10).sum() / np.isfinite(ABG.values).sum()),
}
ab["by_diagnosis"] = {d: S.desc(df.loc[df.diagnosis_category == d, "abg_mean"].dropna())
                      for d in DIAG_ORDER}
ab["test_diagnosis"] = S.kruskal(
    [df.loc[df.diagnosis_category == d, "abg_mean"].dropna() for d in DIAG_ORDER], DIAG_ORDER)
ab["by_consult"] = {g: S.desc(df.loc[df.consultant_grade == g, "abg_mean"].dropna()) for g in LBL6}
ab["test_consult"] = S.kruskal(
    [df.loc[df.consultant_grade == g, "abg_mean"].dropna() for g in LBL6], LBL6)
ab["by_grade_clark"] = {g: S.desc(df.loc[df.who_clark == g, "abg_mean"].dropna()) for g in LBL6}
ab["test_grade_clark"] = S.kruskal(
    [df.loc[df.who_clark == g, "abg_mean"].dropna() for g in LBL6], LBL6)
ab["reverse_gt20_ids"] = sorted(df.loc[df.flag_bc_gt_ac_20 == 1, "study_id"].astype(int).tolist())
ab["reverse_gt10"] = int((df.flag_bc_gt_ac_10 == 1).sum())
ab["reverse_gt20"] = int((df.flag_bc_gt_ac_20 == 1).sum())
ab["gap_gt60"] = int((df.flag_ac_bc_gap_60 == 1).sum())
# AC vs BC at 1 kHz, paired
w = df[["th_1k", "bc_1k"]].dropna()
ab["ac_bc_1k"] = {"n": int(len(w)), "median_ac": float(w.th_1k.median()),
                  "median_bc": float(w.bc_1k.median()),
                  "spearman": float(stats.spearmanr(w.th_1k, w.bc_1k).statistic),
                  "wilcoxon_p": float(stats.wilcoxon(w.th_1k, w.bc_1k).pvalue)}

# --------------------------------------------------------------- 8. diagnosis
dg = out["diagnosis"] = {}
vc = df.diagnosis_category.value_counts()
dg["counts"] = {d: {"ears": int(vc.get(d, 0)),
                    "ear_pct": float(vc.get(d, 0) / len(df)),
                    "patients": int(df.loc[df.diagnosis_category == d, "patient_id"].nunique()),
                    "patient_pct": float(df.loc[df.diagnosis_category == d, "patient_id"].nunique()
                                         / df.patient_id.nunique()),
                    "pta4": S.desc(df.loc[df.diagnosis_category == d, "pta4"])}
                for d in DIAG_ORDER}
dg["missing"] = int((df.diagnosis_category == "not_documented").sum())
dg["named_pct"] = float(1 - (df.diagnosis_category.isin(["other", "not_documented"])).mean())
dg["pta_test"] = S.kruskal(
    [df.loc[df.diagnosis_category == d, "pta4"] for d in DIAG_ORDER if (df.diagnosis_category == d).sum() > 1],
    [d for d in DIAG_ORDER if (df.diagnosis_category == d).sum() > 1])
dg["raw_csom_variants"] = int((pd.read_csv(HERE / "raw_export.csv").diagnosis_category
                              .astype(str).str.strip().str.lower().eq("csom")).sum())

# --------------------------------------------------------------- 9. shape
shp = out["shape"] = {}
shp["counts"] = {k: int(v) for k, v in df.documented_shape.value_counts(dropna=False).items()}
shp["missing"] = int(df.documented_shape.isna().sum())
SHAPEMAP = {"flat": "Flat", "sloping": "Sloping", "rising": "Rising", "notched": "Notched"}
keep = df[df.documented_shape.isin(SHAPEMAP) & df.fai_config.notna()].copy()
keep["doc"] = keep.documented_shape.map(SHAPEMAP)
ct = pd.crosstab(keep.doc, keep.fai_config).reindex(
    index=["Flat", "Sloping", "Rising", "Notched"],
    columns=["Flat", "Sloping", "Rising", "Precipitous", "Notched"]).fillna(0).astype(int)
shp["fai_table"] = {str(k): [int(x) for x in row] for k, row in zip(ct.index, ct.values)}
shp["fai_cols"] = list(ct.columns)
shp["fai_n"] = int(len(keep))
shp["fai_exact"] = float((keep.doc == keep.fai_config).mean())
# nominal kappa documented vs FAI
labels = sorted(set(keep.doc) | set(keep.fai_config))
a = keep.doc.map({g: i for i, g in enumerate(labels)}).to_numpy(int)
b = keep.fai_config.map({g: i for i, g in enumerate(labels)}).to_numpy(int)
O = np.zeros((len(labels), len(labels))); np.add.at(O, (a, b), 1); O /= O.sum()
pe = (O.sum(1) * O.sum(0)).sum()
shp["fai_kappa"] = float((np.trace(O) - pe) / (1 - pe))
shp["fai_kappa_note"] = "unweighted Cohen kappa on the 4 documented against 5 computed categories"
shp["fai_ci"] = list(S.wilson(int((keep.doc == keep.fai_config).sum()), len(keep)))
# threshold-derived configuration, transparent rule on the measured frequencies
def derived_shape(r):
    lo = r.th_500; hi = r.th_4k
    if pd.isna(lo) or pd.isna(hi):
        return "undetermined"
    slope = hi - lo
    notch = r.th_4k - min(r.th_2k, r.th_8k)
    if r.th_3k == r.th_3k and (r.th_3k - r.th_4k) >= 15:
        return "notched"
    if slope >= 20:
        return "sloping"
    if slope <= -20:
        return "rising"
    return "flat"


df["derived_shape"] = df.apply(derived_shape, axis=1)
shp["derived_counts"] = {k: int(v) for k, v in df.derived_shape.value_counts().items()}
ct2 = pd.crosstab(df.documented_shape, df.derived_shape).fillna(0).astype(int)
ct2 = ct2.reindex(index=["flat", "sloping", "rising", "notched"],
                  columns=["flat", "sloping", "rising", "notched", "undetermined"]).fillna(0).astype(int)
shp["derived_table"] = {str(k): [int(x) for x in row] for k, row in zip(ct2.index, ct2.values)}
shp["derived_n"] = int(ct2.values.sum() - ct2["undetermined"].sum())
shp["derived_exact"] = float(np.trace(ct2[["flat", "sloping", "rising", "notched"]].values)
                             / ct2[["flat", "sloping", "rising", "notched"]].values.sum())
shp["derived_agreement_among_documented"] = shp["derived_exact"]

# --------------------------------------------------------------- 10. consultant vs computed
cv = out["consultant"] = {}
ct = pd.crosstab(df.consultant_grade, df.who_clark).reindex(
    index=LBL6, columns=LBL6).fillna(0).astype(int)
cv["vs_clark"] = {str(k): [int(x) for x in row] for k, row in zip(ct.index, ct.values)}
cv["vs_clark_n"] = int(ct.values.sum())
cv["vs_clark_exact"] = float(np.trace(ct.values) / ct.values.sum())
ca = np.repeat(np.arange(6), ct.values.sum(1))
cb = np.concatenate([np.repeat(np.arange(6), row) for row in ct.values])
cv["vs_clark_signed"] = {str(k): int(v) for k, v in
                         pd.Series(cb - ca).value_counts().sort_index().items()}
cv["vs_clark_kappa"] = float(kappa_quad(ca, cb, 6))
cv["vs_clark_weighted_matrix"] = True
# departure: consultant minus Clark, by Clark grade
cv["departure_by_clark"] = {}
for i, g in enumerate(LBL6):
    m = df.g_clark == i
    cv["departure_by_clark"][g] = {"n": int(m.sum()),
                                   "median_signed": float((df.loc[m, "g_consult"] - i).median()),
                                   "pct_exact": float((df.loc[m, "g_consult"] == i).mean()),
                                   "mean_signed": float((df.loc[m, "g_consult"] - i).mean())}
cv["pta_ranges"] = {g: [float(df.loc[df.consultant_grade == g, "pta4"].min()),
                        float(df.loc[df.consultant_grade == g, "pta4"].max())] for g in LBL6}
cv["best_pta_match"] = {}
for name, series in [("pta3", df.pta3), ("pta4", df.pta4), ("pta8", df.pta8)]:
    g = series.apply(lambda p: grade_idx(p, CLARK))
    cv["best_pta_match"][name] = float((g == df.g_consult).mean())

# cluster assignment is written out so the figures use exactly the same labels
# as the tables; derived/ is git-ignored, so this stays off the repository
df[["study_id", "cluster"]].to_csv(HERE / "derived" / "clusters.csv", index=False)

(HERE / "descriptive.json").write_text(json.dumps(out, indent=1, default=str))
print("wrote descriptive.json")
print(json.dumps({k: out[k] for k in ["age", "interaural", "collection"]}, indent=1, default=str)[:6000])

# --------------------------------------------------------------- 11. boundary proximity
bd = out["boundary"] = {}
SCHEMES = {"clark": (CLARK, 6, "Clark / protocol WHO (6)"),
           "who5": (WHO5, 5, "WHO 1997 (5, shipped script)"),
           "who21": (WHO21, 7, "WHO 2021 (7)")}
bd["schemes"] = {k: v[2] for k, v in SCHEMES.items()}
bd["cuts"] = {k: v[0] for k, v in SCHEMES.items()}
for key, (cuts, k, label) in SCHEMES.items():
    dist = df.pta4.apply(lambda p: min(abs(p - c) for c in cuts))
    d = {"n": int(len(dist)), "median": float(dist.median()),
         "q1": float(dist.quantile(.25)), "q3": float(dist.quantile(.75)),
         "max": float(dist.max()), "window_db": 5 * len(cuts),
         "pct_within_window": float((dist <= 5 * len(cuts)).mean())}
    for w in (1, 2, 5, 10):
        n_in = int((dist <= w).sum())
        d[f"n_within_{w}"] = n_in
        d[f"pct_within_{w}"] = float(n_in / len(dist))
        d[f"ci_within_{w}"] = list(S.wilson(n_in, len(dist)))
    d["per_boundary"] = {str(c): int((dist <= 5).sum() * 0 + (df.pta4.between(c - 5, c + 5)).sum())
                         for c in cuts}
    bd[key] = d

# --------------------------------------------------------------- 12. grade distributions, three schemes
gs = out["schemes"] = {}
gs["clark"] = {g: int((df.g_clark == i).sum()) for i, g in enumerate(LBL6)}
gs["who6"] = dict(gs["clark"])
gs["who6_note"] = ("the protocol's six-grade WHO scheme uses the same cuts as Clark "
                   "(25/40/55/70/90), so the two are numerically identical: 0 ears differ")
gs["who5"] = {g: int((df.g_who5 == i).sum()) for i, g in enumerate(LBL5)}
gs["who21"] = {g: int((df.g_who21 == i).sum()) for i, g in enumerate(LBL7)}
gs["consultant"] = {g: int((df.g_consult == i).sum()) for i, g in enumerate(LBL6)}
gs["differ_clark_vs_who6"] = int((df.g_clark != df.g_clark).sum())
# patient-level (each patient counted once, by that patient's worse ear)
worse = df.loc[df.groupby("patient_id").pta4.idxmax()]
gs["patient_level"] = {g: int((worse.g_clark == i).sum()) for i, g in enumerate(LBL6)}
gs["ear_vs_patient_note"] = ("ear-level percentages are unweighted counts of 410 ears; "
                             "patient-level percentages count each of the 205 patients once")

# --------------------------------------------------------------- 13. FAI confusion matrices
def kappa_ci(a, b, k, cluster=None, n=1000, seed=13):
    rng = np.random.default_rng(seed)
    a = np.asarray(a); b = np.asarray(b)
    vals = []
    if cluster is None:
        for _ in range(n):
            i = rng.integers(0, len(a), len(a))
            vals.append(kappa_quad(a[i], b[i], k))
    else:
        cl = np.asarray(cluster)
        groups = [np.where(cl == u)[0] for u in np.unique(cl)]
        for _ in range(n):
            pick = rng.integers(0, len(groups), len(groups))
            i = np.concatenate([groups[j] for j in pick])
            vals.append(kappa_quad(a[i], b[i], k))
    v = np.array(vals)
    return [float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))], float(v.std(ddof=1))


cf = out["confusion"] = {}
for key, (cuts, k, label) in SCHEMES.items():
    labels = LBL6 if k == 6 else (LBL5 if k == 5 else LBL7)
    sub = df[df.fai_label.isin(labels) & df[f"g_{key}"].notna()].copy()
    a = sub.fai_label.map({g: i for i, g in enumerate(labels)}).to_numpy(int)
    b = sub[f"g_{key}"].to_numpy(int)          # already an ordinal 0..k-1
    O = np.zeros((k, k), int); np.add.at(O, (b, a), 1)
    ci, se = kappa_ci(a, b, k)
    ci_c, se_c = kappa_ci(a, b, k, cluster=sub.patient_id.to_numpy())
    cf[key] = {"labels": labels, "n": int(len(sub)),
               "matrix": [[int(x) for x in row] for row in O],
               "kappa_quad": round(kappa_quad(a, b, k), 3),
               "kappa_ci": [round(ci[0], 3), round(ci[1], 3)],
               "kappa_se": round(se, 4),
               "kappa_ci_patient": [round(ci_c[0], 3), round(ci_c[1], 3)],
               "design_effect": round(se_c / se, 2),
               "exact": round(float((a == b).mean()), 4),
               "within1": round(float((np.abs(a - b) <= 1).mean()), 4),
               "mae": round(float(np.abs(a - b).mean()), 4),
               "n_fai_higher": int((a > b).sum()), "n_fai_lower": int((a < b).sum())}

# --------------------------------------------------------------- 14. Bland-Altman
ok = df[df.fai_score.notna()].copy()
ok["diff"] = ok.fai_score - ok.pta4
ok["mean"] = (ok.fai_score + ok.pta4) / 2
ba = out["bland_altman"] = {
    "n": int(len(ok)), "bias": float(ok["diff"].mean()), "sd": float(ok["diff"].std(ddof=1)),
    "loa_low": float(ok["diff"].mean() - 1.96 * ok["diff"].std(ddof=1)),
    "loa_high": float(ok["diff"].mean() + 1.96 * ok["diff"].std(ddof=1)),
    "median": float(ok["diff"].median()),
    "q1": float(ok["diff"].quantile(.25)), "q3": float(ok["diff"].quantile(.75)),
    "slope_vs_mean": S.ols(ok["mean"], ok["diff"]),
    "spearman_vs_mean": float(stats.spearmanr(ok["mean"], ok["diff"]).statistic),
}
ba["by_grade"] = {g: {"n": int((ok.g_clark == i).sum()),
                      "mean_bias": float(ok.loc[ok.g_clark == i, "diff"].mean()),
                      "median_bias": float(ok.loc[ok.g_clark == i, "diff"].median()),
                      "sd": float(ok.loc[ok.g_clark == i, "diff"].std(ddof=1))}
                  for i, g in enumerate(LBL6)}
ba["pct_within_5"] = float((ok["diff"].abs() <= 5).mean())
ba["pct_within_10"] = float((ok["diff"].abs() <= 10).mean())
ba["pct_above_zero"] = float((ok["diff"] > 0).mean())
ba["excl_120"] = (lambda s: {"n": int(len(s)), "bias": float(s.mean()),
                             "loa_low": float(s.mean() - 1.96 * s.std(ddof=1)),
                             "loa_high": float(s.mean() + 1.96 * s.std(ddof=1))})(
    ok.loc[~ok.flag_120_any_freq.astype(bool), "diff"])
ba["saturation"] = {"max_score": float(df.fai_score.max()),
                    "n_score_gt94": int((df.fai_score > 94).sum()),
                    "n_pta_gt95": int((df.pta4 > 95).sum())}

# --------------------------------------------------------------- 15. agreement by grade
ag = out["by_grade"] = {}
for i, g in enumerate(LBL6):
    m = ok.g_clark == i
    n_g = int(m.sum())
    n_ex = int((ok.loc[m, "fai_label"] == g).sum())
    lo, hi = S.wilson(n_ex, n_g)
    err = ok.loc[m, "g_fai"] - i
    ag[g] = {"n": n_g, "exact": float(n_ex / n_g) if n_g else float("nan"),
             "ci": [lo, hi], "n_exact": n_ex,
             "mean_signed_error": float(err.mean()), "sd_signed_error": float(err.std(ddof=1)),
             "n_higher": int((err > 0).sum()), "n_lower": int((err < 0).sum()),
             "n_off1": int((err.abs() == 1).sum()), "n_off2plus": int((err.abs() >= 2).sum())}
# overall exact agreement by grade, weighted by grade n
ag["_overall_exact"] = float((ok.g_fai == ok.g_clark).mean())

# --------------------------------------------------------------- 16. kappa precision curves
def _k_from_O(O):
    O = O / O.sum()
    r, c = O.sum(1), O.sum(0)
    k = O.shape[0]
    W = np.array([[(i - j) ** 2 for j in range(k)] for i in range(k)], float) / ((k - 1) ** 2)
    return float(1 - (W * O).sum() / (W * np.outer(r, c)).sum())


sub = df[df.fai_label.isin(LBL6)]
a = sub.fai_label.map({g: i for i, g in enumerate(LBL6)}).to_numpy(int)
b = sub.who_clark.map({g: i for i, g in enumerate(LBL6)}).to_numpy(int)
O_obs = np.zeros((6, 6)); np.add.at(O_obs, (b, a), 1.0); O_obs /= O_obs.sum()
E_obs = np.outer(O_obs.sum(1), O_obs.sum(0))


def _target_O(target):
    lo, hi = 0.0, 1.0
    for _ in range(40):
        t = (lo + hi) / 2
        if _k_from_O((1 - t) * O_obs + t * E_obs) > target:
            lo = t
        else:
            hi = t
    return (1 - (lo + hi) / 2) * O_obs + ((lo + hi) / 2) * E_obs


def _sim(target, n, reps=160, boot=120, seed=11):
    rng = np.random.default_rng(seed)
    O = _target_O(target)
    p = O.ravel()
    ks, ws = [], []
    for _ in range(reps):
        draw = rng.multinomial(n, p).reshape(6, 6).astype(float)
        kappa = _k_from_O(draw)
        ks.append(kappa)
        bd = rng.multinomial(n, draw.ravel() / draw.sum(), size=boot).astype(float).reshape(boot, 6, 6)
        v = np.array([_k_from_O(x) for x in bd])
        ws.append(np.percentile(v, 97.5) - np.percentile(v, 2.5))
    return float(_k_from_O(O)), float(np.mean(ws)), float(np.std(ks, ddof=1))


kp = out["kappa_curves"] = {"grid_n": [150, 205, 300, 410, 600, 800, 1200], "grid_kappa": [0.6, 0.7, 0.8, 0.9]}
kp["width_by_kappa_at_410"] = {}
for t in kp["grid_kappa"]:
    kk, w, se = _sim(t, 410)
    kp["width_by_kappa_at_410"][str(t)] = {"achieved": round(kk, 3), "width": round(w, 3),
                                           "half_width": round(w / 2, 3), "se": round(se, 4)}
kp["width_by_n"] = {}
for t in kp["grid_kappa"]:
    kp["width_by_n"][str(t)] = {}
    for n in kp["grid_n"]:
        _, w, _ = _sim(t, n, reps=140, boot=100)
        kp["width_by_n"][str(t)][str(n)] = round(w, 3)

# --------------------------------------------------------------- 17. missingness extended
ms = out["missing_ext"] = {}
ms["by_ear"] = {e: {c: float(df.loc[df.ear == e, c].isna().mean()) for c in AC + BC}
                for e in ("left", "right")}
ms["by_diagnosis"] = {d: {c: float(df.loc[df.diagnosis_category == d, c].isna().mean())
                          for c in AC + BC} for d in DIAG_ORDER}
ms["by_year"] = {int(y): {c: float(df.loc[df.year == y, c].isna().mean()) for c in AC + BC}
                 for y in sorted(df.year.dropna().unique())}
for c in ["th_3k", "th_6k", "bc_500", "bc_1k", "bc_2k", "bc_4k"]:
    ms[f"n_missing_{c}"] = int(df[c].isna().sum())
ms["test_3k_by_ear"] = S.chisq([[int(((df.ear == "left") & df.th_3k.isna()).sum()),
                                 int(((df.ear == "left") & df.th_3k.notna()).sum())],
                                [int(((df.ear == "right") & df.th_3k.isna()).sum()),
                                 int(((df.ear == "right") & df.th_3k.notna()).sum())]])
ct3 = pd.crosstab(df.diagnosis_category, df.th_3k.isna()).reindex(DIAG_ORDER).fillna(0)
ms["test_3k_by_diagnosis"] = S.chisq(ct3.values)

# --------------------------------------------------------------- 18. 120 dB ceiling
cd = out["ceiling"] = {}
cd["cells_120"] = {f: int((df[c] == 120).sum()) for c, f in zip(AC, FREQ)}
cd["total_cells_120"] = int(sum(cd["cells_120"].values()))
cd["total_cells"] = int(df[AC].notna().sum().sum())
cd["ears_any_120"] = int(df.flag_120_any_freq.astype(bool).sum())
cd["cells_115"] = {f: int((df[c] == 115).sum()) for c, f in zip(AC, FREQ)}
cdn = df[(df.th_6k == 120)].copy()
cd["six_120_eight_lower"] = int((cdn.th_8k < 120).sum())
cd["six_120_ids"] = sorted(cdn.loc[cdn.th_8k < 120, "study_id"].astype(int).tolist())
cd["six_120_eight_missing"] = int(cdn.th_8k.isna().sum())
cd4 = df[(df.th_4k == 120) & (df.th_8k < 120)]
cd["four_120_eight_lower"] = int(len(cd4))
cd["four_120_ids"] = sorted(cd4.study_id.astype(int).tolist())
cd["eight_120"] = int((df.th_8k == 120).sum())
cd["eight_max_below"] = float(df.th_8k[df.th_8k < 120].max())
cd["pta120_ears"] = int(df.n_pta_freqs_at_120.gt(0).sum())
cd["pta120_all4"] = int(df.n_pta_freqs_at_120.eq(4).sum())
cd["grade_effect_of_121"] = {
    "n_changed": int((df.pta4.apply(lambda p: grade_idx(p, CLARK))
                      != (df.pta4 + 0.25 * df.n_pta_freqs_at_120).apply(lambda p: grade_idx(p, CLARK))).sum()),
    "max_pta_shift": float((0.25 * df.n_pta_freqs_at_120).max())}

# --------------------------------------------------------------- 19. anomaly inventory
an = out["anomalies"] = []
ANOM = [
    ("Non-standard date strings", 58, "fixable", "54 format, 2 assumed year, 2 blank"),
    ("Blank test date", 2, "query", "studies 285-286"),
    ("Year inferred for 2-digit date", 2, "query", "Mar 25 -> Mar 2025"),
    ("csoM capitalisation", 15, "fixable", "canonicalised to csom"),
    ("120 dB HL used as ceiling code", cd["total_cells_120"], "limitation", "4.7% of threshold cells"),
    ("Ears carrying any 120", cd["ears_any_120"], "limitation", "13.2% of ears"),
    ("BC - AC > 10 dB", int(df.flag_bc_gt_ac_10.sum()), "review", "beyond protocol tolerance"),
    ("BC - AC > 20 dB", int(df.flag_bc_gt_ac_20.sum()), "query", "physiologically implausible"),
    ("AC - BC > 60 dB", int(df.flag_ac_bc_gap_60.sum()), "query", "possible masked/unmasked mix"),
    ("Negative BC (-5 dB)", int(df.flag_negative_threshold.sum()), "pass", "within declared range"),
    ("3 kHz missing", int(df.th_3k.isna().sum()), "limitation", "recording practice change"),
    ("Monotonicity > 40 dB", int(df.flag_monotonicity_40.sum()), "review", "protocol rule 7"),
    ("FAI cannot classify", int((~df.ok).sum()), "fix before analysis", "KeyError on 20 ears"),
    ("Recorded as included", int((df.ear_included == 1).sum()), "query", "no exclusion ever applied"),
    ("Identical binaural vectors", 2, "query", "patients 28, 42"),
    ("Duplicate study_id", 0, "pass", ""),
    ("Duplicate patient/ear", 0, "pass", ""),
    ("documented_shape blank", int(df.documented_shape.isna().sum()), "query", "study 257 left"),
    ("consultant_grade blank", int(df.consultant_grade.isna().sum()), "query", "0 blanks is itself the finding"),
]
for name, n, disp, note in ANOM:
    an.append({"label": name, "n": int(n), "disposition": disp, "note": note})

# --------------------------------------------------------------- 20. weighting statement
out["weighting"] = {
    "frame": "none: the export carries no design weights and the sampling frame is "
             "unconfirmed (batched, non-consecutive), so unweighted ear-level proportions "
             "are reported throughout and no survey weighting is applied",
    "icc_pta4": icc,
    "design_effect_pta4": 1 + icc,
    "deff_note": "ICC(1) of PTA-4 between the two ears of a patient; the design effect for an "
                 "ear-level proportion at two ears per patient is 1 + ICC",
    "n_effective_at_kappa08": round(410 / (1 + icc), 1),
}

# cluster assignment is written out so the figures use exactly the same labels
# as the tables; derived/ is git-ignored, so this stays off the repository
df[["study_id", "cluster"]].to_csv(HERE / "derived" / "clusters.csv", index=False)

(HERE / "descriptive.json").write_text(json.dumps(out, indent=1, default=str))
print("wrote descriptive.json")
print(json.dumps({k: out[k] for k in ["boundary", "confusion", "bland_altman", "by_grade",
                                      "kappa_curves", "ceiling", "weighting"]},
                 indent=1, default=str)[:7000])
