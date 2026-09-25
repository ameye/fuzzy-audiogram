#!/usr/bin/env python3
"""Build the WHO 2021 arm as a like-for-like comparison.

scripts/pipeline_who2021.py predates the Ruspini work and carries both defects
that were fixed in the deployed 6-grade pipeline:

  1. optimize_mfs used a = P5 - 2 / d = P95 + 2 with a 2 dB overlap floor, which
     produces gaps where no category holds membership rather than a partition.
  2. the label calibration drew a class-balanced sample and discarded its own
     optimum via `if gaps.min() < 2.0`.

Comparing the 2021 schema through that code against the Ruspini 6-grade arm would
confound the schema with the construction. This script writes
scripts/pipeline_who2021_ruspini.py with both fixed, so the arms differ only in
the classification schema.

Run:  python3 scripts/make_who2021_ruspini.py
"""
import re, sys
from pathlib import Path

SRC = Path("/opt/data/fuzzy-audiogram/scripts/pipeline_who2021.py")
DST = Path("/opt/data/fuzzy-audiogram/scripts/pipeline_who2021_ruspini.py")

src = SRC.read_text(encoding="utf-8")

# ---------------------------------------------------------------- 1. imports
IMPORT_ANCHOR = "from fuzzy_audiogram import core"
assert IMPORT_ANCHOR in src, "import anchor not found"
src = src.replace(
    IMPORT_ANCHOR,
    "from fuzzy_audiogram import core\n"
    "from fuzzy_audiogram.ruspini import build_ruspini_partition, verify\n"
    "\n"
    "# Minimum transition width, matching the deployed 6-grade arm so the two\n"
    "# differ only in the classification schema.\n"
    "MIN_TRANSITION_DB = float(os.environ.get('FA_MIN_TRANSITION', '10.0'))",
    1)

if "import os" not in src.split("\n")[0:40][0] and "\nimport os" not in src:
    src = src.replace("import sys, json, pickle, warnings",
                      "import sys, json, os, pickle, warnings", 1)

# ---------------------------------------------------------------- 2. optimize_mfs
start = src.index("def optimize_mfs(ear_rows):")
end = src.index("# ---- 7-category severity output MF placement", start)
old = src[start:end]

new_opt = '''def optimize_mfs(ear_rows, min_transition=MIN_TRANSITION_DB):
    """Fit severity cores on the training set, then arrange them as a Ruspini
    partition.

    Two stages, matching scripts/pipeline_participant.py. The previous version
    averaged all four trapezoid parameters across frequencies, which silently
    preserved the 2 dB feet and produced gaps between adjacent categories rather
    than a partition. Aligning the construction means the WHO 2021 arm differs
    from the deployed arm only in its classification schema.
    """
    rows = []
    for seqn, cycle, side, th in ear_rows:
        for freq, idx in zip(FREQUENCIES, [1, 2, 3, 4, 5, 6, 7]):
            rows.append((freq, who_category(th[idx]), th[idx]))
    df = pd.DataFrame(rows, columns=['freq', 'cat', 'th'])

    # ---- stage 1: percentile cores, per frequency, averaged as cores ----
    cores_by_freq = {}
    for freq in FREQUENCIES:
        fd = df[df['freq'] == freq]
        cores_by_freq[freq] = {}
        for cat in SEVERITY_ORDER:
            vals = fd[fd['cat'] == cat]['th'].values
            if len(vals) < 10:
                p = _default_params(cat)
                p25, p75 = float(p[1]), float(p[2])
            else:
                p25, p75 = (float(x) for x in np.percentile(vals, [25, 75]))
            cores_by_freq[freq][cat] = (p25, p75)

    cores = {}
    for cat in SEVERITY_ORDER:
        p25 = float(np.mean([cores_by_freq[f][cat][0] for f in FREQUENCIES]))
        p75 = float(np.mean([cores_by_freq[f][cat][1] for f in FREQUENCIES]))
        if cat == 'normal':
            p25 = 0.0
        if p75 < p25:
            p75 = p25
        cores[cat] = (p25, p75)

    # ---- stage 2: Ruspini partition over the seven categories ----
    params = build_ruspini_partition(cores, order=SEVERITY_ORDER,
                                     min_transition=min_transition)
    agg = {cat: [round(float(v), 1) for v in params[cat]]
           for cat in SEVERITY_ORDER}
    report = verify(agg, order=SEVERITY_ORDER)
    if not report['is_partition']:
        raise RuntimeError(
            'Ruspini construction failed for the WHO 2021 schema after '
            f"rounding: {report['n_offending']} offending points, "
            f"max deviation {report['max_deviation']:.3e}")
    return agg


'''
src = src[:start] + new_opt + src[end:]

