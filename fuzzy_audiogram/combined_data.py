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
SENTINELS = {888, 777, 999}

# Code 666 means "no response" — the listener did not respond at the audiometer's
# maximum output for that frequency. It is not the same event as 888 (could not
# obtain), 777 (refused) or 999 (other), which are genuine missing values, because
# the threshold is known to lie at or above the equipment ceiling. Treating 666 as
# missing therefore discards the most severe ears and biases the upper categories,
# which are already the thinnest (severe n=18, profound n=3 in the analysed test
# set). It is right-censored at the frequency's maximum output plus a 5 dB step
# instead, the standard convention for a no-response observation.
CENSOR_CODE = 666
CENSOR_PAD_DB = 5.0
CENSOR_CEILING_DB = 130.0

# Censoring is the default. Setting FA_CENSOR_666=0 restores the previous
# behaviour of treating 666 as missing, which exists so the two arms can be run
# back to back and the effect isolated. It is not a supported analysis mode.
import os as _os
CENSOR_666 = _os.environ.get("FA_CENSOR_666", "1") not in ("0", "false", "no")


def _clean_threshold(v):
    """None/NaN, 777, 888 or 999 -> NaN; 666 retained as a censoring marker;
    otherwise clipped to [-10, 120].

    The 666 marker is resolved to a decibel value per frequency (and per cycle,
    since the equipment ceiling differed between them) in
    :func:`extract_combined_audiometry`, which is the first place the frequency
    is known.
    """
    if v is None or pd.isna(v):
        return np.nan
    v = float(v)
    if v == CENSOR_CODE:
        return float(CENSOR_CODE) if CENSOR_666 else np.nan
    if v in SENTINELS:
        return np.nan
    return float(np.clip(v, -10, 120))
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


def extract_combined_audiometry(df):
    """Return a cleaned per-participant DataFrame (mirrors extract_audiometry
    interface): seqn, cycle, age, female, threshold_{ear}_{freq}."""
    result = pd.DataFrame()
    result['seqn'] = df['SEQN'].astype(int)
    result['cycle'] = df['cycle'].astype(str)
    result['age'] = df['age']
    result['female'] = df['female']
    ceilings = {}
    for side in EAR_SIDES:
        s = 'R' if side == 'right' else 'L'
        for freq in FREQUENCIES:
            col = f'AUXU{FREQ_SUFFIX[freq]}{s}'
            if col not in df.columns:
                result[f'threshold_{side}_{freq}'] = np.nan
                continue
            vals = df[col].apply(_clean_threshold)

            # Right-censor no-response observations. The audiometer ceiling is
            # taken per cycle and frequency as the largest in-range threshold
            # actually recorded, which in a sample of this size is the equipment
            # limit; the classic convention is to place the threshold one 5 dB
            # step above it. The ceiling is recorded so the manuscript can state
            # exactly what was assumed.
            observed = vals[(vals >= -10) & (vals <= 120)]
            ceiling = float(observed.max()) if len(observed) else 120.0
            censor_at = min(ceiling + CENSOR_PAD_DB, CENSOR_CEILING_DB)
            ceilings[f"{side}_{freq}"] = {"ceiling_db": ceiling, "imputed_db": censor_at,
                                          "n_censored": int((vals == CENSOR_CODE).sum())}
            if CENSOR_666:
                result[f'threshold_{side}_{freq}'] = vals.replace(
                    float(CENSOR_CODE), censor_at)
            else:
                result[f'threshold_{side}_{freq}'] = vals.replace(float(CENSOR_CODE), np.nan)

    if not result.empty:
        result.attrs["censoring"] = ceilings
        result.attrs["censoring_note"] = (
            "Code 666 (no response) right-censored at the per-cycle, per-frequency "
            f"maximum recorded output plus {CENSOR_PAD_DB:.0f} dB. Codes 777, 888 and "
            "999 treated as missing.")
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
