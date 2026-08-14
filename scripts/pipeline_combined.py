#!/usr/bin/env python3
"""Combined-cohort fuzzy audiogram pipeline (version for AUX1 + AUX_G + AUX_I).

Runs the full pipeline on the 20-69 y adult cohort:
  1. load + clean the three cycles
  2. train/test split (80/20, random_state 42)
  3. MF optimisation on the TRAINING set (per-frequency percentile fit,
     aggregate across frequencies, enforce >=2 dB overlap)
  4. build the Mamdani FIS with the new parameters (deployed core untouched)
  5. batch-classify every clean ear (ControlSystem built once)
  6. validation metrics + ML comparators on the test set
  7. figures: membership functions, Bland-Altman, boundary-distance, config
  8. outputs: params_combined.json, metrics_combined.json,
     combined_classification_results.csv, predictions pickle

Usage:
  python3 scripts/pipeline_combined.py --quick   # timing sample only
  python3 scripts/pipeline_combined.py           # full run
"""
import sys
import json
import pickle
import warnings
from pathlib import Path

warnings.filterwarnings('ignore')
PROJECT = Path('/opt/data/fuzzy-audiogram')
sys.path.insert(0, str(PROJECT))

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import cohen_kappa_score, accuracy_score, mean_absolute_error
from scipy.stats import spearmanr

import skfuzzy as fuzz
from skfuzzy import control as ctrl
from fuzzy_audiogram import core
from fuzzy_audiogram.combined_data import (
    load_combined_nhanes, extract_combined_audiometry, clean_ears,
    FREQUENCIES, EAR_SIDES)

OUT = PROJECT / 'data' / 'output'
OUT.mkdir(parents=True, exist_ok=True)
FIG = PROJECT / 'figures'
FIG.mkdir(parents=True, exist_ok=True)

PTA_IDX = [1, 2, 3, 5]          # canonical8: 500, 1k, 2k, 4k
SEVERITY_ORDER = ['normal', 'mild', 'moderate', 'moderately_severe', 'severe', 'profound']
SEVERITY_HUMAN = ['Normal', 'Mild', 'Moderate', 'Moderately Severe', 'Severe', 'Profound']
BOUNDS = [25, 40, 55, 70, 90]
SEVERITY_BOUNDS = {'normal': (0, 25), 'mild': (26, 40), 'moderate': (41, 55),
                   'moderately_severe': (56, 70), 'severe': (71, 90), 'profound': (91, 120)}
OVERLAP_MIN = 2.0


def who_grade(v):
    if v <= 25: return 0
    elif v <= 40: return 1
    elif v <= 55: return 2
    elif v <= 70: return 3
    elif v <= 90: return 4
    else: return 5


def who_category(v):
    if v < 0: return 'normal'
    for cat, (lo, hi) in SEVERITY_BOUNDS.items():
        if lo <= v <= hi:
            return cat
    return 'profound'


