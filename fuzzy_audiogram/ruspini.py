"""Ruspini-partition construction for the audiometric severity membership functions.

Background
----------
The severity trapezoids were previously fitted one category at a time
(``a = P5 - 2``, ``b = P25``, ``c = P75``, ``d = P95 + 2``). That leaves a
fixed-width transition band -- in practice exactly 2 dB -- of which both
neighbouring categories hold only *partial* membership, so the memberships do
not sum to 1 and the "fuzzy" zone is too narrow to represent the +/-5 dB
test-retest variability of pure-tone audiometry.

This module arranges the six trapezoids as a formal Ruspini partition: the
memberships of the six severity categories sum to exactly 1.0 at every point of
the 0-120 dB HL universe. No threshold is left unclassified and no region is
double-counted.

Construction
------------
The percentile-derived cores are retained (``b = P25``, ``c = P75``). Each
trapezoid's feet are then tied to its neighbours' cores rather than to its own
percentiles:

    a_i = c_{i-1}          left foot  = previous category's core end
    d_i = b_{i+1}          right foot = next category's core start

so adjacent shoulders are complementary linear ramps. Writing the descending and
ascending memberships over the shared interval [c_{i-1}, b_i],

    mu_{i-1}(x) = (d_{i-1} - x) / (d_{i-1} - c_{i-1}) = (b_i - x) / (b_i - c_{i-1})
    mu_i(x)     = (x - a_i) / (b_i - a_i)             = (x - c_{i-1}) / (b_i - c_{i-1})

which sum to exactly 1. Outside the transition band the incumbent category holds
full membership and its neighbours hold zero, so the sum is 1 there too.

The bottom category's left foot is clamped to the universe floor and the top
category's core is extended to the universe ceiling, so the partition also
covers the open ends.

Requirement
-----------
The construction is only well defined when the cores are ordered and
non-overlapping, ``c_i <= b_{i+1}``. Percentile fits on small tail categories can
violate this. ``repair=True`` (the default) resolves a violation by moving both
the incumbent core end and the neighbour's core start to their midpoint, which
preserves ordering without discarding either category. ``repair=False`` raises
instead.

Typical use
-----------
    from fuzzy_audiogram.ruspini import build_from_percentiles, verify

    params = build_from_percentiles(stats)      # stats: {cat: {'p25': .., 'p75': ..}}
    assert verify(params)['is_partition']       # sum == 1 everywhere
"""
from __future__ import annotations

from typing import Dict, Iterable, Mapping, Optional, Sequence, Tuple

__all__ = [
    "SEVERITY_ORDER",
    "UNIVERSE",
    "trapmf",
    "partition_sum",
    "build_ruspini_partition",
    "build_from_percentiles",
    "core_repairs",
    "verify",
]

# Ascending severity. Order matters: the construction ties each trapezoid to the
# previous and next entries.
SEVERITY_ORDER: Tuple[str, ...] = (
    "normal",
    "mild",
    "moderate",
    "moderately_severe",
    "severe",
    "profound",
)

UNIVERSE: Tuple[float, float] = (0.0, 120.0)

# The standard trapezoid is zero at x == a and x == d, so a partition built on
# the closed interval [0, 120] would leave both endpoints with zero total
# membership. The outer feet are therefore padded just beyond the domain so the
# endpoints are covered. 0.5 dB is far below the 5 dB audiometric step and the
# +/-5 dB test-retest variability, and thresholds are clipped to the universe
# before fuzzification, so the padded shoulders are never traversed.
OUTER_PAD = 0.5

# Tolerance for the sum-to-one check. Memberships are computed in float64 from
# parameters stored to four decimal places, so 1e-9 is comfortably tight while
# still admitting rounding in the stored parameters.
TOL = 1e-9


