#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"

if ! command -v curl >/dev/null 2>&1; then
  echo "curl is required" >&2
  exit 1
fi

echo "[1/6] Bootstrapping Substack sources from data/substack_sources.txt"
curl -sS -X POST "$BASE_URL/sources/substack/bootstrap" \
  -H 'Content-Type: application/json' \
  -d '{"use_default_file": true}' | python -m json.tool

echo "[2/6] Bootstrapping reference sources (includes DataRoma)"
curl -sS -X POST "$BASE_URL/sources/reference/bootstrap" \
  -H 'Content-Type: application/json' \
  -d '{"use_default_file": true}' | python -m json.tool

echo "[3/6] Ingesting a sample investment note"
DOC_JSON=$(curl -sS -X POST "$BASE_URL/documents/paste" \
  -H 'Content-Type: application/json' \
  -d '{
    "source_name": "manual",
    "title": "Demo Value Co",
    "text": "Long DEMO because normalized earnings are improving and leverage is falling. Catalyst: refinancing and margin recovery. Risk: demand slowdown. Valuation at 7x EV/EBIT appears discounted versus peers."
  }')

echo "$DOC_JSON" | python -m json.tool
DOC_ID=$(echo "$DOC_JSON" | python -c 'import json,sys; print(json.load(sys.stdin)["id"])')

echo "[4/6] Feed results"
curl -sS "$BASE_URL/feed" | python -m json.tool

echo "[5/6] Search results for DEMO"
curl -sS "$BASE_URL/search?q=DEMO" | python -m json.tool

echo "[6/6] Weekly digest"
curl -sS "$BASE_URL/digests/weekly/latest" | python -m json.tool

echo "Done. Example document id: $DOC_ID"