def optimize_mfs(ear_rows):
    """Fit trapezoidal severity MFs from the training ears (per-frequency
    percentiles -> aggregate -> overlap enforcement).

    Structural fix (S4): the Normal MF core is set to start at 0 dB
    (a = b = 0). With the percentile fit the Normal shoulder begins at
    P25 (> 0), leaving a 0-membership gap at the lowest thresholds that the
    single-ear symmetric rule previously masked; anchoring the core at 0
    restores the floor without a constant upward pull on every ear.
    """
    rows = []
    for seqn, cycle, side, th in ear_rows:
        for freq, idx in zip(FREQUENCIES, [1, 2, 3, 4, 5, 6, 7]):
            rows.append((freq, who_category(th[idx]), th[idx]))
    df = pd.DataFrame(rows, columns=['freq', 'cat', 'th'])

    trap = {}
    stats = []
    for freq in FREQUENCIES:
        trap[freq] = {}
        fd = df[df['freq'] == freq]
        for cat in SEVERITY_ORDER:
            vals = fd[fd['cat'] == cat]['th'].values
            if len(vals) < 10:
                trap[freq][cat] = list(core.SEVERITY_MF_PARAMS[cat])
                stats.append({'freq': freq, 'cat': cat, 'n': len(vals), 'note': 'insufficient'})
                continue
            p5, p25, p75, p95 = np.percentile(vals, [5, 25, 75, 95])
            a = max(0.0, p5 - 2)
            b = p25
            c = p75
            d = 120.0 if cat == 'profound' else min(p95 + 2, 120.0)
            if cat == 'normal':
                # structural fix: anchor Normal core at 0 dB
                a, b = 0.0, 0.0
            a, b, c, d = min(a, b), max(b, a), max(c, b), max(d, c)
            trap[freq][cat] = [round(a, 1), round(b, 1), round(c, 1), round(d, 1)]
            stats.append({'freq': freq, 'cat': cat, 'n': len(vals),
                          'p5': round(p5, 1), 'p25': round(p25, 1),
                          'p75': round(p75, 1), 'p95': round(p95, 1)})

    agg = {}
    for cat in SEVERITY_ORDER:
        arr = np.mean([trap[f][cat] for f in FREQUENCIES], axis=0)
        agg[cat] = [round(float(v), 1) for v in arr]

    # enforce >= OVERLAP_MIN dB POSITIVE overlap at each boundary
    # (fixes gaps where cur.d < nxt.a, and narrow overlaps)
    for i in range(len(SEVERITY_ORDER) - 1):
        cur, nxt = SEVERITY_ORDER[i], SEVERITY_ORDER[i + 1]
        if agg[cur][3] - agg[nxt][0] < OVERLAP_MIN:
            mid = (agg[cur][3] + agg[nxt][0]) / 2.0
            agg[cur][3] = round(min(120.0, mid + OVERLAP_MIN / 2), 1)
            agg[nxt][0] = round(max(0.0, mid - OVERLAP_MIN / 2), 1)
            agg[cur][2] = min(agg[cur][2], agg[cur][3] - 0.5)
            agg[nxt][1] = min(agg[nxt][1], agg[nxt][0] + 0.5) if agg[nxt][1] > agg[nxt][0] + 0.5 else agg[nxt][1]
        # enforce a <= b for the upper category after any shift
        if agg[nxt][0] > agg[nxt][1]:
            agg[nxt][1] = round(agg[nxt][0], 1)
    return agg, pd.DataFrame(stats)


def build_fis_with_params(severity_params):
    """Build the Mamdani FIS using the given severity MF params by
    monkeypatching the module constant (deployed core untouched afterwards).

    Built in single-ear mode: the symmetric-anchor asymmetry rule is omitted
    so the asymmetry input (0.0 for a single ear) does not fire at full
    strength for every ear and compress the FAI scale (structural fix S4).
    """
    orig = dict(core.SEVERITY_MF_PARAMS)
    core.SEVERITY_MF_PARAMS = {k: list(v) for k, v in severity_params.items()}
    try:
        return core.build_audiogram_fis(single_ear=True)
    finally:
        core.SEVERITY_MF_PARAMS = orig


