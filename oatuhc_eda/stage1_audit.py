"""Stage-1 audit statistics for the OAUTHC FAI validation dataset.

Reads the untouched raw export and emits every quantity the report cites.
Nothing is written back to the source file.
"""
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

RAW = Path("raw_export.csv")
df = pd.read_csv(RAW)

AC = ["th_250", "th_500", "th_1k", "th_2k", "th_3k", "th_4k", "th_6k", "th_8k"]
BC = ["bc_500", "bc_1k", "bc_2k", "bc_4k"]
BC_AC = dict(zip(BC, ["th_500", "th_1k", "th_2k", "th_4k"]))
PTA_COLS = ["th_500", "th_1k", "th_2k", "th_4k"]
ORDER = ["normal", "mild", "moderate", "moderately_severe", "severe", "profound"]

MONTHS = {m.lower(): i for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], 1)}
ALIAS = {"seo": "sep", "msr": "mar", "sept": "sep", "june": "jun", "july": "jul"}


def parse_month(s):
    if pd.isna(s) or str(s).strip() == "":
        return pd.NaT
    parts = str(s).strip().split()
    if len(parts) != 2:
        return pd.NaT
    mon = ALIAS.get(parts[0].lower(), parts[0].lower()[:3])
    yr = parts[1]
    if len(yr) == 2:
        yr = "20" + yr
    if mon not in MONTHS or not yr.isdigit():
        return pd.NaT
    return pd.Timestamp(int(yr), MONTHS[mon], 1)


df["dt"] = df["test_month_year"].apply(parse_month)
df["pta4"] = df[PTA_COLS].mean(axis=1)


def grade(p, cuts):
    for i, c in enumerate(cuts):
        if p <= c:
            return i
    return len(cuts)


CLARK = [25, 40, 55, 70, 90]
WHO5 = [25, 40, 60, 80]
WHO21 = [20, 35, 50, 65, 80, 95]
LBL6 = ["normal", "mild", "moderate", "moderately_severe", "severe", "profound"]
LBL5 = ["normal", "mild", "moderate", "severe", "profound"]
LBL7 = ["normal", "mild", "moderate", "moderately_severe", "severe", "profound", "complete"]

df["who_clark"] = df.pta4.apply(lambda p: LBL6[grade(p, CLARK)])
df["who5"] = df.pta4.apply(lambda p: LBL5[grade(p, WHO5)])
df["who21"] = df.pta4.apply(lambda p: LBL7[grade(p, WHO21)])


def near_boundary(pta, cuts, tol=5.0):
    return int(any(abs(pta - c) <= tol for c in cuts))


df["border_clark"] = df.pta4.apply(lambda p: near_boundary(p, CLARK))
df["border_who5"] = df.pta4.apply(lambda p: near_boundary(p, WHO5))
df["border_who21"] = df.pta4.apply(lambda p: near_boundary(p, WHO21))

out = {}

out["structure"] = {
    "rows": len(df),
    "patients": int(df.patient_id.nunique()),
    "ears_per_patient": {str(k): int(v) for k, v in df.groupby("patient_id").size().value_counts().items()},
    "dup_study_id": int(df.study_id.duplicated().sum()),
    "dup_patient_ear": int(df.duplicated(["patient_id", "ear"]).sum()),
    "patients_multiple_ages": int((df.groupby("patient_id").age_years.nunique() > 1).sum()),
    "ear_included": {str(k): int(v) for k, v in df.ear_included.value_counts().items()},
    "exclusion_reason_nonnull": int(df.exclusion_reason.notna().sum()),
    "left": int((df.ear == "left").sum()),
    "right": int((df.ear == "right").sum()),
}

raw_dates = df.test_month_year.value_counts(dropna=False)
out["dates"] = {
    "distinct_raw_strings": int(df.test_month_year.nunique(dropna=True)),
    "unparsed_rows": df.loc[df.dt.isna(), ["study_id", "test_month_year"]].astype(str).values.tolist(),
    "min": str(df.dt.min().date()) if df.dt.notna().any() else None,
    "max": str(df.dt.max().date()) if df.dt.notna().any() else None,
    "nonstandard": {str(k): int(v) for k, v in raw_dates[raw_dates.index.map(
        lambda x: isinstance(x, str) and not re.fullmatch(r"[A-Z][a-z]{2} \d{4}", x))].items()},
    "by_year": {str(k): int(v) for k, v in df.dt.dt.year.value_counts().sort_index().items()},
    "months_present": sorted(df.dt.dt.to_period("M").dropna().unique().astype(str)),
    "blank_ids": df.loc[df.test_month_year.isna(), "study_id"].tolist(),
}
cov = {}
for y, g in df.dropna(subset=["dt"]).groupby(df.dt.dt.year):
    cov[str(int(y))] = sorted(int(m) for m in g.dt.dt.month.unique())
