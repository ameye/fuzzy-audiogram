#!/usr/bin/env python3
"""WHO 2021 classification-schema variant of the FAI pipeline.

The deployed FAI system (and the Ear & Hearing manuscript) uses the WHO 1991-style
6-grade schema with crisp boundaries at 25/40/55/70/90 dB HL. The WHO 2021 World
Report on Hearing introduced a revised 7-grade schema with boundaries at
20/35/50/65/80/95 dB HL (adding a 'complete' grade >= 95 dB, better-ear PTA-4).

This script rebuilds the entire pipeline under the WHO 2021 schema:
  1. Load combined NHANES 20-69 cohort (identical to pipeline_participant.py)
  2. Participant-level 80/20 split (seed 42, same as the deployed validation)
  3. Optimise 7-category severity MFs on the training set (WHO 2021 category labels)
  4. Build a 7-category Mamdani FIS (severity rules extended with 'complete')
  5. Calibrate FAI score->label thresholds (6 thresholds for 7 labels) on training
  6. Validate on the held-out test set: kappa, overall, borderline/clear, MAE, rho,
     Bland-Altman, distance-to-boundary accuracy
  7. Same-test comparison: classify the SAME test ears with the deployed 6-grade FIS
     (participant-optimised params) and the WHO 2021 variant; report both metric
     sets plus a schema-reclassification matrix and boundary-zone analysis
  8. ML comparators regressing PTA-4, graded under the WHO 2021 schema

Outputs: data/output_who2021_ruspini/{params,metrics}_who2021.json, reclassification
matrix + boundary analysis CSVs, predictions pkl.
"""
import sys, json, os, pickle, warnings
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
from fuzzy_audiogram.ruspini import build_ruspini_partition, verify

# Minimum transition width, matching the deployed 6-grade arm so the two
# differ only in the classification schema.
MIN_TRANSITION_DB = float(os.environ.get('FA_MIN_TRANSITION', '10.0'))
from fuzzy_audiogram.combined_data import (
    load_combined_nhanes, extract_combined_audiometry, clean_ears,
    FREQUENCIES)

OUT = PROJECT / 'data' / 'output_who2021_ruspini'
OUT.mkdir(parents=True, exist_ok=True)

PTA_IDX = [1, 2, 3, 5]

# ---- WHO 2021 schema (7 grades) ----
SEVERITY_ORDER = ['normal', 'mild', 'moderate', 'moderately_severe',
                  'severe', 'profound', 'complete']
SEVERITY_HUMAN = ['Normal', 'Mild', 'Moderate', 'Moderately Severe',
                  'Severe', 'Profound', 'Complete']
# WHO 2021 (better-ear PTA-4): normal <=20, mild 21-35, moderate 36-50,
# moderately severe 51-65, severe 66-80, profound 81-95, complete >=96.
SEVERITY_BOUNDS = {'normal': (0, 20), 'mild': (21, 35), 'moderate': (36, 50),
                   'moderately_severe': (51, 65), 'severe': (66, 80),
                   'profound': (81, 95), 'complete': (96, 120)}
BOUNDS = [20, 35, 50, 65, 80, 95]
OVERLAP_MIN = 2.0


def who_grade(v):
    if v <= 20: return 0
    elif v <= 35: return 1
    elif v <= 50: return 2
    elif v <= 65: return 3
    elif v <= 80: return 4
    elif v <= 95: return 5
    else: return 6


def who_category(v):
    if v < 0: return 'normal'
    for cat, (lo, hi) in SEVERITY_BOUNDS.items():
        if lo <= v <= hi:
            return cat
    return 'complete'


def _default_params(cat):
    """Boundary-anchored trapezoid for sparse categories (n < 10 per freq).

    WHO 2021 defines categories by their dB boundaries; when a category has
    too few training observations for a stable percentile fit (the complete
    grade >= 96 dB is extremely sparse in the working-age cohort), anchor the
    MF to its WHO 2021 boundary band instead of a bottom-of-scale placeholder.
    """
    lo, hi = SEVERITY_BOUNDS[cat]
    if cat == 'normal':
        return [0.0, 0.0, min(22.0, hi), min(26.0, hi + 5)]
    if cat == 'complete':
        return [lo - 3, lo + 1, 120.0, 120.0]
    return [lo - 3, lo + 1, min(hi, 110.0), min(hi + 5, 120.0)]