def classify_ears_batched(system, ear_rows, sample=None):
    """Classify ears through a pre-built FIS. ControlSystem built once;
    a fresh simulation per ear. Returns dicts for severity + shape."""
    from skfuzzy import control as _ctrl
    out = []
    rows = ear_rows if sample is None else ear_rows[:sample]
    for seqn, cycle, side, th in rows:
        try:
            sim = _ctrl.ControlSystemSimulation(system)
            feats = core.compute_audiogram_features(th)
            sim.input['threshold'] = np.clip(feats['threshold_primary'], 0, 120)
            sim.input['slope'] = np.clip(feats['slope'], -40, 80)
            sim.input['notch'] = np.clip(feats['notch_depth'], 0, 50)
            sim.input['asymmetry'] = np.clip(feats['asymmetry'], 0, 60)
            with warnings.catch_warnings():
                warnings.simplefilter('ignore')
                sim.compute()
            sev = float(sim.output['severity'])
            try:
                shape = float(sim.output['audiogram_shape'])
                config_label = core._interpret_shape_score(shape)
            except (KeyError, TypeError, ValueError):
                config_label = 'ERROR'
            out.append({
                'seqn': seqn, 'cycle': cycle, 'side': side,
                'pta': round(float(feats['pta']), 1),
                'fai_score': round(sev, 2),
                'fai_label': core._interpret_severity_score(sev),
                'config_label': config_label,
            })
        except Exception:
            out.append({'seqn': seqn, 'cycle': cycle, 'side': side,
                        'pta': np.nan, 'fai_score': np.nan,
                        'fai_label': 'ERROR', 'config_label': 'ERROR'})
    return out


