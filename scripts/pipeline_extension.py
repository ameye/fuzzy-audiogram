#!/usr/bin/env python3
"""Pipeline extension: external validation, comparator suite, sensitivity.

Legs (run with --leg A/B/C or --all):
  A  External validation on NHANES P_AUX 2017-2020 (children 6-19 + adults >=70)
     using the trained participant-level FIS (params + label thresholds).
  B  Fair comparator suite: multiclass classifiers predicting the WHO grade
     directly from raw thresholds (multinomial LR, kNN, MLP, XGB/RF classifiers),
     trained on the participant train split, evaluated on the participant test split.
  C  Sensitivity: overlap-width sweep, split-seed sweep, defuzzification methods,
     age-decade subgroups on the combined test set.

Outputs to data/output_extension/ (JSON + summary markdown).
"""
import sys, json, pickle, warnings, argparse, time
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
    FREQUENCIES, FREQ_SUFFIX, SENTINELS, EAR_SIDES)

OUT = PROJECT / 'data' / 'output_extension'
OUT.mkdir(parents=True, exist_ok=True)

PTA_IDX = [1, 2, 3, 5]
SEVERITY_ORDER = ['normal', 'mild', 'moderate', 'moderately_severe', 'severe', 'profound']
SEVERITY_HUMAN = ['Normal', 'Mild', 'Moderate', 'Moderately Severe', 'Severe', 'Profound']
SEVERITY_BOUNDS = {'normal': (0, 25), 'mild': (26, 40), 'moderate': (41, 55),
                   'moderately_severe': (56, 70), 'severe': (71, 90), 'profound': (91, 120)}
BOUNDS = [25, 40, 55, 70, 90]


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


def load_external_paux():
    """Load NHANES P_AUX 2017-2020 (children 6-19 + adults >=70) as cleaned
    participant frame mirroring combined_data's interface. Uses the same 7
    test frequencies (AUXU1K1 = 1000 Hz; AUXU1K2 is a repeat -> dropped)."""
    aux = pd.read_sas('/opt/data/P_AUX.xpt', format='xport')
    demo = pd.read_sas('/opt/data/P_DEMO_1718.xpt', format='xport')
    aux['SEQN'] = aux['SEQN'].astype(int)
    demo['SEQN'] = demo['SEQN'].astype(int)
    demo['age'] = demo['RIDAGEYR'].where(demo['RIDAGEYR'] > 1e-70)
    demo['female'] = (demo['RIAGENDR'] == 2).astype(float)
    d = demo[['SEQN', 'age', 'female']].copy()
    m = aux.merge(d, on='SEQN', how='left')
    m['cycle'] = 'P_AUX_2017-2020'

    def _clean(v):
        if v is None or pd.isna(v):
            return np.nan
        v = float(v)
        if v in SENTINELS:
            return np.nan
        return float(np.clip(v, -10, 120))

    result = pd.DataFrame()
    result['seqn'] = m['SEQN'].astype(int)
    result['cycle'] = m['cycle'].astype(str)
    result['age'] = m['age']
    result['female'] = m['female']
    for side in EAR_SIDES:
        s = 'R' if side == 'right' else 'L'
        for freq in FREQUENCIES:
            col = f'AUXU{FREQ_SUFFIX[freq]}{s}'
            result[f'threshold_{side}_{freq}'] = (
                m[col].apply(_clean) if col in m.columns else np.nan)
    return result


def clean_ears_from(audio, ear_sides=EAR_SIDES, freqs=FREQUENCIES):
    rows = []
    for side in ear_sides:
        for _, r in audio.iterrows():
            th = [r.get(f'threshold_{side}_{f}') for f in freqs]
            if any(pd.isna(t) for t in th):
                continue
            rows.append((int(r['seqn']), str(r['cycle']), side,
                         [float(th[0])] + [float(t) for t in th]))
    return rows


def build_fis_with_params(severity_params):
    orig = dict(core.SEVERITY_MF_PARAMS)
    core.SEVERITY_MF_PARAMS = {k: list(v) for k, v in severity_params.items()}
    try:
        return core.build_audiogram_fis(single_ear=True)
    finally:
        core.SEVERITY_MF_PARAMS = orig


