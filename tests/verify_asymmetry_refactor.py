#!/usr/bin/env python3
"""Verify the asymmetry refactor does not change the published validation.

The refactor retargets the asymmetry rules from severity to a referral flag and
removes 6 asymmetry-bearing rules from the severity group. Because the published
validation runs a single-ear protocol with asymmetry pinned to zero, neither
group could have fired, so the test-set FAI should be bit-identical.

This checks that claim by recomputing the FAI on the same test ears with the
refactored FIS and comparing against the pre-refactor vector by MD5.
"""
import sys, json, pickle, hashlib, warnings
from pathlib import Path

warnings.filterwarnings("ignore")
ROOT = Path("/opt/data/fuzzy-audiogram")
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import numpy as np
from fuzzy_audiogram.combined_data import (
    load_combined_nhanes, extract_combined_audiometry, clean_ears)
from fuzzy_audiogram import core

BASELINE = ROOT / "archive/predictions_PRE_asymmetry_refactor.pkl"
EXPECTED_MD5 = "7e75859bc305053884a3841dd6a4dfca"

base = pickle.load(open(BASELINE, "rb"))
fai_base = np.asarray(base["fai"], float)
print(f"  baseline FAI n={len(fai_base):,} md5={hashlib.md5(fai_base.tobytes()).hexdigest()}")

# rebuild the same test split
raw = load_combined_nhanes()
ear_rows = clean_ears(extract_combined_audiometry(raw))
participants = sorted(set(s for s, _, _, _ in ear_rows))
perm = np.random.RandomState(42).permutation(len(participants))
n_test = int(round(0.2 * len(participants)))
test_ppl = set(participants[i] for i in perm[:n_test])
test_rows = [r for r in ear_rows if r[0] in test_ppl]
print(f"  test ears reconstructed: {len(test_rows):,}")

params = json.load(open(ROOT / "data/output_participant/metrics_participant.json"))["mf_params"]
label_th = json.load(open(ROOT / "data/output_participant/metrics_participant.json"))["label_thresholds"]
core.SEVERITY_MF_PARAMS = {k: list(v) for k, v in params.items()}
core.SEVERITY_LABEL_THRESHOLDS = list(label_th)

sys.path.insert(0, str(ROOT / "scripts"))
import pipeline_participant as pp

system, sim, *_ = pp.build_fis_with_params(params)
print(f"  rule base: {len(list(system.rules))} rules, "
      f"consequents {[c.label for c in system.consequents]}")

res = pp.classify_ears_batched(system, test_rows)
fai_new = np.array([r["fai_score"] for r in res], float)
md5_new = hashlib.md5(fai_new.tobytes()).hexdigest()

print(f"\n  refactored FAI n={len(fai_new):,} md5={md5_new}")
identical = (len(fai_new) == len(fai_base)) and (md5_new == EXPECTED_MD5)
print(f"  vector identical to baseline: {identical}")
if not identical:
    d = np.abs(fai_new - fai_base)
    print(f"  max abs difference: {d.max():.6f}   n differing: {(d > 1e-9).sum()}")

# simulate a bilateral case so the referral output is actually exercised
BILATERAL = [
    ("symmetric normal",     [15]*8, [15]*8),
    ("mild asymmetry",       [30]*8, [20]*8),
    ("moderate asymmetry",   [45]*8, [25]*8),
    ("severe asymmetry",     [65]*8, [20]*8),
    ("Reviewer's Case D",    [55]*8, [28]*8),
]
print("\n  bilateral behaviour (severity now reflects the tested ear alone):")
for name, left, right in BILATERAL:
    out = core.classify_audiogram(left, right)
    fai = out["fai_score"] if isinstance(out, dict) else out
    if isinstance(out, dict):
        fai = out.get("fai_score", out.get("fai"))
    print(f"    {name:20} FAI {float(fai):6.1f}  label {core._interpret_severity_score(float(fai))}")
