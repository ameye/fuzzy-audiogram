"""Combined NHANES adult (20-69 y) audiometry loader.

Loads the three NHANES cycles that administered audiometry to working-age
adults (AUX1 1999-2000, AUX_G 2011-2012, AUX_I 2015-2016), cleans them with
the same conventions as fuzzy_audiogram.data, and joins demographics.

The returned DataFrame mirrors the interface of extract_audiometry():
  - seqn, cycle, age, female
  - threshold_{ear}_{freq} for ear in {right, left}, freq in the 7 test freqs
  - tymp_/otoscopy columns are NOT carried over (absent from older cycles)
"""
import numpy as np
import pandas as pd

CYCLES = [
    ('AUX1_1999-2000', '/opt/data/AUX1_9900.xpt', '/opt/data/DEMO_9900.xpt'),
    ('AUX_G_2011-2012', '/opt/data/AUX_G_1112.xpt', '/opt/data/DEMO_G_1112.xpt'),
    ('AUX_I_2015-2016', '/opt/data/AUX_I_1516.xpt', '/opt/data/DEMO_I_1516.xpt'),
]
FREQUENCIES = [500, 1000, 2000, 3000, 4000, 6000, 8000]
# AUXU column suffixes per frequency (same across all three cycles)
FREQ_SUFFIX = {500: '500', 1000: '1K1', 2000: '2K', 3000: '3K',
               4000: '4K', 6000: '6K', 8000: '8K'}
SENTINELS = {666, 777, 888, 999}
EAR_SIDES = ['right', 'left']


def _load_cycle(tag, aux_path, demo_path):
    a = pd.read_sas(aux_path, format='xport')
    d = pd.read_sas(demo_path, format='xport')
    a['SEQN'] = a['SEQN'].astype(int)
    d['SEQN'] = d['SEQN'].astype(int)
    age_col = 'RIDAGEYR' if 'RIDAGEYR' in d.columns else None
    demo = d[['SEQN', age_col, 'RIAGENDR']].copy()
    demo['age'] = demo[age_col].where(demo[age_col] > 1e-70)   # SAS subnormal -> NaN
    demo['female'] = (demo['RIAGENDR'] == 2).astype(float)
    demo = demo.drop(columns=[age_col, 'RIAGENDR'])
    m = a.merge(demo, on='SEQN', how='left')
    m['cycle'] = tag
    return m


def load_combined_nhanes():
    """Load and merge the three adult audiometry cycles."""
    frames = [_load_cycle(*c) for c in CYCLES]
    return pd.concat(frames, ignore_index=True)


def _clean_threshold(v):
    """None/NaN or sentinel -> NaN; else float clipped to [-10, 120]."""
    if v is None or pd.isna(v):
        return np.nan
    v = float(v)
    if v in SENTINELS:
        return np.nan
    return float(np.clip(v, -10, 120))


def extract_combined_audiometry(df):
    """Return a cleaned per-participant DataFrame (mirrors extract_audiometry
    interface): seqn, cycle, age, female, threshold_{ear}_{freq}."""
    result = pd.DataFrame()
    result['seqn'] = df['SEQN'].astype(int)
    result['cycle'] = df['cycle'].astype(str)
    result['age'] = df['age']
    result['female'] = df['female']
    for side in EAR_SIDES:
        s = 'R' if side == 'right' else 'L'
        for freq in FREQUENCIES:
            col = f'AUXU{FREQ_SUFFIX[freq]}{s}'
            result[f'threshold_{side}_{freq}'] = (
                df[col].apply(_clean_threshold) if col in df.columns else np.nan)
    return result


def clean_ears(audio, ear_sides=EAR_SIDES, freqs=FREQUENCIES):
    """Yield (seqn, cycle, side, canonical8) rows for ears with all seven
    thresholds valid. Canonical8 = [500-proxy, 500, 1k, 2k, 3k, 4k, 6k, 8k]
    (250 Hz is not tested in these cycles; 500 Hz is the proxy)."""
    rows = []
    for side in ear_sides:
        for _, r in audio.iterrows():
            th = [r.get(f'threshold_{side}_{f}') for f in freqs]
            if any(pd.isna(t) for t in th):
                continue
            rows.append((int(r['seqn']), str(r['cycle']), side,
                         [float(th[0])] + [float(t) for t in th]))
    return rows
