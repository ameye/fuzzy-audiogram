#!/usr/bin/env python3
"""clean.py — non-destructive cleaning pass for the OAUTHC FAI validation export.

The raw export is NEVER modified. This script reads it, writes a new analysis
file, and records every change it made to a separate change log so that the
cleaning step is auditable and reversible.

What it does
------------
1. Canonicalises `test_month_year` to ISO `YYYY-MM` (case, abbreviation
   spelling, 2-digit year, "June" vs "Jun"). Ambiguous values are NOT guessed
   silently: each one is logged with rule `ASSUMED`.
2. Canonicalises `diagnosis_category` and `documented_shape` to lower-case
   protocol tokens.
3. Adds audit flag columns (see FLAGS) that mark suspect records WITHOUT
   changing any threshold value. Downstream analysis decides what to do with
   them; nothing is dropped here.
4. Optionally writes a sensitivity variant in which 120 dB HL is treated as a
   right-censored ceiling (`--censor-120`), again to a separate file.

Usage
-----
    python clean.py                     # writes derived/analysis_clean.csv
    python clean.py --censor-120        # also writes derived/analysis_censored120.csv

Outputs (all under derived/, none of which are committed — patient-level)
    analysis_clean.csv, cleaning_log.csv, cleaning_summary.csv
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw_export.csv"
DERIVED = HERE / "derived"

AC = ["th_250", "th_500", "th_1k", "th_2k", "th_3k", "th_4k", "th_6k", "th_8k"]
BC = ["bc_500", "bc_1k", "bc_2k", "bc_4k"]
BC_AC = {"bc_500": "th_500", "bc_1k": "th_1k", "bc_2k": "th_2k", "bc_4k": "th_4k"}
PTA_COLS = ["th_500", "th_1k", "th_2k", "th_4k"]

MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}
# spelling aliases seen in the export
ALIAS = {"seo": "sep", "sept": "sep", "msr": "mar", "june": "jun", "july": "jul"}

DIAG_MAP = {
    "csom": "csom", "csoM": "csom", "CSOM": "csom",
    "otosclerosis": "otosclerosis", "nihl": "nihl", "presbyacusis": "presbyacusis",
    "ssnhl": "ssnhl", "ototoxicity": "ototoxicity", "meniere": "meniere",
    "other": "other", "not_documented": "not_documented",
}
SHAPE_MAP = {"flat": "flat", "sloping": "sloping", "notched": "notched", "rising": "rising"}

changes: list[dict] = []


def log(sid, field, old, new, rule, action):
    changes.append({"study_id": sid, "field": field, "old": old, "new": new,
                    "rule": rule, "action": action})


def canon_month(value, sid):
    """Return ISO YYYY-MM, or pd.NA. Logs every non-ISO input."""
    if pd.isna(value) or str(value).strip() == "":
        log(sid, "test_month_year", "", "", "DATE_BLANK", "left missing (query collector)")
        return pd.NA
    raw = str(value).strip()
    parts = raw.split()
    if len(parts) != 2:
        log(sid, "test_month_year", raw, "", "DATE_UNPARSEABLE", "left missing (query collector)")
        return pd.NA
    tok, yr = parts[0], parts[1]
    mon = ALIAS.get(tok.lower(), tok.lower()[:3])
    assumed = False
    if len(yr) == 2:                      # "Mar 25" -> 2025
        yr = "20" + yr
        assumed = True
    if mon not in MONTHS or not yr.isdigit():
        log(sid, "test_month_year", raw, "", "DATE_UNPARSEABLE", "left missing (query collector)")
        return pd.NA
    iso = f"{int(yr):04d}-{MONTHS[mon]:02d}"
    standard = f"{mon[:3].capitalize()} {int(yr)}"
    if assumed:
        log(sid, "test_month_year", raw, iso, "DATE_ASSUMED_YEAR", "canonicalised (year assumed)")
    elif raw != standard:
        log(sid, "test_month_year", raw, iso, "DATE_FORMAT", "canonicalised")
    return iso


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--censor-120", action="store_true",
                    help="also write a sensitivity file with 120 dB HL treated as right-censored")
    args = ap.parse_args()

    if not RAW.exists():
        raise SystemExit(f"raw export not found: {RAW}")

    df = pd.read_csv(RAW)
    n_raw = len(df)
    df["_row"] = np.arange(2, n_raw + 2)      # spreadsheet row, for the log

    # ---- 1. dates ----
    df["test_year_month"] = [canon_month(v, s) for v, s in zip(df.test_month_year, df.study_id)]

    # ---- 2. categorical canon ----
    for i, r in df.iterrows():
        v = r.diagnosis_category
        new = DIAG_MAP.get(str(v).strip(), str(v).strip().lower())
        if new != v:
            log(int(r.study_id), "diagnosis_category", v, new, "CATEGORY_CASE", "canonicalised")
            df.at[i, "diagnosis_category"] = new
        v = r.documented_shape
        if pd.notna(v):
            new = SHAPE_MAP.get(str(v).strip().lower(), str(v).strip().lower())
            if new != v:
                log(int(r.study_id), "documented_shape", v, new, "CATEGORY_CASE", "canonicalised")
                df.at[i, "documented_shape"] = new

    # ---- 3. audit flags (thresholds untouched) ----
    df["pta4"] = df[PTA_COLS].mean(axis=1)

    df["flag_120_any_freq"] = (df[AC] == 120).any(axis=1).astype(int)
    df["n_freq_at_120"] = (df[AC] == 120).sum(axis=1)
    df["n_pta_freqs_at_120"] = (df[PTA_COLS] == 120).sum(axis=1)

    rev = pd.Series(0, index=df.index)
    rev20 = pd.Series(0, index=df.index)
    gap60 = pd.Series(0, index=df.index)
    for bc, ac in BC_AC.items():
        d = df[bc] - df[ac]
        rev = np.maximum(rev, d.fillna(0).clip(lower=0))
        rev20 = np.maximum(rev20, (d > 20).astype(int) * 1)
        gap60 = np.maximum(gap60, (df[ac] - df[bc] > 60).astype(int) * 1)
    df["max_bc_minus_ac"] = rev.round(1)
    df["flag_bc_gt_ac_10"] = (rev > 10).astype(int)      # beyond protocol tolerance
    df["flag_bc_gt_ac_20"] = rev20.astype(int)           # physiologically implausible
    df["flag_ac_bc_gap_60"] = gap60.astype(int)

    seq = df[AC]
    jumps = []
    for _, r in seq.iterrows():
        vals = [(a, b) for a, b in zip(r[:-1], r[1:]) if pd.notna(a) and pd.notna(b)]
        jumps.append(max((abs(a - b) for a, b in vals), default=0))
    df["max_adjacent_jump"] = jumps
    df["flag_monotonicity_40"] = (df["max_adjacent_jump"] > 40).astype(int)

    df["flag_age_out_of_range"] = (~df.age_years.between(18, 110)).astype(int)
    df["flag_date_blank"] = df.test_year_month.isna().astype(int)
    df["flag_negative_threshold"] = (df[AC + BC] < 0).any(axis=1).astype(int)

    # ---- 4. write ----
    DERIVED.mkdir(exist_ok=True)
    out = DERIVED / "analysis_clean.csv"
    df.drop(columns=["_row"]).to_csv(out, index=False)

    logdf = pd.DataFrame(changes)
    logdf.to_csv(DERIVED / "cleaning_log.csv", index=False)

    summary = (logdf.groupby(["field", "rule", "action"]).size()
               .reset_index(name="n").sort_values(["field", "rule"]))
    summary.to_csv(DERIVED / "cleaning_summary.csv", index=False)

    print(f"raw rows            : {n_raw}")
    print(f"analysis rows       : {len(df)}  (no rows dropped)")
    print(f"logged changes      : {len(logdf)}")
    print(f"written             : {out}")
    print("\nchange summary:")
    print(summary.to_string(index=False))
    print("\nflag counts (ears):")
    for c in [c for c in df.columns if c.startswith("flag_")]:
        print(f"  {c:28s} {int(df[c].sum()):4d}")

    if args.censor_120:
        cens = df.copy()
        for c in AC:
            cens[c] = cens[c].where(cens[c] != 120, 121)   # >120 marker
        cens["pta4_original"] = df["pta4"]
        cens["pta4"] = cens[PTA_COLS].mean(axis=1)
        p = DERIVED / "analysis_censored120.csv"
        cens.to_csv(p, index=False)
        print(f"\nsensitivity variant : {p}")


if __name__ == "__main__":
    main()