def trapmf(x: float, params: Sequence[float]) -> float:
    """Trapezoidal membership of ``x`` for ``[a, b, c, d]``.

    Flat-topped by default; degrades gracefully to a triangle when ``a == b`` or
    ``c == d``, and to a rectangle when both.
    """
    a, b, c, d = (float(v) for v in params)
    if x <= a or x >= d:
        return 0.0
    if b <= x <= c:
        return 1.0
    if x < b:
        return (x - a) / (b - a) if b > a else 1.0
    return (d - x) / (d - c) if d > c else 1.0


def partition_sum(
    params: Mapping[str, Sequence[float]], x: float,
    order: Sequence[str] = SEVERITY_ORDER,
) -> float:
    """Total membership held by all categories at threshold ``x``."""
    return sum(trapmf(x, params[k]) for k in order)


def _repair_cores(
    cores: Dict[str, Tuple[float, float]],
    order: Sequence[str],
) -> Tuple[Dict[str, Tuple[float, float]], list]:
    """Force ``c_i <= b_{i+1}`` for every adjacent pair.

    A violation means the percentile-fitted cores overlap. Both the incumbent's
    core end and the neighbour's core start are moved to their midpoint, which
    keeps both categories alive and preserves ordering.

    Returns the repaired cores and a list of (category, neighbour, c_i, b_next)
    describing what was changed.
    """
    adjustments = []
    for prev_key, key in zip(order, order[1:]):
        b_prev, c_prev = cores[prev_key]
        b_next, c_next = cores[key]
        if c_prev > b_next:
            mid = (c_prev + b_next) / 2.0
            adjustments.append((prev_key, key, c_prev, b_next, mid))
            # never let a core invert (c < b) as a side effect
            cores[prev_key] = (min(b_prev, mid), mid)
            cores[key] = (mid, max(c_next, mid))
    return cores, adjustments


def _enforce_min_transition(
    cores: Dict[str, Tuple[float, float]],
    order: Sequence[str],
    min_transition: float,
    floor: float,
    ceiling: float,
) -> None:
    """Widen cores in place so every core gap reaches ``min_transition`` dB.

    The Ruspini transition width equals the gap between one core's end and the
    next core's start, so a data-driven fit on sparse tail categories can leave a
    narrow band (the fixed-2 dB construction was one symptom of this). This
    widens the gap symmetrically -- moving the incumbent's core end down and the
    neighbour's core start up -- and, where one side is already pinned against
    its own core, pushes the other side further.
    """
    for _ in range(200):
        changed = False
        for i in range(len(order) - 1):
            prev_key, key = order[i], order[i + 1]
            b_prev, c_prev = cores[prev_key]
            b_next, c_next = cores[key]
            gap = b_next - c_prev
            if gap >= min_transition - 1e-9:
                continue

            need = (min_transition - gap) / 2.0
            new_c = max(b_prev, c_prev - need)
            new_b = min(c_next, b_next + need)

            # if a side hit its own core limit, make up the shortfall on the other
            shortfall = min_transition - (new_b - new_c)
            if shortfall > 1e-9:
                room_up = c_next - new_b
                take = min(shortfall, room_up)
                new_b += take
                shortfall -= take
            if shortfall > 1e-9:
                room_down = new_c - b_prev
                take = min(shortfall, room_down)
                new_c -= take

            if abs(new_c - c_prev) > 1e-12 or abs(new_b - b_next) > 1e-12:
                cores[prev_key] = (b_prev, new_c)
                cores[key] = (new_b, c_next)
                changed = True
        if not changed:
            break


def core_repairs(
    cores: Mapping[str, Sequence[float]],
    order: Sequence[str] = SEVERITY_ORDER,
) -> list:
    """Report core overlaps that ``build_ruspini_partition`` would repair.

    Each entry is ``(incumbent, neighbour, c_incumbent, b_neighbour, midpoint)``.
    """
    working = {k: (float(cores[k][0]), float(cores[k][1])) for k in order}
    _, adjustments = _repair_cores(working, order)
    return adjustments


