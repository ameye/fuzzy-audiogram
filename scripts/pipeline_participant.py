#!/usr/bin/env python3
"""Participant-level split re-run of the combined-cohort pipeline.

Fixes the ear-level split (88.3% of test participants also in training) by
splitting at the PARTICIPANT level: all ears of a participant go to one side.
Everything else identical to pipeline_combined.py (MF opt on train, label-threshold
calibration on train, batched classification, validation, ML comparators).
Outputs to data/output_participant/.
"""
import sys, json, pickle, warnings
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
    FREQUENCIES)

OUT = PROJECT / 'data' / 'output_participant'
OUT.mkdir(parents=True, exist_ok=True)

PTA_IDX = [1, 2, 3, 5]
SEVERITY_ORDER = ['normal', 'mild', 'moderate', 'moderately_severe', 'severe', 'profound']
SEVERITY_HUMAN = ['Normal', 'Mild', 'Moderate', 'Moderately Severe', 'Severe', 'Profound']
SEVERITY_BOUNDS = {'normal': (0, 25), 'mild': (26, 40), 'moderate': (41, 55),
                   'moderately_severe': (56, 70), 'severe': (71, 90), 'profound': (91, 120)}
BOUNDS = [25, 40, 55, 70, 90]
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
    rows = []
    for seqn, cycle, side, th in ear_rows:
        for freq, idx in zip(FREQUENCIES, [1, 2, 3, 4, 5, 6, 7]):
            rows.append((freq, who_category(th[idx]), th[idx]))
    df = pd.DataFrame(rows, columns=['freq', 'cat', 'th'])
    trap = {}
    for freq in FREQUENCIES:
        trap[freq] = {}
        fd = df[df['freq'] == freq]
        for cat in SEVERITY_ORDER:
            vals = fd[fd['cat'] == cat]['th'].values
            if len(vals) < 10:
                trap[freq][cat] = list(core.SEVERITY_MF_PARAMS[cat]); continue
            p5, p25, p75, p95 = np.percentile(vals, [5, 25, 75, 95])
            a = max(0.0, p5 - 2); b = p25; c = p75
            d = 120.0 if cat == 'profound' else min(p95 + 2, 120.0)
            if cat == 'normal': a, b = 0.0, 0.0
            a, b, c, d = min(a, b), max(b, a), max(c, b), max(d, c)
            trap[freq][cat] = [round(a, 1), round(b, 1), round(c, 1), round(d, 1)]
    agg = {}
    for cat in SEVERITY_ORDER:
        arr = np.mean([trap[f][cat] for f in FREQUENCIES], axis=0)
        agg[cat] = [round(float(v), 1) for v in arr]
    for i in range(len(SEVERITY_ORDER) - 1):
        cur, nxt = SEVERITY_ORDER[i], SEVERITY_ORDER[i + 1]
        if agg[cur][3] - agg[nxt][0] < OVERLAP_MIN:
            mid = (agg[cur][3] + agg[nxt][0]) / 2.0
            agg[cur][3] = round(min(120.0, mid + OVERLAP_MIN / 2), 1)
            agg[nxt][0] = round(max(0.0, mid - OVERLAP_MIN / 2), 1)
            agg[cur][2] = min(agg[cur][2], agg[cur][3] - 0.5)
            agg[nxt][1] = min(agg[nxt][1], agg[nxt][0] + 0.5) if agg[nxt][1] > agg[nxt][0] + 0.5 else agg[nxt][1]
        if agg[nxt][0] > agg[nxt][1]:
            agg[nxt][1] = round(agg[nxt][0], 1)
    return agg


def build_fis_with_params(severity_params):
    orig = dict(core.SEVERITY_MF_PARAMS)
    core.SEVERITY_MF_PARAMS = {k: list(v) for k, v in severity_params.items()}
    try:
        return core.build_audiogram_fis(single_ear=True)
    finally:
        core.SEVERITY_MF_PARAMS = orig