out["dates"]["months_by_year"] = cov

out["categories"] = {
    "diagnosis_raw": {str(k): int(v) for k, v in df.diagnosis_category.value_counts(dropna=False).items()},
    "shape_raw": {str(k): int(v) for k, v in df.documented_shape.value_counts(dropna=False).items()},
    "consultant_raw": {str(k): int(v) for k, v in df.consultant_grade.value_counts(dropna=False).items()},
    "sex": {str(k): int(v) for k, v in df.sex.value_counts(dropna=False).items()},
    "n_missing_consultant": int(df.consultant_grade.isna().sum()),
    "n_missing_shape": int(df.documented_shape.isna().sum()),
    "n_missing_diagnosis": int(df.diagnosis_category.isna().sum()),
}


def q(s, p):
    return float(np.percentile(s.dropna(), p))


out["age"] = {}
for lab, sub in [("all", df), ("male", df[df.sex == 1]), ("female", df[df.sex == 2])]:
    a = sub.age_years
    out["age"][lab] = {"n": int(a.size), "median": float(a.median()), "q1": q(a, 25),
                       "q3": q(a, 75), "min": int(a.min()), "max": int(a.max()),
                       "mean": round(float(a.mean()), 1), "sd": round(float(a.std()), 1)}
out["age"]["under18"] = int((df.age_years < 18).sum())
out["age"]["over110"] = int((df.age_years > 110).sum())
out["age"]["pct_end_in_0"] = round(float((df.age_years % 10 == 0).mean()), 3)
out["age"]["pct_end_in_5"] = round(float((df.age_years % 5 == 0).mean()), 3)
pat_age = df.groupby("patient_id").age_years.first()
out["age"]["patients"] = {
    "n": int(pat_age.size), "median": float(pat_age.median()),
    "q1": q(pat_age, 25), "q3": q(pat_age, 75), "min": int(pat_age.min()), "max": int(pat_age.max())}
for lab, sub in [("male", df[df.sex == 1]), ("female", df[df.sex == 2])]:
    p = sub.groupby("patient_id").age_years.first()
    out["age"][lab]["patients"] = {"n": int(p.size), "median": float(p.median()),
                                  "q1": q(p, 25), "q3": q(p, 75)}

out["thresholds"] = {}
for c in AC + BC:
    s = df[c].dropna()
    out["thresholds"][c] = {"n": int(s.size), "missing": int(df[c].isna().sum()),
                            "median": float(s.median()), "q1": q(s, 25), "q3": q(s, 75),
                            "min": float(s.min()), "max": float(s.max())}
out["thresholds"]["n_cells_120"] = int((df[AC] == 120).sum().sum())
out["thresholds"]["n_cells_total"] = int(df[AC].notna().sum().sum())
out["thresholds"]["ears_any_120"] = int((df[AC] == 120).any(axis=1).sum())
out["thresholds"]["cells_120_by_freq"] = {k: int(v) for k, v in (df[AC] == 120).sum().items()}
out["thresholds"]["n_cells_115"] = int((df[AC] == 115).sum().sum())
out["thresholds"]["cells_115_by_freq"] = {k: int(v) for k, v in (df[AC] == 115).sum().items()}
out["thresholds"]["ears_120_in_pta"] = int((df[PTA_COLS] == 120).any(axis=1).sum())
out["thresholds"]["ears_all_pta_120"] = [[int(s), e] for s, e in df.loc[
    (df[PTA_COLS] == 120).all(axis=1), ["study_id", "ear"]].values.tolist()]
out["thresholds"]["ids_120_in_pta"] = df.loc[(df[PTA_COLS] == 120).any(axis=1),
                                             "study_id"].astype(int).tolist()
out["thresholds"]["ids_120_4k_8k_lower"] = df.loc[(df.th_4k == 120) & (df.th_8k < 120),
                                                   ["study_id", "th_4k", "th_6k", "th_8k"]].values.tolist()
