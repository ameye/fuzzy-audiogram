#!/usr/bin/env python3
"""Cache FAI scores and reference grades for the training split.

The decision-curve analysis needs a risk model fitted on training data, so the
training ears have to be scored by the fuzzy system. That is a ten-minute pass,
so the result is cached to data/output_participant/train_predictions.pkl.
"""
import sys, json, pickle, warnings
from pathlib import Path

warnings.filterwarnings("ignore")
ROOT = Path("/opt/data/fuzzy-audiogram")
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import numpy as np
from fuzzy_audiogram.combined_data import (
    load_combined_nhanes, extract_combined_audiometry, clean_ears)
from pipeline_participant import build_fis_with_params, classify_ears_batched, who_grade, PTA_IDX

OUT = ROOT / "data/output_participant"
if (OUT / "train_predictions.pkl").exists():
    print("  cache already present; delete it to force a rescan")
    raise SystemExit(0)

raw = load_combined_nhanes()
ear_rows = clean_ears(extract_combined_audiometry(raw))
participants = sorted(set(s for s, _, _, _ in ear_rows))
rng = np.random.RandomState(42)
perm = rng.permutation(len(participants))
n_test = int(round(0.2 * len(participants)))
test_ppl = set(participants[i] for i in perm[:n_test])
train_rows = [r for r in ear_rows if r[0] not in test_ppl]
print(f"  train ears {len(train_rows):,}")

params = json.load(open(OUT / "metrics_participant.json"))["mf_params"]
system, sim, *_ = build_fis_with_params(params)

res = classify_ears_batched(system, train_rows)
fai = np.array([r["fai_score"] for r in res], float)
pta = np.array([r["pta"] for r in res], float)
y = np.array([who_grade(p) for p in pta], int)

pickle.dump({"fai": fai, "pta": pta, "y_true": y},
            open(OUT / "train_predictions.pkl", "wb"))
print(f"  cached {len(fai):,} training scores -> {OUT/'train_predictions.pkl'}")
