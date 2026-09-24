#!/usr/bin/env python3
"""End-to-end check of the pipeline's optimize_mfs with the Ruspini construction.

The real NHANES files are absent (lost with /opt/data), so this drives the
function with synthetic audiograms spanning all six severity categories and
asserts the returned parameters form a partition.
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from fuzzy_audiogram.ruspini import verify, partition_sum, SEVERITY_ORDER, trapmf  # noqa: E402
import pipeline_participant as pp  # noqa: E402


def synthetic_ears(n_per_category=400, seed=11):
    """Build (seqn, cycle, side, canonical8) rows spanning all six categories."""
    rng = np.random.RandomState(seed)
    # rough PTA-4 band for each category, in dB HL
    centres = {
        "normal": 12, "mild": 32, "moderate": 48,
        "moderately_severe": 62, "severe": 80, "profound": 100,
    }
    rows, seqn = [], 100000
    for cat in SEVERITY_ORDER:
        c = centres[cat]
        for _ in range(n_per_category):
            # gentle slope so the configuration rules have something to see
            slope = rng.uniform(-0.5, 0.5)
            values = [c + slope * (f - 1000) / 1000.0 + rng.normal(0, 3)
                      for f in range(7)]
            values = [float(np.clip(v, -10, 120)) for v in values]
            th = [values[0]] + values          # canonical8
            rows.append((seqn, "2011-2012", rng.choice(["right", "left"]), th))
            seqn += 1
    return rows


def main() -> int:
    ears = synthetic_ears()
    print(f"  synthetic ears: {len(ears):,}")

    params = pp.optimize_mfs(ears)
    print("\n  optimized parameters (Ruspini, min_transition=10 dB):")
    for cat in SEVERITY_ORDER:
        print(f"    {cat:20} {params[cat]}")

    rep = verify(params)
    print(f"\n  partition property : {'PASS' if rep['is_partition'] else 'FAIL'}")
    print(f"    points checked   {rep['points_checked']}")
    print(f"    max deviation    {rep['max_deviation']:.3e}")
    print(f"    offending points {rep['n_offending']}")
    print(f"    uncovered points {rep['n_uncovered']}")
    print("    transition widths "
          + ", ".join(f"{v:.1f}" for v in rep["overlaps"].values()))

    # explicit spot checks the reviewer would make
    print("\n  spot checks:")
    for db in (0, 25, 26, 40, 55, 70, 90, 120):
        s = partition_sum(params, db)
        members = {k: round(trapmf(db, params[k]), 3) for k in SEVERITY_ORDER}
        members = {k: v for k, v in members.items() if v > 0}
        print(f"    {db:4} dB  sum={s:.6f}  {members}")

    # the old failure mode, for contrast
    legacy = pp.core.SEVERITY_MF_PARAMS
    lrep = verify(legacy)
    print(f"\n  deployed core.py params: partition "
          f"{'PASS' if lrep['is_partition'] else 'FAIL'}"
          f"  ({lrep['n_offending']}/{lrep['points_checked']} points fail)")

    return 0 if rep["is_partition"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
