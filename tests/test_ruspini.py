"""Tests for the Ruspini-partition construction.

Run with:  python -m pytest tests/test_ruspini.py -q
       or:  python tests/test_ruspini.py
"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fuzzy_audiogram.ruspini import (  # noqa: E402
    OUTER_PAD,
    SEVERITY_ORDER,
    TOL,
    build_from_percentiles,
    build_ruspini_partition,
    core_repairs,
    partition_sum,
    trapmf,
    verify,
)

# Cores implied by the parameters the previous pipeline wrote to
# data/output_participant/metrics_participant.json.
CORES = {
    "normal": (0.0, 16.4),
    "mild": (26.3, 35.7),
    "moderate": (42.0, 54.3),
    "moderately_severe": (57.0, 67.1),
    "severe": (72.0, 83.6),
    "profound": (91.5, 120.0),
}

# The parameters that pipeline actually wrote, for the regression comparison.
LEGACY = {
    "normal": [0.0, 0.0, 16.4, 27.8],
    "mild": [25.8, 26.3, 35.7, 43.5],
    "moderate": [41.5, 42.0, 54.3, 58.5],
    "moderately_severe": [56.5, 57.0, 67.1, 73.5],
    "severe": [71.5, 72.0, 83.6, 93.0],
    "profound": [91.0, 91.5, 106.7, 120.0],
}


def approx(a, b, tol=1e-9):
    return abs(a - b) <= tol


def test_trapmf_basics():
    # flat top
    assert trapmf(5, [0, 2, 8, 10]) == 1.0
    # shoulders
    assert approx(trapmf(1, [0, 2, 8, 10]), 0.5)
    assert approx(trapmf(9, [0, 2, 8, 10]), 0.5)
    # standard trapezoid is zero at and beyond the feet
    assert trapmf(0, [0, 2, 8, 10]) == 0.0
    assert trapmf(10, [0, 2, 8, 10]) == 0.0
    assert trapmf(-1, [0, 2, 8, 10]) == 0.0
    # degenerate: a == b makes the ascending shoulder instantaneous, so the
    # plateau starts at the floor; only the descending shoulder is a ramp
    assert approx(trapmf(1, [0, 0, 2, 4]), 1.0)
    assert approx(trapmf(3, [0, 0, 2, 4]), 0.5)
    # degenerate: rectangle (a == b and c == d)
    assert trapmf(1, [0, 0, 4, 4]) == 1.0


def test_partition_sums_to_one():
    params = build_ruspini_partition(CORES)
    rep = verify(params)
    assert rep["is_partition"], rep
    assert rep["n_offending"] == 0
    assert rep["n_uncovered"] == 0
    assert rep["max_deviation"] <= TOL


def test_every_point_covered_including_endpoints():
    params = build_ruspini_partition(CORES)
    for x in (0.0, 0.1, 25.0, 60.0, 119.9, 120.0):
        assert partition_sum(params, x) > 0.0, f"no membership at {x}"


def test_adjacent_shoulders_are_complementary():
    """In each transition band the two neighbours must sum to exactly 1."""
    params = build_ruspini_partition(CORES)
    for i in range(len(SEVERITY_ORDER) - 1):
        lo_key, hi_key = SEVERITY_ORDER[i], SEVERITY_ORDER[i + 1]
        start = params[lo_key][2]          # incumbent core end
        end = params[hi_key][1]            # neighbour core start
        for k in range(11):
            x = start + (end - start) * k / 10.0
            total = trapmf(x, params[lo_key]) + trapmf(x, params[hi_key])
            assert approx(total, 1.0, 1e-9), (
                f"{lo_key}/{hi_key} at {x}: {total}"
            )


def test_legacy_parameters_are_not_a_partition():
    """Regression guard: the old fixed-2 dB parameters must fail the check."""
    rep = verify(LEGACY)
    assert not rep["is_partition"]
    assert rep["n_offending"] > 100          # it fails badly, not marginally


def test_transition_bands_are_wider_than_the_old_two_dB():
    params = build_ruspini_partition(CORES)
    rep = verify(params)
    widths = list(rep["overlaps"].values())
    assert all(w > 2.0 for w in widths), widths
    # and the widest is close to the test-retest range the partition represents
    assert max(widths) >= 5.0


def test_min_transition_enforced():
    params = build_ruspini_partition(CORES, min_transition=10.0)
    rep = verify(params)
    assert rep["is_partition"], rep
    for w in rep["overlaps"].values():
        assert w >= 10.0 - 1e-6, rep["overlaps"]


def test_min_transition_smaller_than_natural_is_a_noop():
    natural = build_ruspini_partition(CORES)
    forced = build_ruspini_partition(CORES, min_transition=1.0)
    assert natural == forced


def test_ordering_and_monotonicity():
    params = build_ruspini_partition(CORES)
    prev_d = -math.inf
    for k in SEVERITY_ORDER:
        a, b, c, d = params[k]
        assert a <= b <= c <= d, f"{k}: {params[k]}"
        assert b >= prev_d - 1e-9 or k == SEVERITY_ORDER[0]
        prev_d = d


def test_outer_feet_padded_beyond_universe():
    params = build_ruspini_partition(CORES)
    assert approx(params[SEVERITY_ORDER[0]][0], -OUTER_PAD)
    assert approx(params[SEVERITY_ORDER[-1]][3], 120.0 + OUTER_PAD)


def test_overlapping_cores_repaired():
    bad = dict(CORES)
    bad["mild"] = (10.0, 30.0)          # core start well inside normal's core
    params = build_ruspini_partition(bad, repair=True)
    assert verify(params)["is_partition"]
    assert core_repairs(bad)             # something was moved


def test_overlapping_cores_raise_when_repair_disabled():
    bad = dict(CORES)
    bad["mild"] = (10.0, 30.0)
    try:
        build_ruspini_partition(bad, repair=False)
    except ValueError:
        return
    raise AssertionError("expected ValueError for overlapping cores")


def test_inverted_core_rejected():
    bad = dict(CORES)
    bad["mild"] = (40.0, 20.0)
    try:
        build_ruspini_partition(bad)
    except ValueError:
        return
    raise AssertionError("expected ValueError for P75 < P25")


def test_missing_category_rejected():
    bad = {k: v for k, v in CORES.items() if k != "mild"}
    try:
        build_ruspini_partition(bad)
    except KeyError:
        return
    raise AssertionError("expected KeyError for a missing category")


def test_build_from_percentiles():
    stats = {k: {"p25": v[0], "p75": v[1]} for k, v in CORES.items()}
    params = build_from_percentiles(stats)
    assert verify(params)["is_partition"]
    assert set(params) == set(SEVERITY_ORDER)


def test_verify_reports_are_comparable():
    """The report must distinguish a real partition from the legacy set."""
    good = verify(build_ruspini_partition(CORES))
    bad = verify(LEGACY)
    assert good["max_deviation"] < bad["max_deviation"]
    assert good["n_offending"] < bad["n_offending"]


if __name__ == "__main__":
    tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_")]
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"  PASS  {name}")
        except AssertionError as e:
            failed += 1
            print(f"  FAIL  {name}: {e}")
        except Exception as e:                       # noqa: BLE001
            failed += 1
            print(f"  ERROR {name}: {type(e).__name__}: {e}")
    print(f"\n  {len(tests) - failed}/{len(tests)} passed")
    raise SystemExit(1 if failed else 0)
