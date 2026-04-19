# Trap Draw Tracker

A tracker for topics the Trap Draw hosts "monitor" on **Chop Session** episodes — the substantive stories they dig into each week, with their POV and a status line for each one. Scoped to 2026 episodes.

**Published site:** https://heathwblack.github.io/trapdrawtracker/

## How it works

```
RSS feed ──▶ filter ──▶ download ──▶ transcribe ──▶ extract ──▶ JSON ──▶ static site
         (Chop 2026)   (.mp3)      (whisper.cpp)   (Claude)
```

1. `fetch_feed.py` pulls the [Trap Draw RSS](https://feeds.megaphone.fm/trapdraw) and keeps episodes whose title matches `^\d+: Chop Session` published in 2026.
2. `download.py` streams the MP3 for each episode to `data/audio/` (gitignored).
3. `transcribe.py` runs `whisper.cpp` locally against each MP3 and writes segment-level JSON transcripts to `data/transcripts/`.
4. `extract.py` sends each transcript to Claude with a structured tool-use schema; Claude returns the monitoring items (title, timestamp, POV summary, status, quote).
5. `docs/items.json` is the served payload; the static site in `docs/` fetches and renders it.

Every stage is idempotent — rerun and it skips finished work.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env  # fill in ANTHROPIC_API_KEY + whisper paths

# whisper.cpp (macOS)
brew install whisper-cpp
# download a model, e.g.:
curl -L -o ~/ggml-medium.en.bin \
  https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-medium.en.bin
# then in .env:
#   WHISPER_CPP_BIN=/opt/homebrew/bin/whisper-cli
#   WHISPER_MODEL_PATH=/Users/you/ggml-medium.en.bin

# ffmpeg (whisper needs 16kHz WAV)
brew install ffmpeg
```

## Run

```bash
./scripts/run_all.sh           # full pipeline end-to-end
# or piecemeal:
python -m pipeline.fetch_feed  # list 2026 Chop Sessions
python -m pipeline.download
python -m pipeline.transcribe
python -m pipeline.extract
```

View the site locally:
```bash
python -m http.server 8000 --directory docs
open http://localhost:8000
```

## Deploy

GitHub Pages → Settings → Pages → Source: `main` branch, `/docs` folder. Push and it's live.

## Layout

```
pipeline/      # the four pipeline stages + config
data/          # audio (gitignored) + transcripts (committed)
docs/          # static site + items.json (served by GH Pages)
scripts/       # run_all.sh
```