out["thresholds"]["n_120_4k_8k_lower"] = int(((df.th_4k == 120) & (df.th_8k < 120)).sum())
out["thresholds"]["n_120_6k_8k_lower"] = int(((df.th_6k == 120) & (df.th_8k < 120)).sum())
out["thresholds"]["n_120_and_115"] = int(((df[AC] == 120).any(axis=1) & (df[AC] == 115).any(axis=1)).sum())
out["thresholds"]["non_multiple_of_5"] = int(sum(((df[c].dropna() % 5) != 0).sum() for c in AC + BC))
out["thresholds"]["negative_values"] = int(sum((df[c] < 0).sum() for c in AC + BC))
out["thresholds"]["ids_negative"] = [[int(s), e] for s, e in df.loc[(df[AC + BC] < 0).any(axis=1),
                                                                    ["study_id", "ear"]].values.tolist()]

df["pta4_cens"] = df[PTA_COLS].replace(120, 121).mean(axis=1)
df["who_clark_cens"] = df.pta4_cens.apply(lambda p: LBL6[grade(p, CLARK)])
out["thresholds"]["grade_changes_if_120_censored"] = int((df.who_clark != df.who_clark_cens).sum())
out["thresholds"]["max_pta4_shift"] = round(float((df.pta4_cens - df.pta4).abs().max()), 2)

out["missing"] = {c: int(df[c].isna().sum()) for c in AC + BC}
out["missing"]["by_year_3k"] = {
    str(int(y)): {"n": int(len(g)), "missing_3k": int(g.th_3k.isna().sum()),
                  "missing_6k": int(g.th_6k.isna().sum())}
    for y, g in df.dropna(subset=["dt"]).groupby(df.dt.dt.year)}
out["missing"]["by_ear_3k"] = {str(k): int(v) for k, v in df.groupby("ear").th_3k.apply(
    lambda s: s.isna().sum()).items()}
out["missing"]["by_ear_6k"] = {str(k): int(v) for k, v in df.groupby("ear").th_6k.apply(
    lambda s: s.isna().sum()).items()}
out["missing"]["ears_complete_pta4"] = int(df[PTA_COLS].notna().all(axis=1).sum())
out["missing"]["ears_any_bc"] = int(df[BC].notna().any(axis=1).sum())
out["missing"]["ears_all_bc"] = int(df[BC].notna().all(axis=1).sum())

rows_rev, rows_gap = [], []
for bc, ac in BC_AC.items():
    d = df[bc] - df[ac]
    rows_rev.append({"freq": bc, "bc_gt_ac": int((d > 0).sum()), "gt10": int((d > 10).sum()),
                     "gt20": int((d > 20).sum()), "max": float(d.max().round(1))})
    g = df[ac] - df[bc]
    rows_gap.append({"freq": ac, "gt40": int((g > 40).sum()), "gt60": int((g > 60).sum()),
                     "max": float(g.max().round(1))})
out["bc"] = {"reverse_by_freq": rows_rev, "gap_by_freq": rows_gap}

rev_any10 = pd.Series(False, index=df.index)
rev_any20 = pd.Series(False, index=df.index)
gap_any60 = pd.Series(False, index=df.index)
for bc, ac in BC_AC.items():
    rev_any10 |= (df[bc] - df[ac]) > 10
    rev_any20 |= (df[bc] - df[ac]) > 20
    gap_any60 |= (df[ac] - df[bc]) > 60
out["bc"]["ears_reverse_gt10"] = int(rev_any10.sum())
out["bc"]["ears_reverse_gt20"] = int(rev_any20.sum())
out["bc"]["ears_gap_gt60"] = int(gap_any60.sum())
out["bc"]["ears_reverse_gt10_ids"] = sorted(df.loc[rev_any10, "study_id"].astype(int).tolist())
out["bc"]["ears_gap_gt60_ids"] = sorted(df.loc[gap_any60, "study_id"].astype(int).tolist())

detail = []
for i, r in df.iterrows():
    for bc, ac in BC_AC.items():
        if pd.notna(r[bc]) and pd.notna(r[ac]):
            d = r[bc] - r[ac]
            if d > 10 or (r[ac] - r[bc]) > 60:
                detail.append({"study_id": int(r.study_id), "ear": r.ear, "freq": ac,
                               "ac": float(r[ac]), "bc": float(r[bc]), "bc_minus_ac": float(d)})