# ---------------------------------------------------------------- 3. calibration
cal_start = src.index("_idx, _rng2 = [], np.random.RandomState(7)")
# anchor on the leading indentation too, or the remainder starts mid-line and
# loses its 4-space indent, breaking the block structure
cal_end = src.index("    print(f'\\n[4] Classifying test ears with WHO 2021 FIS", cal_start)
old_cal = src[cal_start:cal_end]

new_cal = '''    # Population-representative draw rather than a class-balanced one: kappa is a
    # population measure dominated by the normal majority, so a balanced sample
    # optimises the wrong target. Rare classes get a floor, not an inflation.
    _rng2 = np.random.RandomState(7)
    _n_calib = min(5000, len(train_rows))
    _idx = _rng2.choice(len(train_rows), _n_calib, replace=False).tolist()
    _rare = [i for i, g in enumerate(_g) if g >= 4]
    if _rare:
        _extra = _rng2.choice(_rare, min(300, len(_rare)), replace=False).tolist()
        _idx = sorted(set(_idx) | set(_extra))
    calib_rows = [train_rows[i] for i in _idx]
    calib_res = classify_ears_batched(system, calib_rows, lambda s: interpret_2021(s, [20, 35, 50, 65, 80, 95]))
    calib_fai = np.array([r['fai_score'] for r in calib_res])
    calib_pta = np.array([r['pta'] for r in calib_res])
    calib_yt = np.array([who_grade(p) for p in calib_pta])
    DEFAULT_TH = [20.0, 35.0, 50.0, 65.0, 80.0, 95.0]

    def _label_from_th(scores, th):
        th = np.sort(np.asarray(th, dtype=float))
        return np.array([0 if s < th[0] else 1 if s < th[1] else 2 if s < th[2]
                         else 3 if s < th[3] else 4 if s < th[4] else 5 if s < th[5]
                         else 6 for s in scores])

    def _obj_kappa(th):
        return -cohen_kappa_score(calib_yt, _label_from_th(calib_fai, th), weights='quadratic')

    # Multi-start with a 1 dB floor. The previous single run from the defaults
    # was discarded whenever any gap came out under 2.0 dB, which silently
    # reverted to the schema defaults and cost kappa.
    _best = None
    for _s in range(12):
        _x0 = np.array(DEFAULT_TH) if _s == 0 else DEFAULT_TH + np.random.RandomState(_s).normal(0, 8, 6)
        _o = _minimize(_obj_kappa, np.sort(np.clip(_x0, 5.0, 95.0)),
                       method='Nelder-Mead',
                       options={'xatol': 0.25, 'fatol': 1e-7, 'maxiter': 1500})
        _th = np.sort(np.clip(_o.x, 5.0, 95.0))
        if np.diff(_th).min() < 1.0:
            continue
        if _best is None or _o.fun < _best[0]:
            _best = (_o.fun, _th)

    if _best is None:
        print('  WARNING: no non-degenerate optimum; keeping WHO 2021 defaults')
        label_th = list(DEFAULT_TH)
    else:
        label_th = [float(x) for x in _best[1]]
    print(f'  calibrated label thresholds: {[round(x, 1) for x in label_th]}'
          f' (train kappa {(-_best[0] if _best else -_obj_kappa(DEFAULT_TH)):.3f})')

'''
src = src[:cal_start] + new_cal + src[cal_end:]

# ---------------------------------------------------------------- 4. header + output dir
src = src.replace(
    'Outputs: data/output_who2021/',
    'Outputs: data/output_who2021_ruspini/', 1)
src = src.replace("'output_who2021'", "'output_who2021_ruspini'")
src = src.replace('"output_who2021"', '"output_who2021_ruspini"')
src = src.replace("data/output_who2021/", "data/output_who2021_ruspini/")

dst_text = src

# verify the edits actually landed before writing
checks = [
    ("partition construction", "build_ruspini_partition(cores, order=SEVERITY_ORDER"),
    ("min transition", "MIN_TRANSITION_DB"),
    ("population sample", "_n_calib = min(5000, len(train_rows))"),
    ("1 dB floor", "np.diff(_th).min() < 1.0"),
    ("no 2 dB guard", "gaps.min() < 2.0"),
    ("no p5-2 feet", "a = max(0.0, p5 - 2)"),
]
ok = True
for label, probe in checks:
    present = probe in dst_text
    want = label != "no 2 dB guard" and label != "no p5-2 feet"
    good = present if want else not present
    if not good:
        ok = False
    print(f"  {'OK  ' if good else 'FAIL'}  {label}"
          f"{'' if want else ' (must be absent)'}")
if not ok:
    print("  refusing to write: a replacement did not land")
    sys.exit(1)

DST.write_text(dst_text, encoding="utf-8")
print(f"\n  wrote {DST.name} ({len(dst_text):,} chars)")
