#!/usr/bin/env bash
set -euo pipefail

python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'

echo "Starting API at http://127.0.0.1:8000"
uvicorn app.main:app --reload
