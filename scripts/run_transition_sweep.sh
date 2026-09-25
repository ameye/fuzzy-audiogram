#!/usr/bin/env bash
# Parametric sweep of the transition-width floor, 4 to 16 dB in 2 dB steps.
#
# The review's objection: the published ablation compared two points (raw gaps
# against a 10 dB floor), which shows widening helps but not that 10 dB is
# optimal. This sweeps the floor so the plateau is visible.
#
# Each run refits the percentile cores, applies the floor, recalibrates the
# label thresholds on the training set and revalidates on the held-out test set,
# so every point is a complete, independently calibrated run.
set -e
cd /opt/data/fuzzy-audiogram

OUT=data/output_participant
for W in 4.0 6.0 8.0 10.0 12.0 14.0 16.0; do
  echo "=== transition floor ${W} dB ==="
  FA_MIN_TRANSITION="$W" /usr/bin/python3 -u scripts/pipeline_participant.py \
      > "run_sweep_${W}.log" 2>&1
  mkdir -p "archive/sweep_${W}"
  cp "$OUT"/*.json "$OUT"/*.pkl "archive/sweep_${W}/"
  /usr/bin/python3 - "$W" <<'PY'
import json, sys
w = sys.argv[1]
m = json.load(open(f"archive/sweep_{w}/metrics_participant.json"))
print(f"  {w} dB  kappa={m['kappa']:.4f} overall={m['overall']*100:.1f}% "
      f"borderline={m['borderline']*100:.1f}% clear={m['clear']*100:.1f}% "
      f"mae={m['mae']:.2f}")
PY
done

# restore the canonical 10 dB run into the output directory
cp archive/sweep_10.0/*.json archive/sweep_10.0/*.pkl "$OUT/"
echo "SWEEP COMPLETE"