def optimize_mfs(ear_rows, min_transition=MIN_TRANSITION_DB):
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


# ---- 7-category severity output MF placement on the 0-100 FAI scale ----
SEVERITY_OUTPUT_PARAMS = {
    'normal':            [0, 0, 8, 20],
    'mild':              [12, 20, 32, 42],
    'moderate':          [32, 40, 50, 58],
    'moderately_severe': [52, 58, 68, 75],
    'severe':            [68, 75, 85, 92],
    'profound':          [85, 92, 97, 100],
    'complete':          [95, 97, 100, 100],
}


def get_severity_rules_7cat(threshold, severity):
    """7 primary + 7 blended severity rules for the WHO 2021 schema."""
    rules = []
    for cat in SEVERITY_ORDER:
        rules.append(ctrl.Rule(threshold[cat], severity[cat]))
    pairs = [(SEVERITY_ORDER[i], SEVERITY_ORDER[i + 1]) for i in range(6)]
    # blended pair -> the UPPER category of the pair (matches deployed behaviour)
    for lo, hi in pairs:
        rules.append(ctrl.Rule(threshold[lo] & threshold[hi], severity[hi]))
    # triple blend at the normal/mild/moderate junction
    rules.append(ctrl.Rule(threshold['normal'] & threshold['mild'] & threshold['moderate'],
                           severity['moderate']))
    return rules


def build_fis_who2021(severity_params, single_ear=True):
    """Build the 7-category Mamdani FIS (mirrors core.build_audiogram_fis)."""
    import skfuzzy as fuzz
    from skfuzzy import control as ctrl

    threshold_ant = ctrl.Antecedent(np.arange(0, 121, 1), 'threshold')
    slope_ant = ctrl.Antecedent(np.arange(-40, 81, 1), 'slope')
    notch_ant = ctrl.Antecedent(np.arange(0, 51, 1), 'notch')
    asym_ant = ctrl.Antecedent(np.arange(0, 61, 1), 'asymmetry')
    severity_con = ctrl.Consequent(np.arange(0, 101, 1), 'severity')
    shape_con = ctrl.Consequent(np.arange(0, 101, 1), 'audiogram_shape')

    for cat, params in severity_params.items():
        threshold_ant[cat] = fuzz.trapmf(threshold_ant.universe, params)
    for cat, params in core.SLOPE_MF_PARAMS.items():
        slope_ant[cat] = fuzz.trapmf(slope_ant.universe, params)
    for cat, params in core.NOTCH_MF_PARAMS.items():
        notch_ant[cat] = fuzz.trapmf(notch_ant.universe, params)
    for cat, params in core.ASYMMETRY_MF_PARAMS.items():
        asym_ant[cat] = fuzz.trapmf(asym_ant.universe, params)
    for cat, params in SEVERITY_OUTPUT_PARAMS.items():
        severity_con[cat] = fuzz.trapmf(severity_con.universe, params)
    for cat, params in core.SHAPE_OUTPUT_PARAMS.items():
        shape_con[cat] = fuzz.trapmf(shape_con.universe, params)

    from fuzzy_audiogram.rules import (get_configuration_rules,
                                       get_asymmetry_rules, get_mixed_loss_rules)
    rules = []
    rules.extend(get_severity_rules_7cat(threshold_ant, severity_con))
    rules.extend(get_configuration_rules(slope_ant, notch_ant, shape_con, severity_con))
    rules.extend(get_asymmetry_rules(asym_ant, severity_con, single_ear=single_ear))
    rules.extend(get_mixed_loss_rules(threshold_ant, slope_ant, asym_ant, severity_con))

    system = ctrl.ControlSystem(rules)
    simulation = ctrl.ControlSystemSimulation(system)
    return system, simulation


def build_fis_6cat(severity_params, label_thresholds):
    """Build the DEPLOYED 6-grade FIS with given (participant-optimised) params."""
    orig_params = dict(core.SEVERITY_MF_PARAMS)
    orig_th = list(core.SEVERITY_LABEL_THRESHOLDS)
    core.SEVERITY_MF_PARAMS = {k: list(v) for k, v in severity_params.items()}
    core.SEVERITY_LABEL_THRESHOLDS = list(label_thresholds)
    try:
        return core.build_audiogram_fis(single_ear=True)
    finally:
        core.SEVERITY_MF_PARAMS = orig_params
        core.SEVERITY_LABEL_THRESHOLDS = orig_th