def build_ruspini_partition(
    cores: Mapping[str, Sequence[float]],
    order: Sequence[str] = SEVERITY_ORDER,
    universe: Tuple[float, float] = UNIVERSE,
    repair: bool = True,
    min_transition: Optional[float] = None,
) -> Dict[str, list]:
    """Build sum-to-one trapezoids from per-category percentile cores.

    Parameters
    ----------
    cores
        ``{category: (P25, P75)}`` -- the core of each trapezoid, in dB HL.
    order
        Category order, ascending severity.
    universe
        ``(floor, ceiling)`` of the threshold domain, in dB HL.
    repair
        Resolve overlapping cores by splitting the difference. If False, raise
        ValueError instead.
    min_transition
        If given, widen cores so every transition band is at least this wide, in
        dB. The Ruspini transition width equals the core gap, so a data-driven
        fit can leave a band narrower than the test-retest variability the
        partition is meant to represent. ``None`` keeps the percentile cores
        untouched (the manuscript's construction).

    Returns
    -------
    ``{category: [a, b, c, d]}`` satisfying ``sum(mu) == 1`` on the universe.
    Use :func:`core_repairs` to see whether any cores had to be moved.
    """
    missing = [k for k in order if k not in cores]
    if missing:
        raise KeyError(f"cores missing for: {missing}")

    lo, hi = float(universe[0]), float(universe[1])
    working: Dict[str, Tuple[float, float]] = {}
    for k in order:
        p25, p75 = (float(v) for v in cores[k])
        if p75 < p25:
            raise ValueError(f"{k}: P75 ({p75}) < P25 ({p25})")
        working[k] = (max(p25, lo), min(p75, hi))

    if min_transition is not None:
        _enforce_min_transition(working, order, float(min_transition), lo, hi)

    working, adjustments = _repair_cores(working, order)
    if adjustments and not repair:
        detail = "; ".join(
            f"{p}/{n}: c={c:.1f} > b={b:.1f}" for p, n, c, b, _ in adjustments
        )
        raise ValueError(f"overlapping cores and repair=False -- {detail}")

    params: Dict[str, list] = {}
    for i, key in enumerate(order):
        b_i, c_i = working[key]

        if i == 0:
            # bottom trapezoid opens just below the floor, so x == lo is covered
            a_i = lo - OUTER_PAD
        else:
            a_i = working[order[i - 1]][1]  # previous category's core end

        if i == len(order) - 1:
            c_i = hi                            # top core extended to the ceiling
            d_i = hi + OUTER_PAD                # and closes just beyond it
        else:
            d_i = working[order[i + 1]][0]      # next category's core start

        # guard against a degenerate/inverted quadruple after repair
        a_i = min(a_i, b_i)
        d_i = max(d_i, c_i)

        params[key] = [round(a_i, 4), round(b_i, 4), round(c_i, 4), round(d_i, 4)]

    return params


def build_from_percentiles(
    stats: Mapping[str, Mapping[str, float]],
    order: Sequence[str] = SEVERITY_ORDER,
    universe: Tuple[float, float] = UNIVERSE,
    repair: bool = True,
) -> Dict[str, list]:
    """Convenience wrapper for the optimizer's stats layout.

    ``stats`` is ``{category: {'p25': float, 'p75': float, ...}}`` as produced by
    ``scripts/optimize_mfs.py``.
    """
    cores = {
        k: (stats[k]["p25"], stats[k]["p75"])
        for k in order
        if k in stats and stats[k].get("p25") is not None
        and stats[k].get("p75") is not None
    }
    return build_ruspini_partition(cores, order=order, universe=universe, repair=repair)


