"""Continuous Ruspini partition constraint.

The other partition tests sample a grid. This one sweeps the decibel axis densely
and at irregular spacing, including the universe endpoints and the exact
breakpoints of every shoulder, and asserts that the memberships sum to one at
every evaluated point. Grid-only testing can miss a defect that lives between two
sample points, which is exactly where a shoulder boundary sits.

Run:  python3 tests/test_ruspini_continuous.py
"""
import sys
import warnings
from pathlib import Path

import numpy as np

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from fuzzy_audiogram.ruspini import (SEVERITY_ORDER, build_ruspini_partition,  # noqa: E402
                                     partition_sum, trapmf, verify)

TOL = 1e-9
UNIVERSE = (0.0, 120.0)
N_DENSE = 20_001

# Empirical percentile cores (P25, P75) per category, as the pipeline fits them.
# These are the deployed values, so the test exercises the real partition rather
# than a convenient fixture.
CORES = {
    "normal": (0.0, 16.4),
    "mild": (30.0, 35.4),
    "moderate": (45.4, 52.1),
    "moderately_severe": (62.1, 66.1),
    "severe": (76.1, 83.6),
    "profound": (94.8, 120.0),
}

_PARAMS = None


def _params():
    global _PARAMS
    if _PARAMS is None:
        _PARAMS = build_ruspini_partition(CORES, order=SEVERITY_ORDER, universe=UNIVERSE)
    return _PARAMS


def _sums(x):
    """Vectorised membership sum at every point of x."""
    p = _params()
    return np.array([partition_sum(p, float(v)) for v in np.asarray(x, dtype=float).ravel()])


def _breakpoints():
    p = _params()
    return np.array(sorted({float(v) for ps in p.values() for v in ps
                            if UNIVERSE[0] <= float(v) <= UNIVERSE[1]}))


def _check(x, label):
    x = np.asarray(x, dtype=float)
    dev = np.abs(_sums(x) - 1.0)
    worst = float(dev.max())
    assert worst <= TOL, f"{label}: max deviation {worst:.3e} at x={x[int(dev.argmax())]}"


def test_dense_uniform_sweep():
    """Uniform sampling across the full 0-120 dB HL range."""
    _check(np.linspace(UNIVERSE[0], UNIVERSE[1], N_DENSE), "dense uniform sweep")


def test_endpoints_are_covered():
    """The universe endpoints must be covered, not merely approached."""
    for x in (UNIVERSE[0], UNIVERSE[1]):
        s = float(partition_sum(_params(), float(x)))
        assert abs(s - 1.0) <= TOL, f"sum {s!r} at x={x}"
        assert s > 0.0, f"no membership at the endpoint x={x}"


def test_exact_shoulder_breakpoints():
    """Defects hide at breakpoints, so evaluate them exactly rather than near them."""
    _check(_breakpoints(), "exact breakpoints")


def test_irregular_spacing_and_jitter():
    """Sub-step jitter around every breakpoint, plus non-uniform coverage."""
    rng = np.random.RandomState(0)
    parts = [rng.uniform(UNIVERSE[0], UNIVERSE[1], 2_000)]
    for b in _breakpoints():
        parts.append(b + rng.uniform(-0.01, 0.01, 100))
    x = np.clip(np.concatenate(parts), UNIVERSE[0], UNIVERSE[1])
    _check(x, "irregular spacing and jitter")


def test_no_uncovered_point():
    """Memberships sum to one everywhere, so none can be zero anywhere."""
    x = np.linspace(UNIVERSE[0], UNIVERSE[1], N_DENSE)
    assert _sums(x).min() > 0.0, "an uncovered point exists in 0-120 dB HL"


def test_verify_reports_a_partition():
    rep = verify(_params(), order=SEVERITY_ORDER, universe=UNIVERSE)
    assert rep["is_partition"], rep
    assert rep["max_deviation"] <= TOL, rep
    assert rep["n_offending"] == 0, rep
    assert rep["n_uncovered"] == 0, rep


def test_trapmf_primitive():
    """The partition is built from trapezoids, so the primitive must behave."""
    assert trapmf(5.0, [0, 2, 8, 10]) == 1.0
    assert abs(trapmf(1.0, [0, 2, 8, 10]) - 0.5) < 1e-12
    assert trapmf(-1.0, [0, 2, 8, 10]) == 0.0


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"  PASS  {t.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"  FAIL  {t.__name__}: {e}")
    print(f"\n  {len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)
