#!/usr/bin/env python3
"""
validate_oatuhc.py — batch processor for OAUTHC FAI external validation.

Reads the data-entry export (CSV from the web app, Excel, or Access),
  - validates protocol rules (data_dictionary.md v1.0)
  - runs the frozen FAI pipeline on every eligible ear (ear_included = 1)
  - appends derived columns: fai_score, fai_label, fai_config,
    membership_normal..profound, pta4, who_grade, borderline, mono_flag
  - writes an analysis-ready CSV + a QA report

Usage:
    python scripts/validate_oatuhc.py --input export.csv [--out results.csv] [--report qa.md]

Input column order (matches web app / Access export):
    study_id, patient_id, ear, test_month_year, age_years, sex,
    th_250, th_500, th_1k, th_2k, th_3k, th_4k, th_6k, th_8k,
    bc_500, bc_1k, bc_2k, bc_4k,
    diagnosis_category, consultant_grade, documented_shape,
    ear_included, exclusion_reason
"""

from __future__ import annotations

import argparse
import csv
import sys
import warnings
from pathlib import Path

import numpy as np

np.seterr(all="ignore")
warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "webapp"))

THRESH = ["th_250", "th_500", "th_1k", "th_2k", "th_3k", "th_4k", "th_6k", "th_8k"]
CANON = [250, 500, 1000, 2000, 3000, 4000, 6000, 8000]
WHO_BOUNDS = [25, 40, 60, 80]

REQUIRED_COLS = ["study_id", "patient_id", "ear", *THRESH,
                 "diagnosis_category", "ear_included"]


def _f(v):
    """Coerce CSV value to float or None."""
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def pta4(r: dict) -> float | None:
    vals = [_f(r.get(c)) for c in ("th_500", "th_1k", "th_2k", "th_4k")]
    vals = [v for v in vals if v is not None]
    if len(vals) == 4:
        return round(float(np.mean(vals)), 1)
    return None


def who_grade(pta: float | None) -> str | None:
    if pta is None:
        return None
    if pta < 26: return "normal"
    if pta < 41: return "mild"
    if pta < 61: return "moderate"
    if pta < 81: return "severe"
    return "profound"


def borderline(pta: float | None) -> int | None:
    if pta is None:
        return None
    return 1 if any(abs(pta - b) <= 5 for b in WHO_BOUNDS) else 0


def mono_flag(r: dict) -> int:
    seq = [_f(r.get(c)) for c in THRESH]
    pairs = [(a, b) for a, b in zip(seq[:-1], seq[1:]) if a is not None and b is not None]
    if not pairs:
        return 0
    return 1 if max(abs(a - b) for a, b in pairs) > 40 else 0


def to_sparse(r: dict) -> dict[int, float]:
    """CSV row (string keys) -> {freq_hz: dB} with int keys."""
    out = {}
    for col, f in zip(THRESH, CANON):
        v = r.get(col)
        if v is not None and v != "":
            try:
                out[f] = float(v)
            except (TypeError, ValueError):
                continue
    return out


def validate_rows(rows: list[dict]) -> list[dict]:
    """Rule checks per data_dictionary v1.0. Returns list of issue dicts."""
    issues = []
    seen_study = set()
    seen_pair = set()
    for i, r in enumerate(rows, start=2):  # +1 for header
        sid = r.get("study_id")
        if sid is None or str(sid) == "":
            issues.append({"row": i, "study_id": sid, "issue": "missing study_id"})
        elif sid in seen_study:
            issues.append({"row": i, "study_id": sid, "issue": "duplicate study_id"})
        else:
            seen_study.add(sid)

        pair = (r.get("patient_id"), r.get("ear"))
        if pair in seen_pair:
            issues.append({"row": i, "study_id": sid, "issue": "duplicate (patient_id, ear)"})
        else:
            seen_pair.add(pair)

        age = r.get("age_years")
        if age is not None and age != "":
            try:
                if not (18 <= float(age) <= 110):
                    issues.append({"row": i, "study_id": sid, "issue": f"age {age} outside 18-110"})
            except ValueError:
                issues.append({"row": i, "study_id": sid, "issue": f"age non-numeric: {age}"})

        for c in THRESH:
            fv = _f(r.get(c))
            if fv is not None and not (-10 <= fv <= 120):
                issues.append({"row": i, "study_id": sid, "issue": f"{c}={r.get(c)} outside -10..120"})

        if mono_flag(r):
            issues.append({"row": i, "study_id": sid, "issue": "monotonicity: adjacent jump > 40 dB (review only)"})
    return issues