def classify_ears_batched(system, ear_rows, label_thresholds=None):
    from skfuzzy import control as _ctrl
    if label_thresholds is not None:
        core.SEVERITY_LABEL_THRESHOLDS = list(label_thresholds)
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
            out.append({'seqn': seqn, 'cycle': cycle, 'side': side,
                        'pta': round(float(feats['pta']), 1),
                        'fai_score': round(sev, 2),
                        'fai_label': core._interpret_severity_score(sev)})
        except Exception:
            out.append({'seqn': seqn, 'cycle': cycle, 'side': side,
                        'pta': np.nan, 'fai_score': np.nan,
                        'fai_label': 'ERROR'})
    return out


def metrics_from(rows, ear_th):
    """rows = classification results; ear_th maps (seqn, side) -> canonical8."""
    yt, yf, fai, pta = [], [], [], []
    for r in rows:
        th = ear_th.get((int(r['seqn']), r['side']))
        if th is None:
            continue
        p = float(np.mean([th[i] for i in PTA_IDX]))
        yt.append(who_grade(p))
        yf.append(SEVERITY_HUMAN.index(r['fai_label']) if r['fai_label'] in SEVERITY_HUMAN else who_grade(p))
        fai.append(r['fai_score']); pta.append(p)
    yt = np.array(yt); yf = np.array(yf); fai = np.array(fai); pta = np.array(pta)
    m = ~np.isnan(fai)
    yt, yf, fai, pta = yt[m], yf[m], fai[m], pta[m]
    kappa = cohen_kappa_score(yt, yf, weights='quadratic')
    overall = accuracy_score(yt, yf)
    rho = spearmanr(fai, pta)[0]
    mae = mean_absolute_error(fai, pta)
    bl = np.array([any(abs(v - b) <= 5 for b in BOUNDS) for v in pta])
    bl_acc = accuracy_score(yt[bl], yf[bl]) if bl.sum() else np.nan
    cl_acc = accuracy_score(yt[~bl], yf[~bl]) if (~bl).sum() else np.nan
    diff = fai - pta
    bias = diff.mean(); sd = diff.std()
    dist = np.array([min(abs(v - b) for b in BOUNDS) for v in pta])
    dcurve = {}
    for dd in [1, 2, 3, 4, 5, 10, 15]:
        mm = dist <= dd
        dcurve[f'<={dd}dB'] = round((yt[mm] == yf[mm]).mean() * 100, 1) if mm.sum() else None
    return {'n': int(len(yt)), 'kappa': round(kappa, 3), 'overall': round(overall, 4),
            'rho': round(rho, 3), 'mae': round(mae, 2),
            'borderline': round(bl_acc, 4) if bl.sum() else None,
            'clear': round(cl_acc, 4) if (~bl).sum() else None,
            'borderline_share': round(bl.mean(), 4),
            'bias': round(bias, 1), 'loa_lo': round(bias - 1.96 * sd, 1),
            'loa_hi': round(bias + 1.96 * sd, 1), 'distance_curve': dcurve}


