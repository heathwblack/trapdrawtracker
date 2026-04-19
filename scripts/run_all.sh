#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

python3 -m pipeline.fetch_feed
python3 -m pipeline.fetch_captions
python3 -m pipeline.extract

echo
echo "Done. Open docs/index.html or run: python3 -m http.server 8000 --directory docs"
