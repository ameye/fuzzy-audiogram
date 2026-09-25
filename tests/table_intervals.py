"""Table 1 intervals and the clear-case ablation comparison.

Table 1 reports per-class sensitivity, specificity and precision. Several rows are
extreme — sensitivity of 1.000 from 12 severe ears and from 3,475 normal ears are
not equally certain — so each is reported with a Wilson score interval. Wilson is
used rather than the Wald interval because Wald collapses to zero width at p = 0
or 1, which is exactly the regime those rows occupy.

The clear-case comparison contrasts the deployed 10 dB transition floor with the
raw natural gaps of the fitted partition. Both arms must be present under
archive_corrected/; if they are, a paired bootstrap gives the interval on the
difference, since the two arms score the same ears.

Run:  python3 tests/table_intervals.py
Writes: manuscript/table_intervals.json
"""
import json
import pickle
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
CLASSES = ["Normal", "Mild", "Moderate", "Mod. severe", "Severe", "Profound"]
N_BOOT = 2000
SEED = 42


def wilson(k, n, z=1.96):
    """Wilson score interval for a binomial proportion."""
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, centre - half), min(1.0, centre + half))


def confusion(y_true, y_pred, n_classes):
    m = np.zeros((n_classes, n_classes), dtype=int)
    for t, p in zip(y_true, y_pred):
        m[int(t), int(p)] += 1
    return m


def table1(y_true, y_pred):
    m = confusion(y_true, y_pred, len(CLASSES))
    total = m.sum()
    out = {}
    for i, name in enumerate(CLASSES):
        tp = int(m[i, i])
        fn = int(m[i, :].sum() - tp)
        fp = int(m[:, i].sum() - tp)
        tn = int(total - tp - fn - fp)
        sens = (tp / (tp + fn)) if (tp + fn) else 0.0
        spec = (tn / (tn + fp)) if (tn + fp) else 0.0
        prec = (tp / (tp + fp)) if (tp + fp) else 0.0
        out[name] = {
            "n": tp + fn,
            "sensitivity": list(wilson(tp, tp + fn)),
            "specificity": list(wilson(tn, tn + fp)),
            "precision": list(wilson(tp, tp + fp)),
            "point": {"sensitivity": sens, "specificity": spec, "precision": prec},
        }
    return out


def clear_case(seed=SEED, n_boot=N_BOOT):
    """Paired bootstrap on the difference in clear-case agreement between the
    raw-gap arm and the deployed 10 dB floor arm."""
    raw = ROOT / "archive_corrected" / "raw_gap" / "predictions_participant.pkl"
    flo = ROOT / "archive_corrected" / "sweep_10" / "predictions_participant.pkl"
    if not (raw.exists() and flo.exists()):
        return None
    a = pickle.load(open(raw, "rb"))
    b = pickle.load(open(flo, "rb"))
    ya, pa = np.asarray(a["y_true"]), np.asarray(a["yf"])
    yb, pb = np.asarray(b["y_true"]), np.asarray(b["yf"])
    if not (len(ya) == len(yb) and np.array_equal(ya, yb)):
        return {"error": "arms are not scoring the same ears"}
    # a group is "clear" when its pure-form margin sits outside the ambiguous zone
    import sys as _s
    _s.path.insert(0, str(ROOT))
    from fuzzy_audiogram import core
    th = np.array(core.SEVERITY_LABEL_THRESHOLDS)

    def clear_mask(yt, yp, floor_db):
        # an ear is clear when no imprecision zone touches its reference grade
        m = np.zeros(len(yt), dtype=bool)
        for i, (t, q) in enumerate(zip(yt, yp)):
            lo = th[t - 1] if t > 0 else -np.inf
            hi = th[t] if t < len(th) else np.inf
            m[i] = (abs(float(q) - float(lo)) > floor_db) and (abs(float(q) - float(hi)) > floor_db)
        return m

    ma, mb = clear_mask(ya, pa, 0.0), clear_mask(yb, pb, 10.0)
    acc_a = float((pa[ma] == ya[ma]).mean()) if ma.any() else float("nan")
    acc_b = float((pb[mb] == yb[mb]).mean()) if mb.any() else float("nan")
    rng = np.random.RandomState(seed)
    diffs = []
    n = len(ya)
    for _ in range(n_boot):
        idx = rng.randint(0, n, n)
        ia, ib = ma[idx], mb[idx]
        if ia.any() and ib.any():
            diffs.append((pb[idx][ib] == yb[idx][ib]).mean()
                         - (pa[idx][ia] == ya[idx][ia]).mean())
    diffs = np.array(diffs)
    return {
        "n": int(n),
        "raw_gaps_pct": acc_a * 100,
        "floor10_pct": acc_b * 100,
        "difference_pp": (acc_b - acc_a) * 100,
        "ci95_pp": [float(np.percentile(diffs, 2.5) * 100),
                    float(np.percentile(diffs, 97.5) * 100)],
    }


def main():
    d = pickle.load(open(ROOT / "data/output_participant/predictions_participant.pkl", "rb"))
    y_true, y_pred = np.asarray(d["y_true"]), np.asarray(d["yf"])
    out = {"table1_wilson": table1(y_true, y_pred), "n_test": int(len(y_true))}
    cc = clear_case()
    if cc is not None:
        out["clear_case_two_point"] = cc
    dest = ROOT / "manuscript/table_intervals.json"
    dest.write_text(json.dumps(out, indent=2))
    print(f"  test ears: {len(y_true)}")
    for name, v in out["table1_wilson"].items():
        p = v["point"]
        print(f"    {name:14} n={v['n']:>5}  sens {p['sensitivity']:.3f} "
              f"({v['sensitivity'][0]:.3f}-{v['sensitivity'][1]:.3f})  "
              f"prec {p['precision']:.3f} ({v['precision'][0]:.3f}-{v['precision'][1]:.3f})")
    if cc and "error" not in cc:
        print(f"  clear-case: raw {cc['raw_gaps_pct']:.1f}% -> floor10 {cc['floor10_pct']:.1f}%  "
              f"diff {cc['difference_pp']:+.1f} pp [{cc['ci95_pp'][0]:+.1f}, {cc['ci95_pp'][1]:+.1f}]")
    elif cc:
        print(f"  clear-case: {cc['error']}")
    else:
        print("  clear-case: ablation arms not present, skipped")
    print(f"  saved: {dest}")


if __name__ == "__main__":
    main()
