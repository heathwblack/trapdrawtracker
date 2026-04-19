import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
AUDIO_DIR = DATA_DIR / "audio"
TRANSCRIPT_DIR = DATA_DIR / "transcripts"
DOCS_DIR = ROOT / "docs"
ITEMS_PATH = DOCS_DIR / "items.json"

FEED_URL = "https://feeds.megaphone.fm/trapdraw"
CHOP_TITLE_RE = r"^(\d+):\s*Chop Session"
TARGET_YEAR = 2026

ANTHROPIC_MODEL = "claude-opus-4-7"
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

WHISPER_CPP_BIN = os.environ.get("WHISPER_CPP_BIN", "whisper-cli")
WHISPER_MODEL_PATH = os.environ.get("WHISPER_MODEL_PATH", "")