def classify_ears_batched(system, ear_rows):
    from skfuzzy import control as _ctrl
    out = []
    for seqn, cycle, side, th in ear_rows:
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
            out.append({'seqn': seqn, 'cycle': cycle, 'side': side,
                        'pta': round(float(feats['pta']), 1),
                        'fai_score': round(sev, 2),
                        'fai_label': core._interpret_severity_score(sev),
                        'config_label': config_label})
        except Exception:
            out.append({'seqn': seqn, 'cycle': cycle, 'side': side,
                        'pta': np.nan, 'fai_score': np.nan,
                        'fai_label': 'ERROR', 'config_label': 'ERROR'})
    return out


def main():
    print('=' * 70)
    print('COMBINED-COHORT PIPELINE — PARTICIPANT-LEVEL SPLIT (20-69 y)')
    print('=' * 70)

    print('\n[1] Loading combined NHANES adult cycles...')
    raw = load_combined_nhanes()
    audio = extract_combined_audiometry(raw)
    ear_rows = clean_ears(audio)
    print(f'  participants: {len(raw)} | clean ears: {len(ear_rows)} '
          f'from {len(set(s for s, _, _, _ in ear_rows))} participants')

    # participant-level split: all ears of one participant stay together
    print('\n[1b] Participant-level 80/20 split (random_state 42)...')
    participants = sorted(set(s for s, _, _, _ in ear_rows))
    rng = np.random.RandomState(42)
    perm = rng.permutation(len(participants))
    n_test_ppl = int(round(0.2 * len(participants)))
    test_ppl = set(participants[i] for i in perm[:n_test_ppl])
    train_rows = [r for r in ear_rows if r[0] not in test_ppl]
    test_rows = [r for r in ear_rows if r[0] in test_ppl]
    print(f'  train: {len(train_rows):,} ears / {len(set(s for s,_,_,_ in train_rows)):,} participants')
    print(f'  test : {len(test_rows):,} ears / {len(test_ppl):,} participants')
    assert not (set(s for s,_,_,_ in train_rows) & test_ppl), 'leakage!'

    X_all = np.array([r[3] for r in ear_rows])
    y_all = np.array([np.mean([r[3][i] for i in PTA_IDX]) for r in ear_rows])
    X_tr, X_te, y_tr, y_te = train_test_split(X_all, y_all, test_size=0.2, random_state=42)
    tr_mask = np.array([r[0] not in test_ppl for r in ear_rows])
    te_mask = ~tr_mask
    X_tr, y_tr = X_all[tr_mask], y_all[tr_mask]
    X_te, y_te = X_all[te_mask], y_all[te_mask]

    print('\n[2] Optimising membership functions on the TRAINING set...')
    params = optimize_mfs(train_rows)
    for cat in SEVERITY_ORDER:
        print(f'    {cat:20s}: {params[cat]}')
    (OUT / 'params_participant.json').write_text(json.dumps(params, indent=2), encoding='utf-8')

    print('\n[3] Building Mamdani FIS (single-ear mode)...')
    system, sim, *_ = build_fis_with_params(params)
    print('  FIS built (47-rule single-ear base)')

    print('\n[3b] Calibrating label thresholds on the TRAINING set...')
    from scipy.optimize import minimize as _minimize
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
    gaps = np.diff(label_th)
    if gaps.min() < 2.0:
        print('  WARNING: calibrated thresholds degenerate; keeping defaults')
        label_th = list(DEFAULT_TH)
    print(f'  calibrated label thresholds: {[round(x, 1) for x in label_th]} (train kappa {-opt.fun:.3f})')
    core.SEVERITY_LABEL_THRESHOLDS = label_th

    print(f'\n[4] Classifying test ears (n={len(test_rows)})...')
    import time
    t0 = time.time()
    test_res = classify_ears_batched(system, test_rows)
    dt = time.time() - t0
    print(f'  classified {len(test_res)} in {dt:.1f}s ({dt / len(test_res) * 1000:.0f} ms/ear)')

    print('\n[5] Validation metrics (test set)')
    valid = [r for r in test_res if r['fai_score'] == r['fai_score']]
    yf, yt, fai, pta = [], [], [], []
    test_th = {s: [] for s, _, _, _ in test_rows}
    for r in test_rows: test_th[r[0]].append(r[3])
    for row in valid:
        ths = test_th[int(row['seqn'])]
        idx = 0 if row['side'] == 'right' else (1 if len(ths) > 1 else 0)
        th = ths[idx]
        p = float(np.mean([th[i] for i in PTA_IDX]))
        yt.append(who_grade(p))
        yf.append(SEVERITY_HUMAN.index(row['fai_label']) if row['fai_label'] in SEVERITY_HUMAN else who_grade(p))
        fai.append(row['fai_score']); pta.append(p)
    yf = np.array(yf); yt = np.array(yt); fai = np.array(fai); pta = np.array(pta)
    kappa = cohen_kappa_score(yt, yf, weights='quadratic')
    overall = accuracy_score(yt, yf)
    rho = spearmanr(fai, pta)[0]
    mae = mean_absolute_error(fai, pta)
    bl = np.array([any(abs(v - b) <= 5 for b in BOUNDS) for v in pta])
    bl_acc = accuracy_score(yt[bl], yf[bl])
    cl_acc = accuracy_score(yt[~bl], yf[~bl])
    print(f'  kappa={kappa:.3f} overall={overall*100:.1f}% rho={rho:.3f} MAE={mae:.2f}')
    print(f'  borderline(<=5dB)={bl_acc*100:.1f}% (n={bl.sum()}) clear={cl_acc*100:.1f}% (n={(~bl).sum()}) | borderline share {bl.mean()*100:.1f}%')
    dist = np.array([min(abs(v - b) for b in BOUNDS) for v in pta])
    for dd in [1, 2, 3, 4, 5, 10, 15]:
        m = dist <= dd
        if m.sum():
            print(f'    <= {dd} dB: {(yt[m] == yf[m]).mean()*100:.1f}% (n={m.sum()})')
    diff = fai - pta
    bias = diff.mean(); sd = diff.std()
    print(f'  Bland-Altman: bias={bias:.1f} LoA={bias-1.96*sd:.1f}..{bias+1.96*sd:.1f} n={len(fai)}')

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
               'split': 'participant-level (80/20, seed 42)',
               'participants': int(len(raw)), 'clean_ears': len(ear_rows),
               'train_ears': len(train_rows), 'test_ears': len(test_rows),
               'train_participants': int(len(set(s for s, _, _, _ in train_rows))),
               'test_participants': int(len(test_ppl)),
               'kappa': round(kappa, 3), 'overall': round(overall, 4),
               'rho': round(rho, 3), 'mae': round(mae, 2),
               'borderline': round(bl_acc, 4), 'clear': round(cl_acc, 4),
               'borderline_share': round(bl.mean(), 4),
               'bias': round(bias, 1), 'loa_lo': round(bias - 1.96*sd, 1),
               'loa_hi': round(bias + 1.96*sd, 1), 'n_valid': int(len(fai)),
               'label_thresholds': [round(x, 1) for x in label_th],
               'single_ear': True, 'mf_params': params}
    (OUT / 'metrics_participant.json').write_text(json.dumps(metrics, indent=2), encoding='utf-8')
    pickle.dump({'params': params, 'y_te': y_te, 'y_true': yt, 'yf': yf,
                 'fai': fai, 'pta': pta, 'bl': bl, 'dist': dist},
                open(OUT / 'predictions_participant.pkl', 'wb'))
    print('\nsaved:', OUT / 'metrics_participant.json')


if __name__ == '__main__':
    main()
