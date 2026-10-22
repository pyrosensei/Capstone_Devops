#!/usr/bin/env bash
# Generates the local demo secrets that must not be committed.
#
# - Writes METRICS_TOKEN to monitoring/secrets/metrics_token for Prometheus.
# - Mirrors the same value into the local .env file (created from .env.example
#   when it does not exist yet).
#
# Usage: ./scripts/setup-secrets.sh
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SECRET_DIR="$REPO_ROOT/monitoring/secrets"
TOKEN_FILE="$SECRET_DIR/metrics_token"
ENV_FILE="$REPO_ROOT/.env"

mkdir -p "$SECRET_DIR"

if [ -s "$TOKEN_FILE" ]; then
  echo "Reusing existing monitoring/secrets/metrics_token"
else
  head -c 32 /dev/urandom | od -An -tx1 | tr -d ' \n' > "$TOKEN_FILE"
  echo "Generated monitoring/secrets/metrics_token"
fi

TOKEN="$(cat "$TOKEN_FILE")"

if [ ! -f "$ENV_FILE" ]; then
  cp "$REPO_ROOT/.env.example" "$ENV_FILE"
  echo "Created .env from .env.example"
fi

if grep -q '^METRICS_TOKEN=' "$ENV_FILE"; then
  python3 - "$ENV_FILE" "$TOKEN" <<'PY'
import sys
env_file, token = sys.argv[1], sys.argv[2]
with open(env_file, "r", encoding="utf-8") as handle:
    lines = handle.read().splitlines()
lines = [f"METRICS_TOKEN={token}" if line.startswith("METRICS_TOKEN=") else line for line in lines]
with open(env_file, "w", encoding="utf-8") as handle:
    handle.write("\n".join(lines) + "\n")
PY
else
  printf '\nMETRICS_TOKEN=%s\n' "$TOKEN" >> "$ENV_FILE"
fi

echo "METRICS_TOKEN is set in .env and monitoring/secrets/metrics_token"
echo "The Prometheus scrape endpoint /metrics now requires this bearer token."