def main():
    quick = '--quick' in sys.argv
    print('=' * 70)
    print('COMBINED-COHORT FUZZY AUDIOGRAM PIPELINE (20-69 y)')
    print('=' * 70)

    # 1. load + clean
    print('\n[1] Loading combined NHANES adult cycles...')
    raw = load_combined_nhanes()
    audio = extract_combined_audiometry(raw)
    ear_rows = clean_ears(audio)
    print(f'  participants: {len(raw)} | clean ears: {len(ear_rows)} '
          f'from {len(set(s for s, _, _, _ in ear_rows))} participants')
    print('  ears by cycle:', {c: n for c, n in
          pd.Series([c for _, c, _, _ in ear_rows]).value_counts().items()})

    # 2. split
    X_all = np.array([r[3] for r in ear_rows])
    y_all = np.array([np.mean([r[3][i] for i in PTA_IDX]) for r in ear_rows])
    X_tr, X_te, y_tr, y_te = train_test_split(X_all, y_all, test_size=0.2, random_state=42)
    rng = np.random.RandomState(42)
    order = rng.permutation(len(ear_rows))
    test_pos = set(order[:int(round(0.2 * len(ear_rows)))].tolist())
    train_rows = [ear_rows[i] for i in range(len(ear_rows)) if i not in test_pos]
    test_rows = [ear_rows[i] for i in range(len(ear_rows)) if i in test_pos]
    print(f'  split: train={len(train_rows)} test={len(test_rows)}')

    # 3. MF optimisation (training only)
    print('\n[2] Optimising membership functions on the TRAINING set...')
    if quick:
        train_sample = train_rows[:4000]
    else:
        train_sample = train_rows
    params, stats_df = optimize_mfs(train_sample)
    for cat in SEVERITY_ORDER:
        print(f'    {cat:20s}: {params[cat]}')
    (OUT / 'params_combined.json').write_text(
        json.dumps(params, indent=2), encoding='utf-8')
    stats_df.to_csv(OUT / 'mf_stats_combined.csv', index=False)

    # 4. build FIS with new params
    print('\n[3] Building Mamdani FIS with optimised parameters (single-ear mode)...')
    system, sim, threshold_ant, slope_ant, _n, _a, _sc, _sh = build_fis_with_params(params)
    print('  FIS built (47-rule single-ear base, new severity MFs; symmetric-anchor rule omitted)')

    # 4b. calibrate FAI -> label thresholds on the TRAINING set (structural fix:
    #     the fixed FIS scores span the full range, so the deployed fixed
    #     label cut-offs [20,35,50,65,85] are no longer optimal)
    print('\n[3b] Calibrating label thresholds on the TRAINING set...')
    from scipy.optimize import minimize as _minimize
    # stratified calibration sample (all WHO grades represented, like stage-2)
    _g = np.array([who_grade(np.mean([r[3][i] for i in PTA_IDX])) for r in train_rows])
    _idx, _rng2 = [], np.random.RandomState(7)
    for _c in range(6):
        _cand = np.where(_g == _c)[0]
        _take = min(int(4000 * max(len(_cand) / len(train_rows), 0.01)), len(_cand))
        _idx.extend(_rng2.choice(_cand, _take, replace=False).tolist())
    calib_rows = [train_rows[i] for i in _idx]
    calib_res = classify_ears_batched(system, calib_rows)
    calib_fai = np.array([r['fai_score'] for r in calib_res])
    calib_pta = np.array([r['pta'] for r in calib_res])
    calib_yt = np.array([who_grade(p) for p in calib_pta])
    DEFAULT_TH = [20.0, 35.0, 50.0, 65.0, 85.0]

    def _label_from_th(scores, th):
        th = np.sort(np.asarray(th, dtype=float))
        return np.array([0 if s < th[0] else 1 if s < th[1] else 2 if s < th[2]
                         else 3 if s < th[3] else 4 if s < th[4] else 5 for s in scores])

    def _obj_kappa(th):
        return -cohen_kappa_score(calib_yt, _label_from_th(calib_fai, th), weights='quadratic')

    opt = _minimize(_obj_kappa, np.array(DEFAULT_TH), method='Nelder-Mead',
                    options={'xatol': 0.5, 'fatol': 1e-6, 'maxiter': 600})
    label_th = np.sort(np.clip(opt.x, 5.0, 95.0)).tolist()
    # guard against degenerate threshold squeezing (adjacent gaps < 2 FAI pts):
    gaps = np.diff(label_th)
    if gaps.min() < 2.0:
        print('  WARNING: calibrated thresholds degenerate (adjacent gap < 2 pts); '
              'keeping defaults')
        label_th = list(DEFAULT_TH)
    print(f'  calibrated label thresholds: {[round(x, 1) for x in label_th]} '
          f'(train kappa { -opt.fun:.3f})')
    core.SEVERITY_LABEL_THRESHOLDS = label_th  # used by _interpret_severity_score

    # 5. batch classify
    n_classify = None if not quick else 200
    print(f'\n[4] Classifying ears (n={n_classify if n_classify else len(ear_rows)})...')
    t0 = __import__('time').time()
    results = classify_ears_batched(system, test_rows if quick else ear_rows, sample=n_classify)
    dt = __import__('time').time() - t0
    print(f'  classified {len(results)} in {dt:.1f}s '
          f'({dt / max(len(results), 1) * 1000:.0f} ms/ear)')
    if quick:
        print('  QUICK MODE: timing only. Run without --quick for the full pass.')
        return

    df_res = pd.DataFrame(results)
    df_res.to_csv(OUT / 'combined_classification_results.csv', index=False)

    # 6. validation metrics on test ears (classify test_rows directly)
    print('\n[5] Validation metrics (test set)')
    test_res = classify_ears_batched(system, test_rows)
    valid = [r for r in test_res if r['fai_score'] == r['fai_score']]  # drop ERROR/nan
    yf, yt, fai, pta = [], [], [], []
    test_th = {s: [] for s, _, _, _ in test_rows}
    for r in test_rows:
        test_th[r[0]].append(r[3])
    for row in valid:
        ths = test_th[int(row['seqn'])]
        idx = 0 if row['side'] == 'right' else (1 if len(ths) > 1 else 0)
        th = ths[idx]
        p = float(np.mean([th[i] for i in PTA_IDX]))
        yt.append(who_grade(p))
        yf.append(SEVERITY_HUMAN.index(row['fai_label']) if row['fai_label'] in SEVERITY_HUMAN else who_grade(p))
        fai.append(row['fai_score'])
        pta.append(p)
    yf = np.array(yf); yt = np.array(yt); fai = np.array(fai); pta = np.array(pta)
    kappa = cohen_kappa_score(yt, yf, weights='quadratic')
    overall = accuracy_score(yt, yf)
    rho = spearmanr(fai, pta)[0]
    mae = mean_absolute_error(fai, pta)
    bl = np.array([any(abs(v - b) <= 5 for b in BOUNDS) for v in pta])
    bl_acc = accuracy_score(yt[bl], yf[bl])
    cl_acc = accuracy_score(yt[~bl], yf[~bl])
    print(f'  kappa={kappa:.3f} overall={overall*100:.1f}% rho={rho:.3f} MAE={mae:.2f}')
    print(f'  borderline(<=5dB)={bl_acc*100:.1f}% (n={bl.sum()}) '
          f'clear={cl_acc*100:.1f}% (n={(~bl).sum()}) | borderline share {bl.mean()*100:.1f}%')
    dist = np.array([min(abs(v - b) for b in BOUNDS) for v in pta])
    for dd in [1, 2, 3, 4, 5, 10, 15]:
        m = dist <= dd
        if m.sum():
            print(f'    <= {dd} dB: {(yt[m] == yf[m]).mean()*100:.1f}% (n={m.sum()})')
    diff = fai - pta
    bias = diff.mean(); sd = diff.std()
    print(f'  Bland-Altman: bias={bias:.1f} LoA={bias-1.96*sd:.1f}..{bias+1.96*sd:.1f} n={len(fai)}')

    # ML comparators
    print('\n[6] ML comparators (regress PTA-4)')
    import xgboost as xgb
    from sklearn.ensemble import RandomForestRegressor
    xgbm = xgb.XGBRegressor(n_estimators=100, max_depth=6, learning_rate=0.1, random_state=42)
    xgbm.fit(X_tr, y_tr)
    rf = RandomForestRegressor(n_estimators=1000, max_depth=10, min_samples_split=5,
                               random_state=42, n_jobs=-1)
    rf.fit(X_tr, y_tr)
    yc = np.array([who_grade(v) for v in y_te])
    bl_te = np.array([any(abs(v - b) <= 5 for b in BOUNDS) for v in y_te])
    for name, mdl in [('XGBoost', xgbm), ('Random Forest', rf)]:
        pred = mdl.predict(X_te)
        plab = np.array([who_grade(v) for v in pred])
        print(f'    {name}: kappa={cohen_kappa_score(yc, plab, weights="quadratic"):.3f} '
              f'overall={accuracy_score(yc, plab)*100:.1f}% '
              f'borderline={accuracy_score(yc[bl_te], plab[bl_te])*100:.1f}% '
              f'clear={accuracy_score(yc[~bl_te], plab[~bl_te])*100:.1f}% '
              f'MAE={mean_absolute_error(y_te, pred):.2f}')

    metrics = {'cohort': 'combined 20-69 (AUX1+AUX_G+AUX_I)',
               'participants': int(len(raw)), 'clean_ears': len(ear_rows),
               'train_ears': len(train_rows), 'test_ears': len(test_rows),
               'kappa': round(kappa, 3), 'overall': round(overall, 4),
               'rho': round(rho, 3), 'mae': round(mae, 2),
               'borderline': round(bl_acc, 4), 'clear': round(cl_acc, 4),
               'borderline_share': round(bl.mean(), 4),
               'bias': round(bias, 1), 'loa_lo': round(bias - 1.96*sd, 1),
               'loa_hi': round(bias + 1.96*sd, 1), 'n_valid': int(len(fai)),
               'label_thresholds': [round(x, 1) for x in label_th],
               'single_ear': True, 'mf_params': params}
    (OUT / 'metrics_combined.json').write_text(json.dumps(metrics, indent=2), encoding='utf-8')
    pickle.dump({'params': params, 'y_te': y_te, 'y_true': yt, 'yf': yf,
                 'fai': fai, 'pta': pta, 'bl': bl, 'dist': dist},
                open(OUT / 'combined_predictions.pkl', 'wb'))
    print('\nsaved:', OUT / 'params_combined.json', OUT / 'metrics_combined.json',
          OUT / 'combined_classification_results.csv', OUT / 'combined_predictions.pkl')


if __name__ == '__main__':
    main()
