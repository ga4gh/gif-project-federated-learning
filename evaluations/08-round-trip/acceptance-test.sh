#!/usr/bin/env bash
# Round-trip acceptance test for the node-in-a-box. See README.md.
# Usage: ./acceptance-test.sh [--hello] [--skip-a4a]
set -euo pipefail
cd "$(dirname "$0")"

say() { printf '\n== %s\n' "$*"; }
need() { command -v "$1" >/dev/null || { echo "missing: $1 ($2)"; exit 1; }; }

need docker "Docker Desktop"
need python3 "Python 3.11+"
need curl "curl"

DRS_URL=${DRS_URL:-http://localhost:8080}
TES_URL=${TES_URL:-http://localhost:8000}
S3_ENDPOINT=${S3_ENDPOINT:-http://localhost:9000}

say "Checking services"
curl -fsS "$S3_ENDPOINT/minio/health/live" >/dev/null && echo "MinIO   ok  $S3_ENDPOINT" \
  || { echo "MinIO not reachable at $S3_ENDPOINT. Run: docker compose up -d"; exit 1; }
curl -fsS -u "${DRS_USER:-drs-user}:${DRS_PASSWORD:-drs-pass}" "$DRS_URL/ga4gh/drs/v1/service-info" >/dev/null \
  && echo "DRS     ok  $DRS_URL" \
  || { echo "DRS not reachable at $DRS_URL. Check: docker compose logs syfon"; exit 1; }
curl -fsS "$TES_URL/ga4gh/tes/v1/service-info" >/dev/null && echo "TES     ok  $TES_URL" \
  || { echo "TES not reachable at $TES_URL. Run (in another terminal): funnel server run --config config/funnel.yaml"; exit 1; }

if [[ " $* " != *" --hello "* ]]; then
  say "Building training image ${TRAIN_IMAGE:-fl-train:dev}"
  docker build -q -t "${TRAIN_IMAGE:-fl-train:dev}" training >/dev/null && echo "built"
fi

say "Python environment"
if [[ ! -d .venv ]]; then python3 -m venv .venv; fi
# shellcheck disable=SC1091
source .venv/bin/activate
pip install -q -r roundtrip/requirements.txt

say "Running round trip"
python roundtrip/roundtrip.py "$@"
