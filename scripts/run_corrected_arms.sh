#!/usr/bin/env bash
# Re-run every derived analysis against the corrected cohort (code 666 right-censored).
# The cohort changed by 55 ears, so anything that depends on it has to be recomputed:
# the transition sweep behind Table 3, the raw-gap ablation arm behind the clear-case
# comparison, and the WHO 2021 companion arm behind Table 4.
set -u
cd /opt/data/fuzzy-audiogram
export FA_CENSOR_666=1

echo "########## 1. raw-gap ablation arm (FA_MIN_TRANSITION=0) ##########"
FA_MIN_TRANSITION=0 /usr/bin/python3 -u scripts/pipeline_participant.py \
    > run_rawgap.log 2>&1 || echo "  RAW GAP ARM FAILED"
mkdir -p archive_corrected/raw_gap && cp data/output_participant/*.pkl archive_corrected/raw_gap/ 2>/dev/null

for W in 4 6 8 10 12 14 16; do
  echo "########## 2. transition sweep, floor = ${W} dB ##########"
  FA_MIN_TRANSITION=$W /usr/bin/python3 -u scripts/pipeline_participant.py \
      > "run_sweep_${W}.log" 2>&1 || echo "    sweep ${W} FAILED"
  mkdir -p "archive_corrected/sweep_${W}"
  cp data/output_participant/*.pkl "archive_corrected/sweep_${W}/" 2>/dev/null
  /usr/bin/python3 -c "
import json
m = json.load(open('data/output_participant/metrics_participant.json'))
print(f'    {W} dB: kappa={m[\"kappa\"]:.4f} borderline={m[\"borderline\"]*100:.1f}% mae={m[\"mae\"]:.2f}')"
done

echo "########## 3. WHO 2021 companion arm ##########"
/usr/bin/python3 -u scripts/pipeline_who2021_ruspini.py > run_who2021.log 2>&1 \
    || echo "  WHO 2021 ARM FAILED"

echo "########## restore the canonical corrected output ##########"
cp archive_censor_on/*.json archive_censor_on/*.pkl data/output_participant/ 2>/dev/null

echo "CORRECTED ARMS COMPLETE"
