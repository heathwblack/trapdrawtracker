#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

python -m pipeline.fetch_feed
python -m pipeline.download
python -m pipeline.transcribe
python -m pipeline.extract

echo
echo "Done. Open docs/index.html or run: python -m http.server 8000 --directory docs"
