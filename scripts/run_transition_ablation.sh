#!/usr/bin/env bash
# Transition-width ablation: the same Ruspini construction and the same fixed
# calibration, differing only in the minimum transition width. This isolates
# what widening the graded region does to agreement with the crisp reference.
set -e
cd /opt/data/fuzzy-audiogram

OUT=data/output_participant

# keep the 10 dB run that is currently sitting in the output dir
mkdir -p archive/transition_10.0
cp "$OUT"/*.json "$OUT"/*.pkl archive/transition_10.0/ 2>/dev/null || true
echo "archived the 10.0 dB run"

for W in 2.0 10.0; do
  echo "=== running min_transition=$W ==="
  FA_MIN_TRANSITION="$W" /usr/bin/python3 -u scripts/pipeline_participant.py \
      > "run_tb_${W}.log" 2>&1
  mkdir -p "archive/transition_${W}"
  cp "$OUT"/*.json "$OUT"/*.pkl "archive/transition_${W}/"
  echo "  done $W"
done

echo "ABLATION COMPLETE"