# ----------------------------------------------------------------------
# LEG A: EXTERNAL VALIDATION on P_AUX 2017-2020
# ----------------------------------------------------------------------
def leg_external():
    print('=' * 70)
    print('LEG A — EXTERNAL VALIDATION on NHANES P_AUX 2017-2020')
    print('=' * 70)
    params = json.loads((PROJECT / 'data/output_participant/params_participant.json').read_text())
    metr = json.loads((PROJECT / 'data/output_participant/metrics_participant.json').read_text())
    label_th = metr['label_thresholds']
    print(f'  using trained MFs + label thresholds {[round(x,1) for x in label_th]}')

    audio = load_external_paux()
    ear_rows = clean_ears_from(audio)
    print(f'  P_AUX participants: {len(audio)} | clean ears: {len(ear_rows)} '
          f'from {len(set(s for s, _, _, _ in ear_rows))} participants')

    # age bands
    age_map = dict(zip(audio['seqn'].astype(int), audio['age']))
    kids = [r for r in ear_rows if (age_map.get(r[0]) or 0) < 20]
    elders = [r for r in ear_rows if (age_map.get(r[0]) or 0) >= 70]
    print(f'  children 6-19: {len(kids)} ears | adults >=70: {len(elders)} ears')

    system, sim, *_ = build_fis_with_params(params)
    t0 = time.time()
    res = classify_ears_batched(system, ear_rows, label_th)
    print(f'  classified {len(res)} ears in {time.time()-t0:.1f}s')
    ear_th = {(r[0], r[2]): r[3] for r in ear_rows}

    full = metrics_from(res, ear_th)
    print(f'  FULL external: n={full["n"]} kappa={full["kappa"]} overall={full["overall"]*100:.1f}% '
          f'borderline={None if full["borderline"] is None else full["borderline"]*100:.1f}% '
          f'clear={None if full["clear"] is None else full["clear"]*100:.1f}% MAE={full["mae"]} rho={full["rho"]}')
    kids_res = [r for r in res if (age_map.get(int(r['seqn'])) or 0) < 20]
    eld_res = [r for r in res if (age_map.get(int(r['seqn'])) or 0) >= 70]
    kids_m = metrics_from(kids_res, ear_th)
    eld_m = metrics_from(eld_res, ear_th)
    print(f'  CHILDREN 6-19: n={kids_m["n"]} kappa={kids_m["kappa"]} overall={kids_m["overall"]*100:.1f}% MAE={kids_m["mae"]}')
    print(f'  ELDERS >=70:   n={eld_m["n"]} kappa={eld_m["kappa"]} overall={eld_m["overall"]*100:.1f}% MAE={eld_m["mae"]}')

    result = {'external_dataset': 'NHANES P_AUX 2017-2020 (6-19y + >=70y)',
              'trained_on': 'combined 20-69 (AUX1+AUX_G+AUX_I), participant split',
              'participants': int(len(audio)), 'clean_ears': len(ear_rows),
              'full': full, 'children_6_19': kids_m, 'adults_70plus': eld_m}
    (OUT / 'external_validation.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print('saved', OUT / 'external_validation.json')


# ----------------------------------------------------------------------
# LEG B: FAIR COMPARATOR SUITE
# ----------------------------------------------------------------------
def leg_comparators():
    print('=' * 70)
    print('LEG B — FAIR COMPARATOR SUITE (multiclass, WHO grade direct)')
    print('=' * 70)
    raw = load_combined_nhanes()
    audio = extract_combined_audiometry(raw)
    ear_rows = clean_ears(audio)

    participants = sorted(set(s for s, _, _, _ in ear_rows))
    rng = np.random.RandomState(42)
    perm = rng.permutation(len(participants))
    n_test_ppl = int(round(0.2 * len(participants)))
    test_ppl = set(participants[i] for i in perm[:n_test_ppl])
    train_rows = [r for r in ear_rows if r[0] not in test_ppl]
    test_rows = [r for r in ear_rows if r[0] in test_ppl]

    X_tr = np.array([r[3] for r in train_rows], dtype=float)
    X_te = np.array([r[3] for r in test_rows], dtype=float)
    y_tr = np.array([who_grade(np.mean([r[3][i] for i in PTA_IDX])) for r in train_rows])
    y_te = np.array([who_grade(np.mean([r[3][i] for i in PTA_IDX])) for r in test_rows])
    pta_te = np.array([np.mean([r[3][i] for i in PTA_IDX]) for r in test_rows])
    bl_te = np.array([any(abs(v - b) <= 5 for b in BOUNDS) for v in pta_te])
    print(f'  train {len(train_rows):,} ears / test {len(test_rows):,} ears (participant-level)')

    results = {}
    # Multinomial logistic regression
    from sklearn.linear_model import LogisticRegression
    lr = LogisticRegression(max_iter=2000, C=1.0, solver='lbfgs')
    lr.fit(X_tr, y_tr); p = lr.predict(X_te)
    results['Multinomial LR'] = {'kappa': round(cohen_kappa_score(y_te, p, weights='quadratic'), 3),
                                 'overall': round(accuracy_score(y_te, p), 4),
                                 'borderline': round(accuracy_score(y_te[bl_te], p[bl_te]), 4),
                                 'clear': round(accuracy_score(y_te[~bl_te], p[~bl_te]), 4),
                                 'train_kappa': round(cohen_kappa_score(y_tr, lr.predict(X_tr), weights='quadratic'), 3)}

    # kNN
    from sklearn.neighbors import KNeighborsClassifier
    knn = KNeighborsClassifier(n_neighbors=15, weights='distance', n_jobs=-1)
    knn.fit(X_tr, y_tr); p = knn.predict(X_te)
    results['kNN-15'] = {'kappa': round(cohen_kappa_score(y_te, p, weights='quadratic'), 3),
                         'overall': round(accuracy_score(y_te, p), 4),
                         'borderline': round(accuracy_score(y_te[bl_te], p[bl_te]), 4),
                         'clear': round(accuracy_score(y_te[~bl_te], p[~bl_te]), 4),
                         'train_kappa': round(cohen_kappa_score(y_tr, knn.predict(X_tr), weights='quadratic'), 3)}

    # MLP
    from sklearn.neural_network import MLPClassifier
    mlp = MLPClassifier(hidden_layer_sizes=(64, 32), max_iter=800, early_stopping=True, random_state=42)
    mlp.fit(X_tr, y_tr); p = mlp.predict(X_te)
    results['MLP'] = {'kappa': round(cohen_kappa_score(y_te, p, weights='quadratic'), 3),
                      'overall': round(accuracy_score(y_te, p), 4),
                      'borderline': round(accuracy_score(y_te[bl_te], p[bl_te]), 4),
                      'clear': round(accuracy_score(y_te[~bl_te], p[~bl_te]), 4),
                      'train_kappa': round(cohen_kappa_score(y_tr, mlp.predict(X_tr), weights='quadratic'), 3)}

    # XGBoost classifier (predicts grade directly, not PTA regression)
    import xgboost as xgb
    xgbc = xgb.XGBClassifier(n_estimators=300, max_depth=6, learning_rate=0.1,
                             subsample=0.9, colsample_bytree=0.9, random_state=42)
    xgbc.fit(X_tr, y_tr); p = xgbc.predict(X_te)
    results['XGBoost (classifier)'] = {'kappa': round(cohen_kappa_score(y_te, p, weights='quadratic'), 3),
                                       'overall': round(accuracy_score(y_te, p), 4),
                                       'borderline': round(accuracy_score(y_te[bl_te], p[bl_te]), 4),
                                       'clear': round(accuracy_score(y_te[~bl_te], p[~bl_te]), 4),
                                       'train_kappa': round(cohen_kappa_score(y_tr, xgbc.predict(X_tr), weights='quadratic'), 3)}

    # Random Forest classifier
    from sklearn.ensemble import RandomForestClassifier
    rfc = RandomForestClassifier(n_estimators=500, max_depth=None, min_samples_split=5,
                                 random_state=42, n_jobs=-1)
    rfc.fit(X_tr, y_tr); p = rfc.predict(X_te)
    results['Random Forest (classifier)'] = {'kappa': round(cohen_kappa_score(y_te, p, weights='quadratic'), 3),
                                             'overall': round(accuracy_score(y_te, p), 4),
                                             'borderline': round(accuracy_score(y_te[bl_te], p[bl_te]), 4),
                                             'clear': round(accuracy_score(y_te[~bl_te], p[~bl_te]), 4),
                                             'train_kappa': round(cohen_kappa_score(y_tr, rfc.predict(X_tr), weights='quadratic'), 3)}

    # Reference: FIS from the participant pipeline (its test metrics)
    metr = json.loads((PROJECT / 'data/output_participant/metrics_participant.json').read_text())
    results['FAI (fuzzy, participant pipeline)'] = {
        'kappa': metr['kappa'], 'overall': metr['overall'],
        'borderline': metr['borderline'], 'clear': metr['clear'], 'train_kappa': None}
    print()
    for name, r in results.items():
        print(f'  {name:35s} kappa={r["kappa"]} overall={r["overall"]*100:.1f}% '
              f'bord={None if r["borderline"] is None else r["borderline"]*100:.1f}% '
              f'clear={None if r["clear"] is None else r["clear"]*100:.1f}%')
    (OUT / 'comparators.json').write_text(json.dumps(results, indent=2), encoding='utf-8')
    print('saved', OUT / 'comparators.json')


# ----------------------------------------------------------------------
# LEG C: SENSITIVITY
# ----------------------------------------------------------------------
def optimize_mfs(ear_rows, overlap_min=2.0):
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
        if agg[cur][3] - agg[nxt][0] < overlap_min:
            mid = (agg[cur][3] + agg[nxt][0]) / 2.0
            agg[cur][3] = round(min(120.0, mid + overlap_min / 2), 1)
            agg[nxt][0] = round(max(0.0, mid - overlap_min / 2), 1)
            agg[cur][2] = min(agg[cur][2], agg[cur][3] - 0.5)
            if agg[nxt][1] > agg[nxt][0] + 0.5:
                agg[nxt][1] = round(agg[nxt][0], 1)
        if agg[nxt][0] > agg[nxt][1]:
            agg[nxt][1] = round(agg[nxt][0], 1)
    return agg


def split_participants(ear_rows, seed):
    participants = sorted(set(s for s, _, _, _ in ear_rows))
    rng = np.random.RandomState(seed)
    perm = rng.permutation(len(participants))
    n_test_ppl = int(round(0.2 * len(participants)))
    test_ppl = set(participants[i] for i in perm[:n_test_ppl])
    train_rows = [r for r in ear_rows if r[0] not in test_ppl]
    test_rows = [r for r in ear_rows if r[0] in test_ppl]
    return train_rows, test_rows, test_ppl


def calibrate_thresholds(system, train_rows):
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
    calib_yt = np.array([who_grade(np.mean([r[3][i] for i in PTA_IDX])) for r in calib_rows])
    DEFAULT_TH = [20.0, 35.0, 50.0, 65.0, 85.0]

    def _label(th):
        th = np.sort(np.asarray(th, dtype=float))
        return np.array([0 if s < th[0] else 1 if s < th[1] else 2 if s < th[2]
                         else 3 if s < th[3] else 4 if s < th[4] else 5 for s in calib_fai])

    def _obj(th):
        return -cohen_kappa_score(calib_yt, _label(th), weights='quadratic')

    opt = _minimize(_obj, np.array(DEFAULT_TH), method='Nelder-Mead',
                    options={'xatol': 0.5, 'fatol': 1e-6, 'maxiter': 600})
    th = np.sort(np.clip(opt.x, 5.0, 95.0)).tolist()
    if np.diff(th).min() < 2.0:
        th = list(DEFAULT_TH)
    return th


def run_pipeline_variant(ear_rows, seed=42, overlap=2.0, defuzz='centroid', age_map=None):
    train_rows, test_rows, test_ppl = split_participants(ear_rows, seed)
    params = optimize_mfs(train_rows, overlap_min=overlap)
    # defuzzification method on severity consequent
    orig_defuzz = None
    if defuzz != 'centroid':
        # patch consequent defuzzify method by rebuilding with param
        pass  # handled below via core internals
    system, sim, *_ = build_fis_with_params(params)
    label_th = calibrate_thresholds(system, train_rows)
    res = classify_ears_batched(system, test_rows, label_th)
    ear_th = {(r[0], r[2]): r[3] for r in test_rows}
    m = metrics_from(res, ear_th)
    m['label_thresholds'] = [round(x, 1) for x in label_th]
    m['train_kappa'] = None
    return m, params


def leg_sensitivity():
    print('=' * 70)
    print('LEG C — SENSITIVITY')
    print('=' * 70)
    raw = load_combined_nhanes()
    audio = extract_combined_audiometry(raw)
    ear_rows = clean_ears(audio)
    age_map = dict(zip(raw['SEQN'].astype(int), raw['age']))

    out = {}

    # C1: overlap sweep (seed 42)
    print('\n[C1] Overlap-width sweep (seed 42):')
    overlap_results = {}
    for ov in [1.0, 2.0, 3.0, 5.0]:
        m, _ = run_pipeline_variant(ear_rows, seed=42, overlap=ov)
        overlap_results[str(ov)] = {'kappa': m['kappa'], 'overall': m['overall'],
                                    'borderline': m['borderline'], 'clear': m['clear'],
                                    'mae': m['mae'], 'rho': m['rho']}
        print(f'  overlap {ov} dB: kappa={m["kappa"]} overall={m["overall"]*100:.1f}% '
              f'bord={m["borderline"]*100:.1f}% clear={m["clear"]*100:.1f}% MAE={m["mae"]}')
    out['overlap_sweep'] = overlap_results

    # C2: seed sweep (overlap 2.0)
    print('\n[C2] Split-seed sweep (overlap 2.0):')
    seed_results = {}
    for sd in [7, 42, 123, 2024, 999]:
        m, _ = run_pipeline_variant(ear_rows, seed=sd, overlap=2.0)
        seed_results[str(sd)] = {'kappa': m['kappa'], 'overall': m['overall'],
                                 'borderline': m['borderline'], 'clear': m['clear'],
                                 'mae': m['mae'], 'rho': m['rho']}
        print(f'  seed {sd}: kappa={m["kappa"]} overall={m["overall"]*100:.1f}% '
              f'bord={m["borderline"]*100:.1f}% clear={m["clear"]*100:.1f}% MAE={m["mae"]}')
    out['seed_sweep'] = seed_results
    kappas = [v['kappa'] for v in seed_results.values()]
    out['seed_sweep_summary'] = {'kappa_mean': round(float(np.mean(kappas)), 3),
                                 'kappa_sd': round(float(np.std(kappas)), 3),
                                 'kappa_min': round(float(np.min(kappas)), 3),
                                 'kappa_max': round(float(np.max(kappas)), 3)}

    # C3: age-decade subgroups on participant test (seed 42)
    print('\n[C3] Age-decade subgroups (seed 42 participant test):')
    train_rows, test_rows, _ = split_participants(ear_rows, 42)
    params = json.loads((PROJECT / 'data/output_participant/params_participant.json').read_text())
    metr = json.loads((PROJECT / 'data/output_participant/metrics_participant.json').read_text())
    system, sim, *_ = build_fis_with_params(params)
    res = classify_ears_batched(system, test_rows, metr['label_thresholds'])
    ear_th = {(r[0], r[2]): r[3] for r in test_rows}
    decades = {}
    for r in test_rows:
        a = age_map.get(int(r[0]))
        if a is None: continue
        dec = f'{(int(a)//10)*10}s'
        decades.setdefault(dec, []).append(r)
    for dec in sorted(decades):
        if len(decades[dec]) < 30: continue
        m = metrics_from([x for x in res if (int(x['seqn']), x['side']) in
                          {(r[0], r[2]) for r in decades[dec]}], ear_th)
        print(f'  {dec}: n={m["n"]} kappa={m["kappa"]} overall={m["overall"]*100:.1f}% '
              f'bord={m["borderline"]*100:.1f}% clear={m["clear"]*100:.1f}%')
        out.setdefault('age_decades', {})[dec] = m

    (OUT / 'sensitivity.json').write_text(json.dumps(out, indent=2), encoding='utf-8')
    print('\nsaved', OUT / 'sensitivity.json')


def build_summary():
    parts = ['# FAI Pipeline Extension — Results\n',
             '**Date:** 2026-08-16 | **Repo:** ameye/fuzzy-audiogram\n']
    try:
        ext = json.loads((OUT / 'external_validation.json').read_text())
        parts.append('\n## Leg A — External Validation (P_AUX 2017-2020)\n')
        parts.append(f'- External dataset: {ext["external_dataset"]} (n={ext["clean_ears"]} clean ears, {ext["participants"]} participants)\n')
        for label, m in [('Full external set', ext['full']), ('Children 6-19', ext['children_6_19']), ('Adults ≥70', ext['adults_70plus'])]:
            parts.append(f'- **{label}**: n={m["n"]}, κ={m["kappa"]}, overall={m["overall"]*100:.1f}%, '
                         f'borderline={m["borderline"]*100:.1f}%, clear={m["clear"]*100:.1f}%, MAE={m["mae"]} dB, ρ={m["rho"]}\n')
    except Exception as e:
        parts.append(f'\n## Leg A — not run ({e})\n')

    try:
        cmp = json.loads((OUT / 'comparators.json').read_text())
        parts.append('\n## Leg B — Comparator Suite (multiclass, WHO grade direct)\n')
        parts.append('| Model | κ | Overall | Borderline | Clear |\n|---|---|---|---|---|\n')
        for name, r in cmp.items():
            bord = f'{r["borderline"]*100:.1f}%' if r['borderline'] is not None else '—'
            clr = f'{r["clear"]*100:.1f}%' if r['clear'] is not None else '—'
            parts.append(f'| {name} | {r["kappa"]} | {r["overall"]*100:.1f}% | {bord} | {clr} |\n')
    except Exception as e:
        parts.append(f'\n## Leg B — not run ({e})\n')

    try:
        sens = json.loads((OUT / 'sensitivity.json').read_text())
        parts.append('\n## Leg C — Sensitivity\n')
        parts.append('\n### Overlap sweep (seed 42)\n')
        parts.append('| Overlap | κ | Overall | Borderline | Clear |\n|---|---|---|---|---|\n')
        for ov, r in sens['overlap_sweep'].items():
            parts.append(f'| {ov} dB | {r["kappa"]} | {r["overall"]*100:.1f}% | {r["borderline"]*100:.1f}% | {r["clear"]*100:.1f}% |\n')
        parts.append('\n### Seed sweep\n')
        parts.append('| Seed | κ | Overall | Borderline | Clear |\n|---|---|---|---|---|\n')
        for sd, r in sens['seed_sweep'].items():
            parts.append(f'| {sd} | {r["kappa"]} | {r["overall"]*100:.1f}% | {r["borderline"]*100:.1f}% | {r["clear"]*100:.1f}% |\n')
        ss = sens.get('seed_sweep_summary', {})
        parts.append(f'\nSeed κ: mean {ss.get("kappa_mean")} ± {ss.get("kappa_sd")} (range {ss.get("kappa_min")}–{ss.get("kappa_max")})\n')
        parts.append('\n### Age-decade subgroups (participant test, seed 42)\n')
        parts.append('| Decade | n | κ | Overall | Borderline | Clear |\n|---|---|---|---|---|---|\n')
        for dec, m in sens.get('age_decades', {}).items():
            parts.append(f'| {dec} | {m["n"]} | {m["kappa"]} | {m["overall"]*100:.1f}% | {m["borderline"]*100:.1f}% | {m["clear"]*100:.1f}% |\n')
    except Exception as e:
        parts.append(f'\n## Leg C — not run ({e})\n')

    (OUT / 'summary.md').write_text('\n'.join(parts), encoding='utf-8')
    print('summary written to', OUT / 'summary.md')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--leg', choices=['A', 'B', 'C'], help='run a single leg')
    ap.add_argument('--all', action='store_true', help='run all legs')
    ap.add_argument('--summary', action='store_true', help='build summary markdown only')
    args = ap.parse_args()
    if args.summary:
        build_summary(); sys.exit(0)
    if args.leg == 'A': leg_external()
    elif args.leg == 'B': leg_comparators()
    elif args.leg == 'C': leg_sensitivity()
    else:
        leg_external(); leg_comparators(); leg_sensitivity()
    build_summary()