def interpret_2021(score, th):
    """Map FAI score to WHO 2021 label using calibrated thresholds."""
    if score < th[0]: return 'Normal'
    elif score < th[1]: return 'Mild'
    elif score < th[2]: return 'Moderate'
    elif score < th[3]: return 'Moderately Severe'
    elif score < th[4]: return 'Severe'
    elif score < th[5]: return 'Profound'
    else: return 'Complete'


def classify_ears_batched(system, ear_rows, label_fn):
    out = []
    for seqn, cycle, side, th in ear_rows:
        try:
            sim = ctrl.ControlSystemSimulation(system)
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
                        'fai_label': label_fn(sev)})
        except Exception:
            out.append({'seqn': seqn, 'cycle': cycle, 'side': side,
                        'pta': np.nan, 'fai_score': np.nan,
                        'fai_label': 'ERROR'})
    return out


def main():
    print('=' * 70)
    print('WHO 2021 SCHEMA VARIANT — COMBINED 20-69 COHORT, PARTICIPANT SPLIT')
    print('=' * 70)

    print('\n[1] Loading combined NHANES adult cycles...')
    raw = load_combined_nhanes()
    audio = extract_combined_audiometry(raw)
    ear_rows = clean_ears(audio)
    print(f'  participants: {len(raw)} | clean ears: {len(ear_rows)} '
          f'from {len(set(s for s, _, _, _ in ear_rows))} participants')

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
    tr_mask = np.array([r[0] not in test_ppl for r in ear_rows])
    te_mask = ~tr_mask
    X_tr, y_tr = X_all[tr_mask], y_all[tr_mask]
    X_te, y_te = X_all[te_mask], y_all[te_mask]

    print('\n[2] Optimising WHO 2021 7-category MFs on the TRAINING set...')
    params = optimize_mfs(train_rows)
    for cat in SEVERITY_ORDER:
        print(f'    {cat:20s}: {params[cat]}')
    (OUT / 'params_who2021.json').write_text(json.dumps(params, indent=2), encoding='utf-8')

    print('\n[3] Building 7-category Mamdani FIS (single-ear mode)...')
    system, sim = build_fis_who2021(params, single_ear=True)
    print('  FIS built')

    print('\n[3b] Calibrating label thresholds on the TRAINING set...')
    from scipy.optimize import minimize as _minimize
    _g = np.array([who_grade(np.mean([r[3][i] for i in PTA_IDX])) for r in train_rows])
        # Population-representative draw rather than a class-balanced one: kappa is a
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

    print(f'\n[4] Classifying test ears with WHO 2021 FIS (n={len(test_rows)})...')
    import time
    t0 = time.time()
    label_fn = lambda s: interpret_2021(s, label_th)
    test_res_who = classify_ears_batched(system, test_rows, label_fn)
    dt = time.time() - t0
    print(f'  classified {len(test_res_who)} in {dt:.1f}s ({dt / len(test_res_who) * 1000:.0f} ms/ear)')

    # ---- Deployed 6-grade FIS on the SAME test ears ----
    print('\n[4b] Deployed 6-grade FIS on the same test ears...')
    part_metrics = json.load(open(PROJECT / 'data' / 'output_participant' / 'metrics_participant.json'))
    part_params = json.load(open(PROJECT / 'data' / 'output_participant' / 'params_participant.json'))
    part_th = part_metrics['label_thresholds']
    sys6 = build_fis_6cat(part_params, part_th)[0]

    def label_6cat(sev):
        return ('Normal' if sev < part_th[0] else 'Mild' if sev < part_th[1] else
                'Moderate' if sev < part_th[2] else 'Moderately Severe' if sev < part_th[3] else
                'Severe' if sev < part_th[4] else 'Profound')

    test_res_6 = classify_ears_batched(sys6, test_rows, label_6cat)

    def grade_6cat(label):
        return ['Normal', 'Mild', 'Moderate', 'Moderately Severe', 'Severe',
                'Profound'].index(label) if label in ['Normal', 'Mild', 'Moderate',
                'Moderately Severe', 'Severe', 'Profound'] else -1

    # ---- Align rows by (seqn, side) ----
    def align(res):
        d = {}
        for r in res:
            if r['fai_score'] == r['fai_score']:
                d[(int(r['seqn']), r['side'])] = r
        return d

    d_who = align(test_res_who)
    d_6 = align(test_res_6)
    keys = sorted(set(d_who) & set(d_6))
    test_th = {}
    for s, _, _, th in test_rows:
        test_th.setdefault(s, []).append(th)
    y_true, y_who, y_6, fai_who, fai_6, pta_all = [], [], [], [], [], []
    for k in keys:
        seqn, side = k
        ths = test_th[int(seqn)]
        idx = 0 if side == 'right' else (1 if len(ths) > 1 else 0)
        th = ths[idx]
        p = float(np.mean([th[i] for i in PTA_IDX]))
        y_true.append(who_grade(p))
        y_who.append(SEVERITY_HUMAN.index(d_who[k]['fai_label']) if d_who[k]['fai_label'] in SEVERITY_HUMAN else who_grade(p))
        g6 = grade_6cat(d_6[k]['fai_label'])
        y_6.append(g6 if g6 >= 0 else who_grade(p))
        fai_who.append(d_who[k]['fai_score'])
        fai_6.append(d_6[k]['fai_score'])
        pta_all.append(p)
    y_true = np.array(y_true); y_who = np.array(y_who); y_6 = np.array(y_6)
    fai_who = np.array(fai_who); fai_6 = np.array(fai_6); pta_all = np.array(pta_all)
    n = len(y_true)

    def metrics_block(yt, yf, fai, pta, tag):
        kappa = cohen_kappa_score(yt, yf, weights='quadratic')
        overall = accuracy_score(yt, yf)
        rho = spearmanr(fai, pta)[0]
        mae = mean_absolute_error(fai, pta)
        bl = np.array([any(abs(v - b) <= 5 for b in BOUNDS) for v in pta])
        bl_acc = accuracy_score(yt[bl], yf[bl])
        cl_acc = accuracy_score(yt[~bl], yf[~bl])
        diff = fai - pta
        bias = diff.mean(); sd = diff.std()
        print(f'  [{tag}] kappa={kappa:.3f} overall={overall*100:.1f}% rho={rho:.3f} MAE={mae:.2f}')
        print(f'  [{tag}] borderline(<=5dB)={bl_acc*100:.1f}% (n={bl.sum()}) clear={cl_acc*100:.1f}% (n={(~bl).sum()}) | borderline share {bl.mean()*100:.1f}%')
        print(f'  [{tag}] Bland-Altman: bias={bias:.1f} LoA={bias-1.96*sd:.1f}..{bias+1.96*sd:.1f} n={len(fai)}')
        return {'kappa': round(kappa, 3), 'overall': round(overall, 4),
                'rho': round(rho, 3), 'mae': round(mae, 2),
                'borderline': round(bl_acc, 4), 'clear': round(cl_acc, 4),
                'borderline_share': round(bl.mean(), 4), 'n': int(n),
                'bias': round(bias, 1), 'loa_lo': round(bias - 1.96*sd, 1),
                'loa_hi': round(bias + 1.96*sd, 1)}

    print('\n[5] Validation metrics (WHO 2021 schema, test set)')
    m_who = metrics_block(y_true, y_who, fai_who, pta_all, 'WHO2021')

    print('\n[5b] Same test ears under the DEPLOYED 6-grade schema (comparison)')
    m_6 = metrics_block(y_true, y_6, fai_6, pta_all, '6GRADE')

    # ---- Reclassification matrix: 6-grade label vs WHO 2021 label ----
    print('\n[6] Schema reclassification matrix (deployed 6-grade vs WHO 2021)...')
    g6_human = ['Normal', 'Mild', 'Moderate', 'Moderately Severe', 'Severe', 'Profound']
    mat = np.zeros((6, 7), dtype=int)
    for i, k in enumerate(keys):
        g6 = y_6[i]
        gw = y_who[i]
        mat[g6, gw] += 1
    rec_df = pd.DataFrame(mat, index=g6_human, columns=SEVERITY_HUMAN)
    rec_df.to_csv(OUT / 'reclassification_matrix.csv')
    print(rec_df)

    # ---- Boundary-zone analysis (WHO 2021 boundaries) ----
    print('\n[6b] Boundary-zone accuracy vs distance to WHO 2021 boundaries...')
    dist = np.array([min(abs(v - b) for b in BOUNDS) for v in pta_all])
    dist_rows = []
    for dd in [1, 2, 3, 4, 5, 10, 15]:
        m = dist <= dd
        if m.sum():
            acc = (y_true[m] == y_who[m]).mean() * 100
            dist_rows.append({'within_dB': dd, 'n': int(m.sum()),
                              'accuracy_pct': round(acc, 1)})
            print(f'    <= {dd} dB: {acc:.1f}% (n={m.sum()})')
    dist_df = pd.DataFrame(dist_rows)
    dist_df.to_csv(OUT / 'distance_accuracy.csv', index=False)

    # ---- Per-category prevalence (WHO 2021) ----
    print('\n[6c] WHO 2021 test-set prevalence (crisp reference):')
    for c in range(7):
        cnt = int((y_true == c).sum())
        print(f'    {SEVERITY_HUMAN[c]:20s}: {cnt} ({cnt / n * 100:.1f}%)')

    # ---- ML comparators (regress PTA-4, grade under WHO 2021) ----
    print('\n[7] ML comparators (regress PTA-4, WHO 2021 grading)')
    import xgboost as xgb
    from sklearn.ensemble import RandomForestRegressor
    xgbm = xgb.XGBRegressor(n_estimators=100, max_depth=6, learning_rate=0.1, random_state=42)
    xgbm.fit(X_tr, y_tr)
    rf = RandomForestRegressor(n_estimators=1000, max_depth=10, min_samples_split=5,
                               random_state=42, n_jobs=-1)
    rf.fit(X_tr, y_tr)
    yc = np.array([who_grade(v) for v in y_te])
    bl_te = np.array([any(abs(v - b) <= 5 for b in BOUNDS) for v in y_te])
    comparators = {}
    for name, mdl in [('XGBoost', xgbm), ('Random Forest', rf)]:
        pred = mdl.predict(X_te)
        plab = np.array([who_grade(v) for v in pred])
        res = {'kappa': round(cohen_kappa_score(yc, plab, weights='quadratic'), 3),
               'overall': round(accuracy_score(yc, plab), 4),
               'borderline': round(accuracy_score(yc[bl_te], plab[bl_te]), 4),
               'clear': round(accuracy_score(yc[~bl_te], plab[~bl_te]), 4),
               'mae': round(mean_absolute_error(y_te, pred), 2)}
        comparators[name] = res
        print(f'    {name}: kappa={res["kappa"]} overall={res["overall"]*100:.1f}% '
              f'borderline={res["borderline"]*100:.1f}% clear={res["clear"]*100:.1f}% '
              f'MAE={res["mae"]:.2f}')

    metrics = {
        'schema': 'WHO 2021 (7 grades; boundaries 20/35/50/65/80/95 dB)',
        'comparison_schema': 'deployed WHO 1991-style 6 grades (25/40/55/70/90)',
        'cohort': 'combined 20-69 (AUX1+AUX_G+AUX_I)',
        'split': 'participant-level (80/20, seed 42)',
        'participants': int(len(raw)), 'clean_ears': len(ear_rows),
        'train_ears': len(train_rows), 'test_ears': len(test_rows),
        'test_participants': int(len(test_ppl)), 'n_valid': n,
        'who2021': m_who, 'deployed_6grade': m_6,
        'comparators': comparators,
        'label_thresholds': [round(x, 1) for x in label_th],
        'mf_params': params, 'single_ear': True}
    (OUT / 'metrics_who2021.json').write_text(json.dumps(metrics, indent=2), encoding='utf-8')
    pickle.dump({'params': params, 'y_true': y_true, 'y_who': y_who, 'y_6': y_6,
                 'fai_who': fai_who, 'fai_6': fai_6, 'pta': pta_all,
                 'dist': dist, 'keys': keys},
                open(OUT / 'predictions_who2021.pkl', 'wb'))
    print('\nsaved:', OUT / 'metrics_who2021.json')


if __name__ == '__main__':
    main()
