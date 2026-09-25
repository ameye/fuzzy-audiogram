"""Transition-floor sweep statistics on the corrected cohort.

Recomputes the 4-16 dB sweep from the arms archived under archive_corrected/ and
bootstraps the paired difference against the deployed 10 dB floor. The arms must
share a split for a paired comparison to mean anything, which is why the split is
keyed on SEQN rather than on position in the participant list.

Mean absolute error is |FAI - PTA-4| in decibels; the FAI is defuzzified onto a
0-100 index, so it is compared against PTA-4 directly on that scale.

Run:  python3 tests/sweep_corrected_stats.py
Writes: data/output_participant/transition_sweep.json
"""
import json
import pickle
from pathlib import Path

import numpy as np
from sklearn.metrics import accuracy_score, cohen_kappa_score, mean_absolute_error

ROOT = Path(__file__).resolve().parent.parent
FLOORS = (4, 6, 8, 10, 12, 14, 16)
DEPLOYED = 10
N_BOOT = 2000
SEED = 42


def load(floor):
    p = ROOT / f"archive_corrected/sweep_{floor}/predictions_participant.pkl"
    if not p.exists():
        return None
    d = pickle.load(open(p, "rb"))
    return {"y": np.asarray(d["y_true"]), "yp": np.asarray(d["yf"]),
            "pta": np.asarray(d["y_te"]), "fai": np.asarray(d["fai"]),
            "bl": np.asarray(d["bl"], dtype=bool)}


def oneline(a):
    return (cohen_kappa_score(a["y"], a["yp"], weights="quadratic"),
            mean_absolute_error(a["pta"], a["fai"]),
            accuracy_score(a["y"], a["yp"]) * 100,
            accuracy_score(a["y"][a["bl"]], a["yp"][a["bl"]]) * 100 if a["bl"].any() else np.nan,
            accuracy_score(a["y"][~a["bl"]], a["yp"][~a["bl"]]) * 100 if (~a["bl"]).any() else np.nan)


def main():
    arms = {w: load(w) for w in FLOORS}
    if not any(a is not None for a in arms.values()):
        print("  no sweep arms found under archive_corrected/")
        return
    base = arms[DEPLOYED] if arms.get(DEPLOYED) is not None else next(a for a in arms.values() if a is not None)
    n = len(base["y"])
    rng = np.random.RandomState(SEED)
    boots = [rng.randint(0, n, n) for _ in range(N_BOOT)]
    k_base_boot = np.array([cohen_kappa_score(base["y"][i], base["yp"][i], weights="quadratic")
                            for i in boots])

    out = {"deployed_floor": DEPLOYED, "n_test": int(n), "arms": {}}
    print(f"  n = {n:,} test ears per arm\n")
    print(f"  {'floor':>6} {'kappa':>8} {'delta vs 10 dB':>26} {'MAE dB':>8} {'overall':>9} {'border':>8}")
    for w in FLOORS:
        a = arms.get(w)
        if a is None:
            print(f"  {w:>6}   missing")
            continue
        k, mae, ov, bord, cl = oneline(a)
        kb = np.array([cohen_kappa_score(a["y"][i], a["yp"][i], weights="quadratic") for i in boots])
        d = kb - k_base_boot
        lo, hi = np.percentile(d, 2.5), np.percentile(d, 97.5)
        differs = bool(lo > 0 or hi < 0)
        out["arms"][str(w)] = {"kappa": float(k), "mae_db": float(mae), "overall_pct": float(ov),
                               "borderline_pct": float(bord), "clear_pct": float(cl),
                               "delta_vs_deployed": float(k) - float(oneline(base)[0]),
                               "delta_ci95": [float(lo), float(hi)], "differs_from_deployed": differs}
        print(f"  {w:>6} {k:>8.4f}   {lo:+.4f} to {hi:+.4f}{' *' if differs else '  '} "
              f"{mae:>8.2f} {ov:>8.1f}% {bord:>7.1f}%")

    ks = {w: out["arms"][str(w)]["kappa"] for w in FLOORS if str(w) in out["arms"]}
    pk = max(ks, key=ks.get)
    plateau = [w for w in FLOORS if str(w) in ks and abs(ks[w] - ks[pk]) <= 0.005]
    out["peak_floor"] = pk
    out["plateau_within_0.005"] = plateau
    print(f"\n  peak: {pk} dB at kappa {ks[pk]:.4f}")
    print(f"  within 0.005 of peak: {plateau}")
    print(f"  deployed {DEPLOYED} dB delta vs peak: "
          f"{out['arms'][str(DEPLOYED)]['delta_vs_deployed']:+.4f}" if pk != DEPLOYED
          else f"  deployed {DEPLOYED} dB IS the peak")
    for w in FLOORS:
        e = out["arms"].get(str(w))
        if e and e["differs_from_deployed"]:
            print(f"    {w} dB differs from deployed: {e['delta_ci95'][0]:+.4f} to {e['delta_ci95'][1]:+.4f}")

    p = ROOT / "data/output_participant/transition_sweep.json"
    p.write_text(json.dumps(out, indent=2))
    print(f"\n  saved: {p}")


if __name__ == "__main__":
    main()