out["bc"]["detail"] = detail

mono = []
for i, r in df.iterrows():
    seq = [r[c] for c in AC]
    prs = [(a, b) for a, b in zip(seq[:-1], seq[1:]) if pd.notna(a) and pd.notna(b)]
    if prs:
        mx = max(abs(a - b) for a, b in prs)
        if mx > 40:
            mono.append({"study_id": int(r.study_id), "ear": r.ear, "jump": float(mx)})
out["monotonicity"] = {"n": len(mono), "ids": [m["study_id"] for m in mono], "detail": mono}

out["grades"] = {
    "clark": {k: int(v) for k, v in df.who_clark.value_counts().reindex(LBL6).fillna(0).items()},
    "who5": {k: int(v) for k, v in df.who5.value_counts().reindex(LBL5).fillna(0).items()},
    "who21": {k: int(v) for k, v in df.who21.value_counts().reindex(LBL7).fillna(0).items()},
    "consultant": {k: int(v) for k, v in df.consultant_grade.value_counts().reindex(LBL6).fillna(0).items()},
}
out["pta4"] = {"median": float(df.pta4.median()), "q1": q(df.pta4, 25), "q3": q(df.pta4, 75),
               "min": float(df.pta4.min()), "max": float(df.pta4.max()),
               "mean": round(float(df.pta4.mean()), 1)}
out["borderline"] = {
    "clark": {"n": int(df.border_clark.sum()), "pct": round(100 * df.border_clark.mean(), 1)},
    "who5": {"n": int(df.border_who5.sum()), "pct": round(100 * df.border_who5.mean(), 1)},
    "who21": {"n": int(df.border_who21.sum()), "pct": round(100 * df.border_who21.mean(), 1)},
}
for k, cuts in [("clark", CLARK), ("who5", WHO5), ("who21", WHO21)]:
    d = df.pta4.apply(lambda p: min(abs(p - c) for c in cuts))
    out["borderline"][k]["dist_median"] = float(d.median())
    out["borderline"][k]["pct_within_2"] = round(100 * float((d <= 2).mean()), 1)


def kappa_quad(a, b):
    a = np.asarray(a, dtype=int)
    b = np.asarray(b, dtype=int)
    k = max(a.max(), b.max()) + 1
    O = np.zeros((k, k))
    for x, y in zip(a, b):
        O[x, y] += 1
    O = O / O.sum()
    r = O.sum(1)
    c = O.sum(0)
    E = np.outer(r, c)
    W = np.array([[(i - j) ** 2 for j in range(k)] for i in range(k)]) / ((k - 1) ** 2)
    return 1 - (W * O).sum() / (W * E).sum()


out["consultant_vs"] = {}
for name, col, lbl in [("clark", "who_clark", LBL6), ("who5", "who5", LBL5), ("who21", "who21", LBL7)]:
    sub = df[df.consultant_grade.isin(lbl)]
    a = sub.consultant_grade.map({g: i for i, g in enumerate(lbl)})
    b = sub[col].map({g: i for i, g in enumerate(lbl)})
    ok = a.notna() & b.notna()
    out["consultant_vs"][name] = {
        "n": int(ok.sum()),
        "exact": round(float((a[ok] == b[ok]).mean()), 3),
        "kappa_quad": round(float(kappa_quad(a[ok], b[ok])), 3),
        "within1": round(float((a[ok] - b[ok]).abs().le(1).mean()), 3),
        "spearman": round(float(sub.pta4.corr(
            sub.consultant_grade.map({g: i for i, g in enumerate(lbl)}), method="spearman")), 3),
    }
rng = df.groupby("consultant_grade").pta4.agg(["min", "max"]).reindex(LBL6)
out["consultant_vs"]["pta4_ranges"] = {k: [float(v["min"]), float(v["max"])] for k, v in rng.iterrows()}

out["crosstab_consultant_clark"] = {
    str(k): {str(k2): int(v2) for k2, v2 in v.items()}
    for k, v in pd.crosstab(df.consultant_grade, df.who_clark).reindex(index=LBL6, columns=LBL6).fillna(0).iterrows()}

print(json.dumps(out, indent=1, default=str))
Path("stage1.json").write_text(json.dumps(out, indent=1, default=str))
