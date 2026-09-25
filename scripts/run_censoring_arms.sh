#!/usr/bin/env bash
# Run the two censoring arms back to back on the same SEQN-keyed split, so the
# effect of right-censoring code 666 can be read off directly. Before the split
# was made stable the two arms also differed in which participants were held out,
# which confounded the comparison entirely.
set -e
cd /opt/data/fuzzy-audiogram

for ARM in off on; do
  if [ "$ARM" = "off" ]; then export FA_CENSOR_666=0; else export FA_CENSOR_666=1; fi
  echo "=== arm: censoring ${ARM} (FA_CENSOR_666=${FA_CENSOR_666}) ==="
  /usr/bin/python3 -u scripts/pipeline_participant.py > "run_censor_${ARM}.log" 2>&1
  mkdir -p "archive_censor_${ARM}"
  cp data/output_participant/*.json data/output_participant/*.pkl "archive_censor_${ARM}/" 2>/dev/null
  /usr/bin/python3 - "$ARM" <<'PY'
import json, sys
arm = sys.argv[1]
m = json.load(open(f"archive_censor_{arm}/metrics_participant.json"))
print(f"  ears={m['clean_ears']:,} test={m['test_ears']:,} "
      f"kappa={m['kappa']:.4f} overall={m['overall']*100:.1f}% "
      f"borderline={m['borderline']*100:.1f}% mae={m['mae']:.2f}")
PY
done

# leave the corrected arm in place as the canonical output
cp archive_censor_on/*.json archive_censor_on/*.pkl data/output_participant/
echo "CENSORING ARMS COMPLETE"
