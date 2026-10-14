#!/usr/bin/env bash
# Run the full pipeline 3 times from scratch (different PYTHONHASHSEED each time to expose any
# hidden dict/set-ordering dependence) and require byte-identical outputs.
set -euo pipefail
cd "$(dirname "$0")/.."
rm -rf runs && mkdir -p runs
for i in 1 2 3; do
  PYTHONHASHSEED=$((i * 1234)) python3 -m freight_watch --out "runs/run$i" > /dev/null
done
report=outputs/repro_check.txt
{
  echo "Reproducibility check: 3 untouched runs on the same input (PYTHONHASHSEED = 1234, 2468, 3702)"
  for f in output.csv weekly_metrics.csv run_log.json; do
    sha256sum runs/run1/$f runs/run2/$f runs/run3/$f | sed 's/^/  /'
    if cmp -s runs/run1/$f runs/run2/$f && cmp -s runs/run2/$f runs/run3/$f; then
      echo "  -> $f: IDENTICAL across all 3 runs"
    else
      echo "  -> $f: DIFFERENT"; exit 1
    fi
  done
  echo "RESULT: PASS - flags, verdicts, cited notes, numbers and even reason text are byte-identical."
} | tee "$report"