def verify(
    params: Mapping[str, Sequence[float]],
    order: Sequence[str] = SEVERITY_ORDER,
    universe: Tuple[float, float] = UNIVERSE,
    step: float = 0.1,
) -> dict:
    """Check that ``params`` is a Ruspini partition on ``universe``.

    Returns a report dict. ``is_partition`` is True only when the memberships sum
    to 1 within ``TOL`` at every evaluated point and no evaluated point is left
    with zero total membership.
    """
    lo, hi = universe
    n = int(round((hi - lo) / step)) + 1
    worst_x, worst_err, worst_sum = None, 0.0, None
    offenders = []
    uncovered = []
    for i in range(n):
        x = lo + i * step
        s = partition_sum(params, x, order=order)
        err = abs(s - 1.0)
        if s == 0.0:
            uncovered.append(round(x, 3))
        if err > worst_err:
            worst_x, worst_err, worst_sum = round(x, 3), err, s
        if err > TOL:
            offenders.append((round(x, 3), round(s, 6)))

    return {
        "is_partition": not offenders and not uncovered,
        "max_deviation": worst_err,
        "worst_point": worst_x,
        "worst_sum": worst_sum,
        "tolerance": TOL,
        "points_checked": n,
        "n_offending": len(offenders),
        "n_uncovered": len(uncovered),
        "first_offenders": offenders[:12],
        "uncovered": uncovered[:12],
        "overlaps": {
            order[i]: round(params[order[i]][3] - params[order[i + 1]][0], 4)
            for i in range(len(order) - 1)
        },
    }


def _selftest() -> int:
    """Round-trip check on the cores implied by the current deployed parameters."""
    print("  Ruspini construction self-test")
    print("  " + "-" * 58)

    cores = {
        "normal": (0.0, 16.4),
        "mild": (26.3, 35.7),
        "moderate": (42.0, 54.3),
        "moderately_severe": (57.0, 67.1),
        "severe": (72.0, 83.6),
        "profound": (91.5, 120.0),
    }
    params = build_ruspini_partition(cores)
    print("  constructed parameters:")
    for k in SEVERITY_ORDER:
        print(f"    {k:20} {params[k]}")
    adj = core_repairs(cores)
    if adj:
        print(f"  core repairs applied: {len(adj)}")

    rep = verify(params)
    print(f"\n  sum-to-one: {'PASS' if rep['is_partition'] else 'FAIL'}")
    print(f"    points checked   {rep['points_checked']}")
    print(f"    max deviation    {rep['max_deviation']:.3e} (tol {TOL:.0e})")
    print(f"    offending points {rep['n_offending']}")
    print(f"    uncovered points {rep['n_uncovered']}")
    print("\n  adjacent transition widths (dB):")
    for k, v in rep["overlaps"].items():
        print(f"    {k:20} -> next: {v:6.2f}")

    # optional widening, for the reviewer's ~10 dB request
    wide = build_ruspini_partition(cores, min_transition=10.0)
    wrep = verify(wide)
    print("\n  same cores with min_transition=10 dB:")
    for k in SEVERITY_ORDER:
        print(f"    {k:20} {wide[k]}")
    print(f"    sum-to-one: {'PASS' if wrep['is_partition'] else 'FAIL'}"
          f"   transition widths "
          + ", ".join(f"{v:.1f}" for v in wrep["overlaps"].values()))

    # the failing case the module exists to fix
    print("\n  for contrast, the previously fitted 2 dB-overlap parameters:")
    old = {
        "normal": [0.0, 0.0, 16.4, 27.8],
        "mild": [25.8, 26.3, 35.7, 43.5],
        "moderate": [41.5, 42.0, 54.3, 58.5],
        "moderately_severe": [56.5, 57.0, 67.1, 73.5],
        "severe": [71.5, 72.0, 83.6, 93.0],
        "profound": [91.0, 91.5, 106.7, 120.0],
    }
    old_rep = verify(old)
    print(f"    sum-to-one: {'PASS' if old_rep['is_partition'] else 'FAIL'}"
          f"   offending points {old_rep['n_offending']}/{old_rep['points_checked']}"
          f"   max deviation {old_rep['max_deviation']:.3f}")

    return 0 if rep["is_partition"] else 1


if __name__ == "__main__":
    raise SystemExit(_selftest())
