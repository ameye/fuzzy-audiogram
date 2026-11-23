#!/usr/bin/env python3
"""Cohort description for Table 1 and the asymmetry sentence.

Reads the three vendored NHANES cycles, applies the same cleaning and the same
SEQN-keyed participant split as scripts/pipeline_participant.py, and writes
data/output_participant/cohort_stats.json.

Kept separate from the classification pipeline because none of these values
depend on the membership functions: they describe the cohort, not the
classifier. Computing them here means the manuscript's Table 1 has a code path
like every other number rather than being transcribed from an earlier run.
"""
import hashlib
import json
import os
import sys
from pathlib import Path

import numpy as np

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))

from fuzzy_audiogram.combined_data import (  # noqa: E402
    FREQUENCIES, clean_ears, extract_combined_audiometry, load_combined_nhanes)

OUT = Path(os.environ.get("FA_OUT_DIR", PROJECT / "data" / "output_participant"))
PTA_IDX = [1, 2, 3, 5]
GRADES = ["Normal", "Mild", "Moderate", "Moderately Severe", "Severe", "Profound"]


def _in_test(p, seed=42, holdout=0.20):
    h = hashlib.md5(f"{int(p)}:{seed}".encode()).hexdigest()
    return (int(h[:8], 16) % 10_000) < int(holdout * 10_000)


def who_grade(v):
    if v <= 25: return 0
    if v <= 40: return 1
    if v <= 55: return 2
    if v <= 70: return 3
    if v <= 90: return 4
    return 5


def summarise(rows, meta):
    ages = np.array([meta[s]["age"] for s, *_ in rows], float)
    female = np.array([meta[s]["female"] for s, *_ in rows], float)
    pta = np.array([np.mean([th[i] for i in PTA_IDX]) for *_, th in rows], float)
    grades = np.array([who_grade(v) for v in pta])
    return {
        "ears": len(rows),
        "participants": len({s for s, *_ in rows}),
        "age_mean": round(float(ages.mean()), 1),
        "age_sd": round(float(ages.std(ddof=1)), 1),
        "age_median": round(float(np.median(ages)), 1),
        "age_q1": round(float(np.percentile(ages, 25)), 1),
        "age_q3": round(float(np.percentile(ages, 75)), 1),
        "female_pct": round(float(female.mean()) * 100, 1),
        "pta_mean": round(float(pta.mean()), 1),
        "pta_sd": round(float(pta.std(ddof=1)), 1),
        "grades": {g: round(float((grades == i).mean()) * 100, 1)
                   for i, g in enumerate(GRADES)},
    }


def main():
    print("[1] Loading combined NHANES adult cycles...")
    raw = load_combined_nhanes()
    audio = extract_combined_audiometry(raw)
    ears = clean_ears(audio)

    meta = (audio.drop_duplicates("seqn").set_index("seqn")[["age", "female"]]
            .to_dict(orient="index"))
    participants = sorted({s for s, *_ in ears})
    test_ppl = {p for p in participants if _in_test(p)}
    train_rows = [r for r in ears if r[0] not in test_ppl]
    test_rows = [r for r in ears if r[0] in test_ppl]

    stats = {
        "cohort": "NHANES 20-69 y (AUX1 1999-2000, AUX_G 2011-2012, AUX_I 2015-2016)",
        "participants_all": len(raw),
        "ears_all": len(ears),
        "participants_with_complete_ears": len({s for s, *_ in ears}),
        "train": summarise(train_rows, meta),
        "test": summarise(test_rows, meta),
    }

    # Inter-aural asymmetry over participants with both ears retained.
    both = {}
    for seqn, cycle, side, th in ears:
        both.setdefault(seqn, {})[side] = th
    asym = np.array([np.max(np.abs(np.array(d["left"]) - np.array(d["right"])))
                     for d in both.values() if "left" in d and "right" in d])
    stats["asymmetry"] = {
        "n_participants": int(len(asym)),
        "mean_db": round(float(asym.mean()), 1),
        "median_db": round(float(np.median(asym)), 1),
        "pct_gt_15db": round(float((asym > 15).mean()) * 100, 1),
    }

    print(f"  participants {stats['participants_all']:,}  ears {stats['ears_all']:,}")
    print(f"  train {stats['train']['ears']:,} ears / {stats['train']['participants']:,} ppl"
          f"   test {stats['test']['ears']:,} ears / {stats['test']['participants']:,} ppl")
    print(f"  test grades {stats['test']['grades']}")
    print(f"  asymmetry mean {stats['asymmetry']['mean_db']} dB, "
          f"{stats['asymmetry']['pct_gt_15db']}% > 15 dB "
          f"(n={stats['asymmetry']['n_participants']:,})")

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "cohort_stats.json").write_text(json.dumps(stats, indent=2), encoding="utf-8")
    print("  saved:", OUT / "cohort_stats.json")


if __name__ == "__main__":
    main()
