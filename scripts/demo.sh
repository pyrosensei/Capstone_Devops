#!/usr/bin/env bash
set -euo pipefail
BASE_URL="${DEVPLANE_URL:-http://127.0.0.1:8000}"
if command -v conda >/dev/null 2>&1; then
  conda run -n capstone_devops python scripts/smoke.py --base-url "$BASE_URL"
else
  python3 scripts/smoke.py --base-url "$BASE_URL"
fi