def process(rows: list[dict]) -> list[dict]:
    """Run FAI on eligible ears; return enriched rows."""
    from services.fai_service import classify_values

    out = []
    for r in rows:
        row = dict(r)
        pta = pta4(row)
        row["pta4"] = pta
        row["who_grade"] = who_grade(pta)
        row["borderline"] = borderline(pta)
        row["mono_flag"] = mono_flag(row)

        included = row.get("ear_included")
        if included in (1, "1", 1.0):
            sparse = to_sparse(row)
            if not sparse:
                row.update({"fai_score": None, "fai_label": "NO_DATA",
                            "fai_config": None, "fai_error": "no thresholds"})
                out.append(row)
                continue
            try:
                res = classify_values(thresholds_left=sparse)
                if "error" in res:
                    row.update({"fai_score": None, "fai_label": None,
                                "fai_config": None, "fai_error": res["error"]})
                else:
                    row.update({
                        "fai_score": res.get("fai_score"),
                        "fai_label": res.get("fai_label"),
                        "fai_config": res.get("configuration_label"),
                        "fai_error": "",
                    })
                    for k, v in (res.get("threshold_memberships") or {}).items():
                        row[f"membership_{k}"] = round(float(v), 4) if v is not None else None
            except Exception as e:  # noqa: BLE001 — record and continue
                row.update({"fai_score": None, "fai_label": None,
                            "fai_config": None, "fai_error": str(e)[:120]})
        else:
            row.update({"fai_score": None, "fai_label": "EXCLUDED",
                        "fai_config": None, "fai_error": ""})
        out.append(row)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="CSV export from web app / Access / Excel")
    ap.add_argument("--out", default=None, help="analysis-ready CSV (default: <input>_fai.csv)")
    ap.add_argument("--report", default=None, help="QA report markdown path")
    args = ap.parse_args()

    src = Path(args.input)
    if not src.exists():
        raise SystemExit(f"❌ Input not found: {src}")

    with open(src, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    if not rows:
        raise SystemExit("❌ Empty input file")

    # Missing columns check
    missing = [c for c in REQUIRED_COLS if c not in rows[0]]
    if missing:
        print(f"⚠️  Missing columns (will be treated as blank): {missing}")

    print(f"📥 Loaded {len(rows)} ear records from {src.name}")

    # 1. Rules
    issues = validate_rows(rows)
    print(f"\n🔍 Rule check: {len(issues)} issue(s)")
    for iss in issues[:15]:
        print(f"   row {iss['row']} | study {iss['study_id']} | {iss['issue']}")
    if len(issues) > 15:
        print(f"   … and {len(issues)-15} more")

    # 2. FAI
    print("\n🧠 Running frozen FAI pipeline on eligible ears…")
    enriched = process(rows)
    n_fai = sum(1 for r in enriched if r.get("fai_score") is not None)
    n_err = sum(1 for r in enriched if r.get("fai_error"))
    print(f"   {n_fai} ears classified")
    if n_err:
        print(f"   ⚠️  {n_err} ears could NOT be classified by the frozen FIS")
        print("       (typically extreme non-monotonic shapes, >40 dB adjacent jump —")
        print("        review the monotonicity flags; the FIS is frozen per protocol)")

    # 3. Outputs
    out_path = Path(args.out) if args.out else src.with_name(src.stem + "_fai.csv")
    fieldnames = list(enriched[0].keys())
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(enriched)
    print(f"\n✅ Analysis-ready CSV: {out_path}")

    if args.report or True:
        rep = Path(args.report) if args.report else src.with_name(src.stem + "_qa.md")
        with open(rep, "w", encoding="utf-8") as f:
            f.write(f"# OAUTHC FAI Validation — Batch QA Report\n\n")
            f.write(f"- Input: `{src.name}`\n")
            f.write(f"- Records: {len(rows)}\n")
            f.write(f"- Ears classified by FAI: {n_fai}\n")
            f.write(f"- Issues: {len(issues)}\n\n")
            if issues:
                f.write("| Row | study_id | Issue |\n|---|---|---|\n")
                for iss in issues:
                    f.write(f"| {iss['row']} | {iss['study_id']} | {iss['issue']} |\n")
            f.write(f"\n*Generated by validate_oatuhc.py*\n")
        print(f"📄 QA report: {rep}")

    # Summary stats
    labels = {}
    for r in enriched:
        lb = r.get("fai_label")
        if lb and lb not in ("EXCLUDED", "NO_DATA"):
            labels[lb] = labels.get(lb, 0) + 1
    if labels:
        print("\n📊 FAI label distribution (eligible ears):")
        for lb, n in sorted(labels.items()):
            print(f"   {lb:20s} {n}")


if __name__ == "__main__":
    main()
