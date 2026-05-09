#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"

endpoints=(
  "/"
  "/stockin/applications/"
  "/approvals/"
  "/stockout/"
  "/returns/"
  "/supplies/"
)

ok=0
fail=0

for ep in "${endpoints[@]}"; do
  code=$(curl -s -o /dev/null -w "%{http_code}" "${BASE_URL}${ep}" || true)
  if [[ "$code" == "200" || "$code" == "302" ]]; then
    echo "[OK]   $ep -> $code"
    ok=$((ok+1))
  else
    echo "[FAIL] $ep -> $code"
    fail=$((fail+1))
  fi
done

echo "ok=$ok fail=$fail"
[[ $fail -eq 0 ]]
